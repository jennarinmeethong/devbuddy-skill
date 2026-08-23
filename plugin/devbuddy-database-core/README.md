# DevBuddy read-only database tool

Build or publish `src/DevBuddy.Database.Policy`. The executable accepts `--engine`, `--request`, and `--config`. The config is a local-only `appsettings.json` containing `ConnectionStrings.Connection`; it is deliberately not included in this package.

Every request needs `database_id`, `max_rows` (1–5000), `max_result_bytes` (1024–10485760), and `timeout_seconds` (1–120). Relational requests use `sql` and optional scalar `parameters`; MongoDB requests use structured operations; Redis requests use an allowlisted command and `key_prefix`.

The tool validates policy before reading its connection configuration or opening a network connection. Database principals must still be independently restricted to read-only access.
