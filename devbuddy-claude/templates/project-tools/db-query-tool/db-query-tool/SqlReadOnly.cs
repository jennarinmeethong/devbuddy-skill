using System.Text.Json;
using System.Text.RegularExpressions;

namespace BmsReadonlyDatabaseQuery;

internal static class SqlReadOnly
{
    private const int MaxSqlCharacters = 100_000;
    private static readonly Regex ParameterName = new("^[A-Za-z_][A-Za-z0-9_]{0,127}$", RegexOptions.Compiled);
    private static readonly HashSet<string> Forbidden = new(StringComparer.OrdinalIgnoreCase)
    {
        "ALTER", "BACKUP", "BEGIN", "COMMIT", "CREATE", "DBCC", "DENY", "DELETE",
        "DECLARE", "DROP", "EXEC", "EXECUTE", "GRANT", "INSERT", "MERGE", "REVERT",
        "REVOKE", "ROLLBACK", "SET", "TRUNCATE", "UPDATE", "USE",
    };
    private static readonly HashSet<string> External = new(StringComparer.OrdinalIgnoreCase)
    {
        "OPENQUERY", "OPENROWSET", "OPENDATASOURCE", "BULK",
    };
    private static readonly string[] DangerousFunctionPrefixes = ["XP_", "SP_", "OPEN"];

    public static (string Sql, IReadOnlyList<SqlParameterBinding> Bindings) Parameterize(string sql, JsonElement? parameters)
    {
        var tokens = Validate(sql);
        var normalized = ValidateParameters(parameters);
        var used = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var replacements = new List<(int Start, int End, string Replacement)>();
        var bindings = new List<SqlParameterBinding>();
        var parameterIndex = 0;

        foreach (var token in tokens)
        {
            if (token.Kind != TokenKind.Parameter)
            {
                continue;
            }

            var key = token.Value.ToLowerInvariant();
            if (!normalized.TryGetValue(key, out var value))
            {
                throw new SqlValidationException("Every SQL parameter must be supplied.");
            }

            used.Add(key);
            var name = $"@p{parameterIndex++}";
            replacements.Add((token.Start, token.End, name));
            bindings.Add(new SqlParameterBinding(name, value));
        }

        if (!used.SetEquals(normalized.Keys))
        {
            throw new SqlValidationException("Unused SQL parameters are not allowed.");
        }

        var compiled = sql;
        for (var index = replacements.Count - 1; index >= 0; index--)
        {
            var replacement = replacements[index];
            compiled = compiled[..replacement.Start] + replacement.Replacement + compiled[replacement.End..];
        }

        return (compiled, bindings);
    }

    public static IReadOnlyList<Token> Validate(string sql)
    {
        if (string.IsNullOrWhiteSpace(sql) || sql.Length > MaxSqlCharacters)
        {
            throw new SqlValidationException("SQL is required and must be within the size limit.");
        }

        var tokens = Tokenize(sql);
        if (tokens.Count == 0)
        {
            throw new SqlValidationException("SQL is required.");
        }

        var semicolons = tokens.Select((token, index) => (token, index)).Where(item => item.token.Value == ";").Select(item => item.index).ToArray();
        if (semicolons.Length > 0 && (semicolons.Length != 1 || semicolons[0] != tokens.Count - 1))
        {
            throw new SqlValidationException("Only one SQL statement is allowed.");
        }

        var words = tokens.Where(token => token.Kind == TokenKind.Identifier).Select(token => token.Value.ToUpperInvariant()).ToList();
        if (words.Count == 0 || (words[0] != "SELECT" && words[0] != "WITH") || !words.Contains("SELECT"))
        {
            throw new SqlValidationException("Only SELECT statements are allowed.");
        }
        if (words.Any(Forbidden.Contains) || words.Contains("INTO"))
        {
            throw new SqlValidationException("Only read-only SELECT statements are allowed.");
        }
        if (words.Any(External.Contains) || words.Contains("OPTION"))
        {
            throw new SqlValidationException("External sources and query hints are not allowed.");
        }

        var depth = 0;
        for (var index = 0; index < tokens.Count; index++)
        {
            var token = tokens[index];
            if (token.Value == "(") depth++;
            if (token.Value == ")")
            {
                depth--;
                if (depth < 0) throw new SqlValidationException("Unbalanced SQL parentheses.");
            }

            if (token.Kind == TokenKind.Identifier && DangerousFunctionPrefixes.Any(prefix => token.Value.StartsWith(prefix, StringComparison.OrdinalIgnoreCase)) &&
                index + 1 < tokens.Count && tokens[index + 1].Value == "(")
            {
                throw new SqlValidationException("Extended and external functions are not allowed.");
            }
            if (token.Kind == TokenKind.Identifier && token.Value.Equals("WITH", StringComparison.OrdinalIgnoreCase) &&
                index + 1 < tokens.Count && tokens[index + 1].Value == "(")
            {
                throw new SqlValidationException("Table hints are not allowed.");
            }
        }
        if (depth != 0)
        {
            throw new SqlValidationException("Unbalanced SQL parentheses.");
        }

        RejectQualifiedExternalNames(tokens);
        for (var index = 0; index < tokens.Count - 1; index++)
        {
            if (!tokens[index].Value.Equals("FROM", StringComparison.OrdinalIgnoreCase) &&
                !tokens[index].Value.Equals("JOIN", StringComparison.OrdinalIgnoreCase) &&
                tokens[index].Value != ",")
            {
                continue;
            }

            if (tokens[index + 1].Kind != TokenKind.Identifier) continue;
            var cursor = index + 2;
            while (cursor + 1 < tokens.Count && tokens[cursor].Value == "." && tokens[cursor + 1].Kind == TokenKind.Identifier)
            {
                cursor += 2;
            }
            if (cursor < tokens.Count && tokens[cursor].Value == "(")
            {
                throw new SqlValidationException("Table-valued functions are not allowed.");
            }
        }

        return tokens;
    }

    private static Dictionary<string, object?> ValidateParameters(JsonElement? parameters)
    {
        var normalized = new Dictionary<string, object?>(StringComparer.OrdinalIgnoreCase);
        if (parameters is null || parameters.Value.ValueKind == JsonValueKind.Undefined || parameters.Value.ValueKind == JsonValueKind.Null)
        {
            return normalized;
        }
        if (parameters.Value.ValueKind != JsonValueKind.Object || parameters.Value.EnumerateObject().Count() > 100)
        {
            throw new SqlValidationException("Parameters must be a JSON object with at most 100 entries.");
        }

        foreach (var property in parameters.Value.EnumerateObject())
        {
            var name = property.Name.StartsWith('@') ? property.Name[1..] : property.Name;
            if (!ParameterName.IsMatch(name) || !normalized.TryAdd(name.ToLowerInvariant(), JsonParameterValue(property.Value)))
            {
                throw new SqlValidationException("Parameter names must be unique simple identifiers.");
            }
        }

        return normalized;
    }

    private static object? JsonParameterValue(JsonElement value)
    {
        return value.ValueKind switch
        {
            JsonValueKind.Null => null,
            JsonValueKind.String when value.GetString()!.Length <= 4_000 => value.GetString(),
            JsonValueKind.String => throw new SqlValidationException("String parameters exceed the size limit."),
            JsonValueKind.True or JsonValueKind.False => value.GetBoolean(),
            JsonValueKind.Number when value.TryGetInt64(out var integer) => integer,
            JsonValueKind.Number when value.TryGetDecimal(out var decimalValue) => decimalValue,
            JsonValueKind.Number when value.TryGetDouble(out var doubleValue) => doubleValue,
            _ => throw new SqlValidationException("Parameters must be scalar JSON values."),
        };
    }

    private static List<Token> Tokenize(string sql)
    {
        var tokens = new List<Token>();
        var index = 0;
        while (index < sql.Length)
        {
            var character = sql[index];
            if (char.IsWhiteSpace(character)) { index++; continue; }
            if (sql.AsSpan(index).StartsWith("--", StringComparison.Ordinal))
            {
                var newline = sql.IndexOf('\n', index + 2);
                index = newline < 0 ? sql.Length : newline + 1;
                continue;
            }
            if (sql.AsSpan(index).StartsWith("/*", StringComparison.Ordinal))
            {
                var end = sql.IndexOf("*/", index + 2, StringComparison.Ordinal);
                if (end < 0) throw new SqlValidationException("Unterminated SQL comment.");
                index = end + 2;
                continue;
            }
            if (character == '\'') { tokens.Add(ReadQuoted(sql, index, '\'', '\'', TokenKind.String, out index)); continue; }
            if (character is '[' or '"')
            {
                var closing = character == '[' ? ']' : '"';
                tokens.Add(ReadQuoted(sql, index, character, closing, TokenKind.Identifier, out index));
                continue;
            }
            if (character == '@')
            {
                var start = index++;
                while (index < sql.Length && (char.IsLetterOrDigit(sql[index]) || sql[index] == '_')) index++;
                if (index == start + 1) throw new SqlValidationException("Invalid SQL variable.");
                tokens.Add(new Token(TokenKind.Parameter, sql[(start + 1)..index], start, index));
                continue;
            }
            if (char.IsLetter(character) || character == '_')
            {
                var start = index++;
                while (index < sql.Length && (char.IsLetterOrDigit(sql[index]) || sql[index] is '_' or '$')) index++;
                tokens.Add(new Token(TokenKind.Identifier, sql[start..index], start, index));
                continue;
            }
            if (char.IsDigit(character))
            {
                var start = index++;
                while (index < sql.Length && (char.IsLetterOrDigit(sql[index]) || sql[index] is '.' or '_' or '+' or '-')) index++;
                tokens.Add(new Token(TokenKind.Number, sql[start..index], start, index));
                continue;
            }
            if (";.,()=*<>+-/%?".Contains(character))
            {
                tokens.Add(new Token(TokenKind.Punctuation, character.ToString(), index, index + 1));
                index++;
                continue;
            }
            throw new SqlValidationException("Unsupported SQL syntax.");
        }
        return tokens;
    }

    private static Token ReadQuoted(string sql, int start, char opening, char closing, TokenKind kind, out int end)
    {
        var index = start + 1;
        while (index < sql.Length)
        {
            if (sql[index] == closing)
            {
                if (index + 1 < sql.Length && sql[index + 1] == closing) { index += 2; continue; }
                index++;
                var value = sql[(start + 1)..(index - 1)].Replace(new string(closing, 2), closing.ToString(), StringComparison.Ordinal);
                end = index;
                return new Token(kind, value, start, end);
            }
            index++;
        }
        throw new SqlValidationException(kind == TokenKind.String ? "Unterminated SQL string." : "Unterminated quoted identifier.");
    }

    private static void RejectQualifiedExternalNames(IReadOnlyList<Token> tokens)
    {
        for (var index = 0; index < tokens.Count; index++)
        {
            var token = tokens[index];
            if (token.Kind == TokenKind.Identifier && token.Value.StartsWith('#')) throw new SqlValidationException("Temporary tables are not allowed.");
            if (token.Kind == TokenKind.Identifier && External.Contains(token.Value)) throw new SqlValidationException("External data sources are not allowed.");
            if (token.Kind != TokenKind.Identifier || index + 2 >= tokens.Count || tokens[index + 1].Value != ".") continue;
            var identifiers = 1;
            var cursor = index + 2;
            while (cursor < tokens.Count && tokens[cursor].Kind == TokenKind.Identifier)
            {
                identifiers++;
                cursor++;
                if (cursor + 1 >= tokens.Count || tokens[cursor].Value != ".") break;
                cursor++;
            }
            if (identifiers > 2) throw new SqlValidationException("Cross-database and linked-server names are not allowed.");
        }
    }

    internal sealed record Token(TokenKind Kind, string Value, int Start, int End);
}

internal enum TokenKind
{
    Identifier,
    String,
    Parameter,
    Number,
    Punctuation,
}

internal sealed record SqlParameterBinding(string Name, object? Value);

internal sealed class SqlValidationException : Exception
{
    public SqlValidationException(string message) : base(message) { }
}
