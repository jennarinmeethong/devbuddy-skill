---
name: devbuddy-database
description: Policy gate for Plugin-owned, read-only DevBuddy database adapters.
---

# DevBuddy Database Plugin Policy

This skill is policy only. It does not ship a database tool, driver, executable,
connection configuration, or direct database invocation. Database execution is
owned by an installed DevBuddy Plugin: `devbuddy-database-core` plus one
matching `devbuddy-database-<engine>` adapter selected by the workspace
profile.

Database access is optional and always Tier 2. Before dispatch, require an
explicit `database_id`, the selected adapter package, its Plugin-owned tool
manifest, a read-only principal, and target-specific approval (production
defaults to `ask`). If the required package, manifest, adapter, or approval is
unavailable, return `waiting_user`; do not fall back to a workspace custom
tool, a direct driver, or a shell command. Never accept or log credentials.

Treat the old `readonly_database_query` custom tool and
`.devbuddy/tools/db-query-tool/` as retired. Do not invoke them even if an
older workspace still contains their registry or executable. Ask the user to
preview the release-owned `migrate_legacy_database_tools.py` migration, then
use a materialized Plugin-owned adapter instead.

- Relational requests must be parameterized, one read-only statement, time-limited, and result-limited.
- MongoDB accepts only structured `find`, allowlisted `aggregate`, `count`, and `distinct` operations.
- Redis accepts only adapter-declared read commands with an approved key prefix.
- Redact secret-like and PII-like output. Do not automatically persist raw results to knowledge.
- Return normalized errors without topology or credential details.
