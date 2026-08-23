# Initialise a local database fixture for testing

The DevBuddy adapter is deliberately read-only. Create test databases, tables, sample data, and database accounts with a normal administrator client **before** invoking DevBuddy. Never point these commands at a production server, and never give the DevBuddy runtime account DDL or write permission.

After setup, copy the appropriate `appsettings.template.json`, use the `devbuddy_reader` account in its local-only `appsettings.json`, then query only the sample data through the adapter.

## SQL Server

Run in a local SQL Server administrator session. Reconnect to `devbuddy_test` before the second block.

```sql
CREATE DATABASE devbuddy_test;
GO
USE devbuddy_test;
GO
CREATE SCHEMA reporting;
GO
CREATE TABLE reporting.invoice (
  id int NOT NULL PRIMARY KEY,
  customer_name nvarchar(100) NOT NULL,
  total decimal(12,2) NOT NULL,
  issued_at datetime2 NOT NULL
);
INSERT INTO reporting.invoice VALUES (1, N'Example Co', 1250.00, SYSUTCDATETIME());
GO
CREATE LOGIN devbuddy_reader WITH PASSWORD = '<choose-a-local-secret>';
CREATE USER devbuddy_reader FOR LOGIN devbuddy_reader;
GRANT SELECT ON SCHEMA::reporting TO devbuddy_reader;
```

## PostgreSQL

Run the first line while connected to a PostgreSQL administration database, reconnect to `devbuddy_test`, then run the remaining commands.

```sql
CREATE DATABASE devbuddy_test;
-- reconnect to devbuddy_test
CREATE SCHEMA reporting;
CREATE TABLE reporting.invoice (
  id integer PRIMARY KEY,
  customer_name text NOT NULL,
  total numeric(12,2) NOT NULL,
  issued_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO reporting.invoice (id, customer_name, total) VALUES (1, 'Example Co', 1250.00);
CREATE ROLE devbuddy_reader LOGIN PASSWORD '<choose-a-local-secret>';
GRANT CONNECT ON DATABASE devbuddy_test TO devbuddy_reader;
GRANT USAGE ON SCHEMA reporting TO devbuddy_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA reporting TO devbuddy_reader;
```

## MariaDB

Run the following using a local MariaDB administrator account.

```sql
CREATE DATABASE devbuddy_test;
USE devbuddy_test;
CREATE TABLE invoice (
  id int NOT NULL PRIMARY KEY,
  customer_name varchar(100) NOT NULL,
  total decimal(12,2) NOT NULL,
  issued_at datetime NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO invoice (id, customer_name, total) VALUES (1, 'Example Co', 1250.00);
CREATE USER 'devbuddy_reader'@'%' IDENTIFIED BY '<choose-a-local-secret>';
GRANT SELECT ON devbuddy_test.* TO 'devbuddy_reader'@'%';
```

## Oracle

The exact database/container setup is DBA-specific. In a non-production pluggable database, an administrator can create a dedicated test user, then connect as that user:

```sql
CREATE USER devbuddy_test IDENTIFIED BY "<choose-a-local-secret>";
GRANT CREATE SESSION, CREATE TABLE TO devbuddy_test;
-- reconnect as devbuddy_test
CREATE TABLE invoice (
  id NUMBER PRIMARY KEY,
  customer_name VARCHAR2(100) NOT NULL,
  total NUMBER(12,2) NOT NULL,
  issued_at TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL
);
INSERT INTO invoice (id, customer_name, total) VALUES (1, 'Example Co', 1250.00);
COMMIT;
```

For a strict read-only runtime account, have the DBA create a separate account with `CREATE SESSION` and `SELECT` only on the required tables; do not reuse the setup account above.

## MongoDB

Run in `mongosh` against a local development deployment. The adapter will subsequently allow only structured read operations.

```javascript
use devbuddy_test
db.createCollection("invoice")
db.invoice.insertOne({ _id: 1, customer_name: "Example Co", total: 1250, issued_at: new Date() })
db.createUser({ user: "devbuddy_reader", pwd: "<choose-a-local-secret>", roles: [{ role: "read", db: "devbuddy_test" }] })
```

## Redis

Redis has logical databases and keys rather than tables. Run this only against a local test instance, using an administrator connection:

```text
ACL SETUSER devbuddy_reader on >choose-a-local-secret ~devbuddy:test:* +get +mget +exists +ttl +pttl +type +scan
SET devbuddy:test:invoice:1 '{"id":1,"customer_name":"Example Co","total":1250}'
```

The runtime connection string must use that ACL user, `allowAdmin=False`, and a matching `key_prefix` of `devbuddy:test:`.

## Verify through DevBuddy

Only after the fixture and local connection file exist, submit a bounded read request. PostgreSQL example:

```json
{
  "database_id": "devbuddy-test-postgresql",
  "sql": "SELECT id, customer_name, total, issued_at FROM reporting.invoice ORDER BY id",
  "max_rows": 10,
  "max_result_bytes": 65536,
  "timeout_seconds": 10
}
```

Validate the request first:

```text
python scripts/validate_database_request.py postgresql (Get-Content -Raw request.json)
```

Then use the target-specific Tier 2 approval and the selected adapter. The initialisation commands above must never be sent through the DevBuddy database adapter.
