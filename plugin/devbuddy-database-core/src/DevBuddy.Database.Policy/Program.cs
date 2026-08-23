using System.Data;
using System.Data.Common;
using System.Diagnostics;
using System.Text.Json;
using System.Text.Json.Serialization;
using DevBuddy.Database.Policy;
using Microsoft.Data.SqlClient;
using MongoDB.Bson;
using MongoDB.Bson.Serialization;
using MongoDB.Driver;
using MySqlConnector;
using Npgsql;
using Oracle.ManagedDataAccess.Client;
using StackExchange.Redis;

var options = Arguments.Parse(args);
try
{
    if (options.Engine is "mongodb" or "redis")
    {
        await NoSqlExecutor.Run(options);
        return;
    }
    var request = JsonSerializer.Deserialize<RelationalRequest>(await File.ReadAllTextAsync(options.RequestPath), JsonDefaults.Options)
        ?? throw new PolicyException("invalid_request", "request is empty");
    if (string.IsNullOrWhiteSpace(request.DatabaseId)) throw new PolicyException("invalid_request", "database_id is required");
    if (!ReadOnlyRequestPolicy.IsSafeRelationalQuery(request.Sql, out var reason)) throw new PolicyException("policy_rejected", reason);
    if (request.MaxRows is < 1 or > 5000 || request.MaxResultBytes is < 1024 or > 10 * 1024 * 1024 || request.TimeoutSeconds is < 1 or > 120)
        throw new PolicyException("invalid_limits", "limits exceed the adapter policy");
    var connectionString = ConnectionString.Load(options.ConfigPath);
    await using var connection = Connections.Create(options.Engine, connectionString);
    using var cancel = new CancellationTokenSource(TimeSpan.FromSeconds(request.TimeoutSeconds));
    var watch = Stopwatch.StartNew();
    await connection.OpenAsync(cancel.Token);
    await using var command = connection.CreateCommand();
    command.CommandText = request.Sql; command.CommandTimeout = request.TimeoutSeconds; command.CommandType = CommandType.Text;
    foreach (var (name, value) in request.Parameters ?? new Dictionary<string, JsonElement>())
    {
        if (!name.StartsWith('@')) throw new PolicyException("invalid_parameter", "parameter names must start with @");
        var parameter = command.CreateParameter(); parameter.ParameterName = name; parameter.Value = Value.Convert(value) ?? DBNull.Value; command.Parameters.Add(parameter);
    }
    await using var reader = await command.ExecuteReaderAsync(CommandBehavior.SequentialAccess, cancel.Token);
    var columns = Enumerable.Range(0, reader.FieldCount).Select(reader.GetName).ToArray();
    var rows = new List<Dictionary<string, object?>>(); var serializedBytes = 0; var truncated = false;
    while (await reader.ReadAsync(cancel.Token))
    {
        if (rows.Count >= request.MaxRows) { truncated = true; break; }
        var row = new Dictionary<string, object?>(StringComparer.Ordinal);
        for (var column = 0; column < reader.FieldCount; column++) row[columns[column]] = reader.IsDBNull(column) ? null : reader.GetValue(column);
        Redactor.Apply(row);
        var bytes = JsonSerializer.SerializeToUtf8Bytes(row).Length;
        if (serializedBytes + bytes > request.MaxResultBytes) { truncated = true; break; }
        serializedBytes += bytes; rows.Add(row);
    }
    await JsonSerializer.SerializeAsync(Console.OpenStandardOutput(), new Result(request.DatabaseId, options.Engine, "query", columns, rows, rows.Count, truncated, watch.ElapsedMilliseconds, true, "1.0.0"));
}
catch (PolicyException error) { await Output.Error(error.Code, error.Message); Environment.ExitCode = 2; }
catch (OperationCanceledException) { await Output.Error("timeout", "database operation timed out"); Environment.ExitCode = 2; }
catch (DbException) { await Output.Error("database_error", "database operation failed"); Environment.ExitCode = 2; }
catch (Exception) { await Output.Error("internal_error", "database adapter failed"); Environment.ExitCode = 2; }

internal sealed record RelationalRequest([property: JsonPropertyName("database_id")] string DatabaseId, [property: JsonPropertyName("sql")] string Sql, [property: JsonPropertyName("parameters")] Dictionary<string, JsonElement>? Parameters, [property: JsonPropertyName("max_rows")] int MaxRows, [property: JsonPropertyName("max_result_bytes")] int MaxResultBytes, [property: JsonPropertyName("timeout_seconds")] int TimeoutSeconds);
internal sealed record Result(string database_id, string engine, string operation, string[] columns, List<Dictionary<string, object?>> rows, int row_count, bool truncated, long duration_ms, bool redaction_applied, string adapter_version);
internal sealed class PolicyException(string code, string message) : Exception(message) { public string Code { get; } = code; }
internal sealed record Arguments(string Engine, string RequestPath, string ConfigPath)
{
    public static Arguments Parse(string[] args)
    {
        var values = args.Chunk(2).ToDictionary(pair => pair[0], pair => pair.Length == 2 ? pair[1] : "", StringComparer.OrdinalIgnoreCase);
        if (!values.TryGetValue("--engine", out var engine) || !values.TryGetValue("--request", out var request) || !values.TryGetValue("--config", out var config))
            throw new PolicyException("invalid_arguments", "--engine, --request, and --config are required");
        return new Arguments(engine.ToLowerInvariant(), request, config);
    }
}
internal static class Connections
{
    public static DbConnection Create(string engine, string connection) => engine switch
    {
        "sqlserver" => new SqlConnection(connection), "postgresql" => new NpgsqlConnection(connection), "mariadb" => new MySqlConnection(connection), "oracle" => new OracleConnection(connection),
        _ => throw new PolicyException("unsupported_engine", "relational adapter does not support this engine"),
    };
}
internal static class ConnectionString
{
    public static string Load(string path)
    {
        using var document = JsonDocument.Parse(File.ReadAllText(path));
        if (!document.RootElement.TryGetProperty("ConnectionStrings", out var section) || !section.TryGetProperty("Connection", out var value) || string.IsNullOrWhiteSpace(value.GetString()))
            throw new PolicyException("invalid_config", "local connection configuration is missing");
        return value.GetString()!;
    }
}
internal static class Value
{
    public static object? Convert(JsonElement value) => value.ValueKind switch { JsonValueKind.String => value.GetString(), JsonValueKind.Number when value.TryGetInt64(out var number) => number, JsonValueKind.Number => value.GetDecimal(), JsonValueKind.True => true, JsonValueKind.False => false, JsonValueKind.Null => null, _ => throw new PolicyException("invalid_parameter", "parameter values must be scalar") };
}
internal static class Output
{
    public static Task Error(string code, string message) => JsonSerializer.SerializeAsync(Console.OpenStandardOutput(), new { error = new { code, message } });
}
internal static class JsonDefaults { public static readonly JsonSerializerOptions Options = new() { PropertyNameCaseInsensitive = true }; }
internal static class Redactor
{
    private static readonly string[] Sensitive = ["password", "secret", "token", "key", "email", "phone", "ssn"];
    private static readonly System.Text.RegularExpressions.Regex SensitiveJson = new("(?i)\\\"(password|secret|token|api[_-]?key|email|phone|ssn)\\\"\\s*:\\s*(?:\\\"(?:\\\\.|[^\\\"])*\\\"|[^,}]+)");
    public static void Apply(Dictionary<string, object?> row)
    {
        foreach (var key in row.Keys.ToArray())
            if (Sensitive.Any(item => key.Contains(item, StringComparison.OrdinalIgnoreCase))) row[key] = "[REDACTED]";
    }
    public static JsonElement Json(string json)
    {
        var redacted = SensitiveJson.Replace(json, match => $"\"{match.Groups[1].Value}\":\"[REDACTED]\"");
        return JsonDocument.Parse(redacted).RootElement.Clone();
    }
    public static JsonElement Value(object? value) => Json(JsonSerializer.Serialize(value));
}
internal sealed record NoSqlRequest([property: JsonPropertyName("database_id")] string DatabaseId, [property: JsonPropertyName("database")] string Database, [property: JsonPropertyName("collection")] string Collection, [property: JsonPropertyName("operation")] string Operation, [property: JsonPropertyName("limit")] int Limit, [property: JsonPropertyName("max_rows")] int MaxRows, [property: JsonPropertyName("max_result_bytes")] int MaxResultBytes, [property: JsonPropertyName("timeout_seconds")] int TimeoutSeconds, [property: JsonPropertyName("filter")] JsonElement? Filter, [property: JsonPropertyName("pipeline")] JsonElement? Pipeline, [property: JsonPropertyName("field")] string? Field, [property: JsonPropertyName("command")] string? Command, [property: JsonPropertyName("key")] string? Key, [property: JsonPropertyName("key_prefix")] string? KeyPrefix, [property: JsonPropertyName("keys")] string[]? Keys, [property: JsonPropertyName("fields")] string[]? Fields);
internal static class NoSqlExecutor
{
    private static readonly HashSet<string> MongoOperations = new(StringComparer.Ordinal) { "find", "aggregate", "count", "distinct" };
    private static readonly HashSet<string> MongoStages = new(StringComparer.Ordinal) { "$match", "$project", "$limit", "$skip", "$sort", "$group", "$unwind", "$lookup", "$addFields", "$set", "$count", "$facet" };
    private static readonly HashSet<string> RedisCommands = new(StringComparer.OrdinalIgnoreCase) { "GET", "MGET", "HGET", "HMGET", "HGETALL", "LRANGE", "SCARD", "SMEMBERS", "ZRANGE", "TTL", "EXISTS", "TYPE", "STRLEN" };
    public static async Task Run(Arguments options)
    {
        var request = JsonSerializer.Deserialize<NoSqlRequest>(await File.ReadAllTextAsync(options.RequestPath), JsonDefaults.Options) ?? throw new PolicyException("invalid_request", "request is empty");
        if (string.IsNullOrWhiteSpace(request.DatabaseId) || request.MaxRows is < 1 or > 5000 || request.MaxResultBytes is < 1024 or > 10 * 1024 * 1024 || request.TimeoutSeconds is < 1 or > 120)
            throw new PolicyException("invalid_request", "database_id and bounded limits are required");
        using var cancel = new CancellationTokenSource(TimeSpan.FromSeconds(request.TimeoutSeconds));
        var connection = ConnectionString.Load(options.ConfigPath); var watch = Stopwatch.StartNew();
        if (options.Engine == "mongodb") await Mongo(request, connection, watch, cancel.Token);
        else await Redis(request, connection, watch, cancel.Token);
    }
    private static async Task Mongo(NoSqlRequest request, string connection, Stopwatch watch, CancellationToken cancellation)
    {
        if (!MongoOperations.Contains(request.Operation) || string.IsNullOrWhiteSpace(request.Database) || string.IsNullOrWhiteSpace(request.Collection) || request.Limit is < 1 or > 5000 || request.Limit > request.MaxRows)
            throw new PolicyException("policy_rejected", "MongoDB operation, target, or limit is not allowlisted");
        var filter = request.Filter is null ? new BsonDocument() : BsonDocument.Parse(request.Filter.Value.GetRawText());
        if (filter.ToJson().Contains("$where", StringComparison.OrdinalIgnoreCase) || filter.ToJson().Contains("$function", StringComparison.OrdinalIgnoreCase)) throw new PolicyException("policy_rejected", "MongoDB JavaScript is not allowed");
        var database = new MongoClient(connection).GetDatabase(request.Database);
        var collection = database.GetCollection<BsonDocument>(request.Collection);
        object payload = request.Operation switch
        {
            "find" => (await collection.Find(filter).Limit(request.Limit).ToListAsync(cancellation)).Select(document => Redactor.Json(document.ToJson())).ToArray(),
            "count" => await collection.CountDocumentsAsync(filter, cancellationToken: cancellation),
            "distinct" when !string.IsNullOrWhiteSpace(request.Field) => (await collection.DistinctAsync<BsonValue>(request.Field, filter, cancellationToken: cancellation)).ToList().Select(value => value.ToString()).ToArray(),
            "aggregate" => await Aggregate(database, request, cancellation),
            _ => throw new PolicyException("policy_rejected", "MongoDB request is incomplete"),
        };
        await JsonSerializer.SerializeAsync(Console.OpenStandardOutput(), new { database_id = request.DatabaseId, engine = "mongodb", operation = request.Operation, documents = payload, row_count = Count(payload), truncated = false, duration_ms = watch.ElapsedMilliseconds, redaction_applied = true, adapter_version = "1.0.0", untrusted_result = true });
    }
    private static async Task<string[]> Aggregate(IMongoDatabase database, NoSqlRequest request, CancellationToken cancellation)
    {
        if (request.Pipeline is null || request.Pipeline.Value.ValueKind != JsonValueKind.Array) throw new PolicyException("policy_rejected", "aggregate requires a pipeline");
        var pipeline = BsonSerializer.Deserialize<BsonArray>(request.Pipeline.Value.GetRawText());
        if (pipeline.Any(stage => stage is not BsonDocument document || document.ElementCount != 1 || !MongoStages.Contains(document.GetElement(0).Name))) throw new PolicyException("policy_rejected", "MongoDB pipeline stage is not allowlisted");
        var command = new BsonDocument { { "aggregate", request.Collection }, { "pipeline", pipeline }, { "cursor", new BsonDocument() } };
        var result = await database.RunCommandAsync<BsonDocument>(command, cancellationToken: cancellation);
        return result["cursor"].AsBsonDocument["firstBatch"].AsBsonArray.Select(item => Redactor.Json(item.ToJson()).GetRawText()).ToArray();
    }
    private static async Task Redis(NoSqlRequest request, string connection, Stopwatch watch, CancellationToken cancellation)
    {
        if (string.IsNullOrWhiteSpace(request.Command) || !RedisCommands.Contains(request.Command) || string.IsNullOrWhiteSpace(request.Key) || string.IsNullOrWhiteSpace(request.KeyPrefix) || !request.Key.StartsWith(request.KeyPrefix, StringComparison.Ordinal))
            throw new PolicyException("policy_rejected", "Redis command or key prefix is not allowlisted");
        await using var multiplexer = await ConnectionMultiplexer.ConnectAsync(connection);
        var database = multiplexer.GetDatabase(); var key = (RedisKey)request.Key; object? payload = request.Command.ToUpperInvariant() switch
        {
            "GET" => await database.StringGetAsync(key), "HGET" when request.Fields?.Length == 1 => await database.HashGetAsync(key, request.Fields[0]), "HGETALL" => await database.HashGetAllAsync(key), "LRANGE" => await database.ListRangeAsync(key, 0, request.Limit - 1), "SCARD" => await database.SetLengthAsync(key), "SMEMBERS" => await database.SetMembersAsync(key), "ZRANGE" => await database.SortedSetRangeByRankAsync(key, 0, request.Limit - 1), "TTL" => await database.KeyTimeToLiveAsync(key), "EXISTS" => await database.KeyExistsAsync(key), "TYPE" => await database.KeyTypeAsync(key), "STRLEN" => await database.StringLengthAsync(key), _ => throw new PolicyException("policy_rejected", "Redis request arguments are not allowlisted"),
        };
        await JsonSerializer.SerializeAsync(Console.OpenStandardOutput(), new { database_id = request.DatabaseId, engine = "redis", operation = request.Command, documents = Redactor.Value(payload), row_count = Count(payload), truncated = false, duration_ms = watch.ElapsedMilliseconds, redaction_applied = true, adapter_version = "1.0.0", untrusted_result = true });
    }
    private static int Count(object? value) => value switch { null => 0, Array array => array.Length, _ => 1 };
}
