# DevBuddy read-only database tool

Build or publish `src/DevBuddy.Database.Policy`. The executable accepts `--engine`, `--request`, and `--config`. The config is a local-only `appsettings.json` containing `ConnectionStrings.Connection`; it is deliberately not included in this package.

Copy the `appsettings.template.json` from the selected engine package to the workspace database profile and rename it to `appsettings.json`. Replace only the `__...__` values locally. The template has the expected syntax for SQL Server, PostgreSQL, MariaDB, Oracle, MongoDB, or Redis; see `docs/database-connection-templates.md` for examples and the security requirements. Never commit the resulting file.

Create a distributable adapter before installing the plugin with `python scripts/build_plugin.py --runtime win-x64 --apply` (or the intended .NET runtime identifier). This compiles the shared executable and all six engine drivers once; engine-specific `tool.json` manifests select its read-only policy mode at invocation time.

Every request needs `database_id`, `max_rows` (1–5000), `max_result_bytes` (1024–10485760), and `timeout_seconds` (1–120). Relational requests use `sql` and optional scalar `parameters`; MongoDB requests use structured operations; Redis requests use an allowlisted command and `key_prefix`.

The tool validates policy before reading its connection configuration or opening a network connection. Database principals must still be independently restricted to read-only access.
