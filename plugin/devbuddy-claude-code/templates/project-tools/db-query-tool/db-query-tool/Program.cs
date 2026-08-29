using System.Data;
using System.Globalization;
using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.Data.SqlClient;

namespace BmsReadonlyDatabaseQuery;

internal static class Program
{
    private const int DefaultMaxRows = 500;
    private const int HardMaxRows = 5_000;
    private const int DefaultTimeoutSeconds = 30;
    private const int HardTimeoutSeconds = 120;
    private const int MaxRequestBytes = 256_000;
    private const int MaxResponseBytes = 1_048_576;
    private const int MaxCellCharacters = 1_000_000;
    private const int MaxCellBytes = 1_000_000;

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = null,
        WriteIndented = false,
    };

    public static int Main()
    {
        var correlationId = Guid.NewGuid().ToString("N");
        try
        {
            using var document = JsonDocument.Parse(ReadRequestBytes(), new JsonDocumentOptions { MaxDepth = 64 });
            if (document.RootElement.ValueKind != JsonValueKind.Object)
            {
                throw new ToolException("INVALID_REQUEST", "A JSON object request is required.");
            }

            var request = ParseRequest(document.RootElement);
            var response = Execute(request);
            Console.Out.Write(JsonSerializer.Serialize(response, JsonOptions));
            return 0;
        }
        catch (ToolException exception)
        {
            Console.Out.Write(JsonSerializer.Serialize(new ErrorEnvelope(
                new ErrorBody(exception.Code, exception.Message, correlationId)), JsonOptions));
            return 2;
        }
        catch (JsonException)
        {
            Console.Out.Write(JsonSerializer.Serialize(new ErrorEnvelope(
                new ErrorBody("INVALID_REQUEST", "Request JSON is invalid.", correlationId)), JsonOptions));
            return 2;
        }
        catch (OperationCanceledException)
        {
            Console.Out.Write(JsonSerializer.Serialize(new ErrorEnvelope(
                new ErrorBody("CANCELLED", "The query was cancelled.", correlationId)), JsonOptions));
            return 3;
        }
        catch
        {
            Console.Out.Write(JsonSerializer.Serialize(new ErrorEnvelope(
                new ErrorBody("QUERY_FAILED", "The read-only query could not be completed.", correlationId)), JsonOptions));
            return 1;
        }
    }

    private static byte[] ReadRequestBytes()
    {
        using var input = Console.OpenStandardInput();
        using var buffer = new MemoryStream();
        var chunk = new byte[8192];
        int read;
        while ((read = input.Read(chunk, 0, chunk.Length)) > 0)
        {
            buffer.Write(chunk, 0, read);
            if (buffer.Length > MaxRequestBytes)
            {
                throw new ToolException("INVALID_REQUEST", "Request exceeds the size limit.");
            }
        }

        return buffer.ToArray();
    }

    private static QueryRequest ParseRequest(JsonElement root)
    {
        var seen = new HashSet<string>(StringComparer.Ordinal);
        string? sql = null;
        JsonElement? parameters = null;
        var maxRows = DefaultMaxRows;
        var timeoutSeconds = DefaultTimeoutSeconds;

        foreach (var property in root.EnumerateObject())
        {
            if (!seen.Add(property.Name))
            {
                throw new ToolException("INVALID_REQUEST", "Duplicate JSON properties are not allowed.");
            }

            switch (property.Name)
            {
                case "sql":
                    if (property.Value.ValueKind != JsonValueKind.String)
                    {
                        throw new ToolException("INVALID_REQUEST", "sql is required and must be a string.");
                    }
                    sql = property.Value.GetString();
                    break;
                case "parameters":
                    parameters = property.Value.Clone();
                    break;
                case "maxRows":
                    maxRows = ReadInteger(property.Value, "maxRows");
                    break;
                case "timeoutSeconds":
                    timeoutSeconds = ReadInteger(property.Value, "timeoutSeconds");
                    break;
                default:
                    throw new ToolException("INVALID_REQUEST", "Unknown request properties are not allowed.");
            }
        }

        if (string.IsNullOrWhiteSpace(sql))
        {
            throw new ToolException("INVALID_REQUEST", "sql is required and must be a string.");
        }
        if (maxRows is < 1 or > HardMaxRows)
        {
            throw new ToolException("INVALID_LIMIT", $"maxRows must be between 1 and {HardMaxRows}.");
        }
        if (timeoutSeconds is < 1 or > HardTimeoutSeconds)
        {
            throw new ToolException("INVALID_LIMIT", $"timeoutSeconds must be between 1 and {HardTimeoutSeconds}.");
        }

        return new QueryRequest(sql, parameters, maxRows, timeoutSeconds);
    }

    private static int ReadInteger(JsonElement value, string name)
    {
        if (value.ValueKind != JsonValueKind.Number || !value.TryGetInt32(out var result))
        {
            throw new ToolException("INVALID_LIMIT", $"{name} must be an integer.");
        }

        return result;
    }

    private static QueryResponse Execute(QueryRequest request)
    {
        string compiledSql;
        IReadOnlyList<SqlParameterBinding> bindings;
        try
        {
            (compiledSql, bindings) = SqlReadOnly.Parameterize(request.Sql, request.Parameters);
        }
        catch (SqlValidationException exception)
        {
            throw new ToolException("READ_ONLY_VIOLATION", exception.Message);
        }

        var connectionString = LoadConnectionString();
        using var connection = new SqlConnection(connectionString);
        connection.Open();
        using var command = connection.CreateCommand();
        command.CommandText = compiledSql;
        command.CommandTimeout = request.TimeoutSeconds;
        foreach (var binding in bindings)
        {
            var parameter = command.Parameters.Add(binding.Name, SqlTypeFor(binding.Value));
            parameter.Value = binding.Value ?? DBNull.Value;
        }

        using var reader = command.ExecuteReader();
        var columns = UniqueColumns(reader);
        var rows = new List<Dictionary<string, object?>>();
        var truncated = false;

        while (reader.Read())
        {
            var row = new Dictionary<string, object?>(StringComparer.Ordinal);
            for (var index = 0; index < columns.Count; index++)
            {
                row[columns[index]] = JsonValue(reader.GetValue(index));
            }

            var candidate = new QueryResponse(columns, rows.Append(row).ToList(), rows.Count + 1, true);
            if (Serialize(candidate).Length > MaxResponseBytes)
            {
                truncated = true;
                break;
            }

            rows.Add(row);
            if (rows.Count >= request.MaxRows)
            {
                truncated = reader.Read();
                break;
            }
        }

        var response = new QueryResponse(columns, rows, rows.Count, truncated);
        if (Serialize(response).Length > MaxResponseBytes)
        {
            throw new ToolException("RESULT_LIMIT", "The query result exceeds the response limit.");
        }

        return response;
    }

    private static string LoadConnectionString()
    {
        var path = Path.Combine(AppContext.BaseDirectory, "appsettings.json");
        if (!File.Exists(path))
        {
            throw new ToolException("CONFIGURATION_ERROR", "Read-only database configuration is not configured.");
        }

        try
        {
            using var document = JsonDocument.Parse(File.ReadAllBytes(path));
            if (!document.RootElement.TryGetProperty("ConnectionStrings", out var connectionStrings) ||
                connectionStrings.ValueKind != JsonValueKind.Object ||
                !connectionStrings.TryGetProperty("Connection", out var connection) ||
                connection.ValueKind != JsonValueKind.String ||
                string.IsNullOrWhiteSpace(connection.GetString()))
            {
                throw new ToolException("CONFIGURATION_ERROR", "Read-only database configuration is not configured.");
            }

            return connection.GetString()!.Trim();
        }
        catch (JsonException exception)
        {
            throw new ToolException("CONFIGURATION_ERROR", "Read-only database configuration is invalid.", exception);
        }
        catch (IOException exception)
        {
            throw new ToolException("CONFIGURATION_ERROR", "Read-only database configuration is unavailable.", exception);
        }
    }

    private static List<string> UniqueColumns(SqlDataReader reader)
    {
        var counts = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
        var columns = new List<string>(reader.FieldCount);
        for (var index = 0; index < reader.FieldCount; index++)
        {
            var baseName = reader.GetName(index);
            if (string.IsNullOrEmpty(baseName))
            {
                baseName = $"column_{index + 1}";
            }

            counts.TryGetValue(baseName, out var count);
            count++;
            counts[baseName] = count;
            columns.Add(count == 1 ? baseName : $"{baseName}_{count}");
        }

        return columns;
    }

    private static SqlDbType SqlTypeFor(object? value) => value switch
    {
        null => SqlDbType.NVarChar,
        string => SqlDbType.NVarChar,
        bool => SqlDbType.Bit,
        int => SqlDbType.Int,
        long => SqlDbType.BigInt,
        decimal => SqlDbType.Decimal,
        double => SqlDbType.Float,
        _ => SqlDbType.NVarChar,
    };

    private static object? JsonValue(object value)
    {
        if (value is DBNull)
        {
            return null;
        }
        if (value is string text)
        {
            if (text.Length > MaxCellCharacters)
            {
                throw new ToolException("RESULT_LIMIT", "A result value is too large.");
            }
            return text;
        }
        if (value is byte[] bytes)
        {
            if (bytes.Length > MaxCellBytes)
            {
                throw new ToolException("RESULT_LIMIT", "A result value is too large.");
            }
            return Convert.ToBase64String(bytes);
        }
        if (value is decimal decimalValue)
        {
            return decimalValue.ToString(CultureInfo.InvariantCulture);
        }
        if (value is DateTime dateTime)
        {
            return dateTime.ToString("O", CultureInfo.InvariantCulture);
        }
        if (value is DateTimeOffset dateTimeOffset)
        {
            return dateTimeOffset.ToString("O", CultureInfo.InvariantCulture);
        }
        if (value is TimeSpan timeSpan)
        {
            return timeSpan.ToString("c", CultureInfo.InvariantCulture);
        }
        if (value is Guid guid)
        {
            return guid.ToString();
        }
        if (value is double doubleValue && (double.IsNaN(doubleValue) || double.IsInfinity(doubleValue)) ||
            value is float floatValue && (float.IsNaN(floatValue) || float.IsInfinity(floatValue)))
        {
            throw new ToolException("RESULT_LIMIT", "The result contains an unsupported numeric value.");
        }

        return value;
    }

    private static byte[] Serialize(QueryResponse response) => JsonSerializer.SerializeToUtf8Bytes(response, JsonOptions);
}

internal sealed record QueryRequest(string Sql, JsonElement? Parameters, int MaxRows, int TimeoutSeconds);

internal sealed record QueryResponse(
    [property: JsonPropertyName("columns")] IReadOnlyList<string> Columns,
    [property: JsonPropertyName("rows")] IReadOnlyList<Dictionary<string, object?>> Rows,
    [property: JsonPropertyName("rowCount")] int RowCount,
    [property: JsonPropertyName("truncated")] bool Truncated);

internal sealed record ErrorEnvelope([property: JsonPropertyName("error")] ErrorBody Error);

internal sealed record ErrorBody(
    [property: JsonPropertyName("code")] string Code,
    [property: JsonPropertyName("message")] string Message,
    [property: JsonPropertyName("correlationId")] string CorrelationId);

internal sealed class ToolException : Exception
{
    public ToolException(string code, string message, Exception? inner = null) : base(message, inner) => Code = code;

    public string Code { get; }
}
