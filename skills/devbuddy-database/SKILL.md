---
name: devbuddy-database
description: Portable, read-only database policy for DevBuddy optional database adapters.
---

# DevBuddy Database

Database access is optional and always Tier 2. Require an explicit `database_id`, matching adapter package, tool manifest, read-only principal, and target-specific approval (production defaults to `ask`). Never accept or log credentials.

- Relational requests must be parameterized, one read-only statement, time-limited, and result-limited.
- MongoDB accepts only structured `find`, allowlisted `aggregate`, `count`, and `distinct` operations.
- Redis accepts only adapter-declared read commands with an approved key prefix.
- Redact secret-like and PII-like output. Do not automatically persist raw results to knowledge.
- Return normalized errors without topology or credential details.
