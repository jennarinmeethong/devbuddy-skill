# Database connection-string templates

Use the `appsettings.template.json` from the database adapter package selected by the workspace profile. Copy it to that database profile as `appsettings.json`, then replace each `__...__` placeholder locally. The executable reads only `ConnectionStrings.Connection` and ignores the explanatory `_instructions` field.

`appsettings.json` is intentionally excluded from packages and source control. Store its password in the local secret mechanism approved for the workstation, and create a separate, least-privilege read-only account for DevBuddy.

| Engine | Template | Connection-string format |
| --- | --- | --- |
| SQL Server | `plugin/devbuddy-database-sqlserver/appsettings.template.json` | `Server=host,1433;Database=name;User ID=user;Password=secret;Encrypt=True;TrustServerCertificate=False` |
| PostgreSQL | `plugin/devbuddy-database-postgresql/appsettings.template.json` | `Host=host;Port=5432;Database=name;Username=user;Password=secret;SSL Mode=VerifyFull` |
| MariaDB | `plugin/devbuddy-database-mariadb/appsettings.template.json` | `Server=host;Port=3306;Database=name;User ID=user;Password=secret;SslMode=VerifyFull` |
| Oracle | `plugin/devbuddy-database-oracle/appsettings.template.json` | `User Id=user;Password=secret;Data Source=host:1521/service_name` |
| MongoDB | `plugin/devbuddy-database-mongodb/appsettings.template.json` | `mongodb://user:secret@host:27017/auth_database?authSource=auth_database&tls=true` |
| Redis | `plugin/devbuddy-database-redis/appsettings.template.json` | `host:6380,user=user,password=secret,ssl=True,abortConnect=False,allowAdmin=False` |

## Notes by engine

- SQL Server: retain `Encrypt=True`. In production, retain `TrustServerCertificate=False` and install a server certificate trusted by the machine running the adapter. See [Microsoft's SQL Server connection-string syntax](https://learn.microsoft.com/en-us/sql/connect/ado-net/connection-string-syntax?view=sql-server-ver17).
- PostgreSQL: `SSL Mode=VerifyFull` checks the server certificate and host name. Configure the appropriate trusted CA certificate on the workstation as required. See [Npgsql connection-string parameters](https://www.npgsql.org/doc/connection-string-parameters).
- MariaDB: `SslMode=VerifyFull` checks both certificate trust and the host name. See [MySqlConnector connection options](https://mysqlconnector.net/connection-options/).
- Oracle: the template uses Easy Connect syntax. If the DBA provides a TNS alias, a TNS descriptor, or a TCPS endpoint, replace the complete `Data Source` value with that supplied form. See [ODP.NET connection features](https://docs.oracle.com/en/database/oracle/oracle-database/21/odpnt/featConnecting.html).
- MongoDB: URL-encode reserved characters in username or password. For Atlas, use the provided `mongodb+srv://` URI and retain TLS. See [MongoDB .NET/C# connection options](https://www.mongodb.com/docs/drivers/csharp/current/connect/connection-options/).
- Redis: use a Redis ACL user restricted to the allowed key prefix and read commands. Do not enable admin commands; the template retains `allowAdmin=False`. See [StackExchange.Redis configuration](https://stackexchange.github.io/StackExchange.Redis/Configuration).

The connection string only chooses where and how the adapter connects. It does not relax DevBuddy's request validation, target-specific Tier 2 approval, row/byte/timeout limits, or read-only query policy.

For local test database/table setup and a bounded first read request, see [database-test-fixtures.md](database-test-fixtures.md). Those setup commands must be run through an administrator client, never through the DevBuddy read-only adapter.
