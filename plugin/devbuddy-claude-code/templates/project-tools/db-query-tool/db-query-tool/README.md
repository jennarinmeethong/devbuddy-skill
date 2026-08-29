# Read-only database query tool

This is a self-contained .NET 8 executable that accepts one JSON request on stdin and writes one JSON response on stdout. It uses `Microsoft.Data.SqlClient`, matching the Web API's SQL Server provider and connection-string format. Runtime execution does not require `dotnet`, Python, `uv`, or an ODBC driver.

## Local configuration

Copy `appsettings.template.json` to `appsettings.json` beside the executable and set the same connection string used by the Web API under `ConnectionStrings:Connection`.

The real `appsettings.json` is local-only and must never be committed, placed in `tool.json`, or included in a release artifact. Use a dedicated SQL Server principal with `SELECT` access only to approved views/tables and no write, DDL, `EXECUTE`, ownership, or administrative privileges.

## Build releases

From the repository root, run the build script once on a machine with the .NET 8 SDK and network access to restore packages:

```text
.devbuddy/tools/db-query-tool/build-release.sh
```

It produces self-contained single-file bundles for `osx-arm64`, `win-x64`, and `linux-x64`. Each bundle contains a native executable, `tool.json`, and `appsettings.template.json`; the runtime command in each manifest calls the executable directly.

## Protocol

The request supports `sql`, scalar `parameters`, `maxRows` (1–5000), and `timeoutSeconds` (1–120). Only one validated `SELECT`/CTE statement is allowed. Writes, DDL, execution, temporary/cross-database/external sources, table/query hints, table-valued functions, and `SELECT INTO` are rejected before execution.
