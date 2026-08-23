using System.Text.RegularExpressions;

namespace DevBuddy.Database.Policy;

/// <summary>Policy gate only; a least-privilege database principal remains the security boundary.</summary>
public static partial class ReadOnlyRequestPolicy
{
    private static readonly HashSet<string> RedisReadCommands = new(StringComparer.OrdinalIgnoreCase)
    {
        "GET", "MGET", "HGET", "HMGET", "HGETALL", "LRANGE", "SCARD", "SMEMBERS", "ZRANGE", "TTL", "EXISTS", "TYPE", "STRLEN",
    };

    public static bool IsSafeRelationalQuery(string? sql, out string error)
    {
        error = string.Empty;
        if (string.IsNullOrWhiteSpace(sql)) { error = "sql is required"; return false; }
        var query = Comments().Replace(sql, string.Empty).Trim();
        if (!StartsReadOnly().IsMatch(query)) { error = "only SELECT or CTE queries are allowed"; return false; }
        if (query.TrimEnd(';').Contains(';')) { error = "only one statement is allowed"; return false; }
        if (UnsafeSql().IsMatch(query)) { error = "unsafe SQL operation is not allowed"; return false; }
        if (LockingSyntax().IsMatch(query)) { error = "locking or temporary-object syntax is not allowed"; return false; }
        if (UnsafeFunction().IsMatch(query)) { error = "unsafe SQL function is not allowed"; return false; }
        if (CrossDatabase().IsMatch(query)) { error = "cross-database access is not allowed"; return false; }
        return true;
    }

    public static bool IsSafeRedisRequest(string? command, string? key, string? approvedPrefix, out string error)
    {
        error = string.Empty;
        if (string.IsNullOrWhiteSpace(command) || !RedisReadCommands.Contains(command)) { error = "Redis command is not allowlisted"; return false; }
        if (string.IsNullOrEmpty(approvedPrefix) || string.IsNullOrEmpty(key) || !key.StartsWith(approvedPrefix, StringComparison.Ordinal)) { error = "Redis key must use the approved key prefix"; return false; }
        return true;
    }

    [GeneratedRegex(@"--[^\r\n]*|/\*.*?\*/", RegexOptions.Singleline)] private static partial Regex Comments();
    [GeneratedRegex(@"^(select|with)\b", RegexOptions.IgnoreCase)] private static partial Regex StartsReadOnly();
    [GeneratedRegex(@"\b(insert|update|delete|merge|create|alter|drop|truncate|exec(?:ute)?|call|grant|revoke|commit|rollback|begin|declare|use|into|lock|copy|load|outfile|dblink|prepare|deallocate)\b", RegexOptions.IgnoreCase)] private static partial Regex UnsafeSql();
    [GeneratedRegex(@"\b(select\s+.*\s+into|for\s+(update|share)|nolock)\b", RegexOptions.IgnoreCase | RegexOptions.Singleline)] private static partial Regex LockingSyntax();
    [GeneratedRegex(@"\b(?:pg_sleep|sleep|benchmark|load_file|xp_[a-z0-9_]+|sys\.)\s*\(", RegexOptions.IgnoreCase)] private static partial Regex UnsafeFunction();
    [GeneratedRegex(@"\b[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*\b")] private static partial Regex CrossDatabase();
}
