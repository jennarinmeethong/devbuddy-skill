# Project Settings

Create the selected `.devbuddy/settings.yaml` before any dispatch. Register every source repository by stable project ID. The file uses this restricted YAML shape:

```yaml
schema_version: 1
workspace:
  projects:
    fe:
      path: ../frontend
    be:
      path: ../backend
memory_root: knowledge-base
orchestration:
  max_concurrency: 2
  task_timeout_seconds: 900
  retry_limit: 1
  approved_models:
    - id: approved-model-id
      rank: 1
      allowed_roles: [developer, qa]
      allowed_risks: [low, medium]
  approved_effort_levels:
    - id: low
      rank: 1
      allowed_roles: [developer, qa]
      allowed_risks: [low, medium]
```

Ranks are positive integers; lower means less capable/costly. Choose the lowest-ranked approved model and effort independently; every dispatched role/risk must be allowed by both selected entries. A model rank and effort rank do not need to match, and neither selection implies the other. Escalation above the lowest permitted option needs a task-specific reason in the ledger before dispatch. The allowlist is an approval boundary, not a model catalogue. Do not add provider, price, credential, prompt, or personal data to settings.

Relative project paths resolve from the parent of `.devbuddy`. `memory_root: knowledge-base` places shared canonical knowledge below the workspace; tasks and tools remain siblings. The Codex adapter does not ship provider model IDs: project settings own the approved model allowlist, and selected values map to the subagent call's `model` and `reasoning_effort` parameters.

## Custom tools

A workspace that owns custom tools declares them, so the Orchestrator knows which executables are approved, what shape each call takes, and where the host's secrets live:

```yaml
tools:
  approved_custom_tool_runtimes: [python, dotnet]
custom_tools:
  - name: readonly_database_query
    runtime: dotnet
    manifest: tools/db-query-tool/tool.json
    secret_file: tools/db-query-tool/appsettings.json
```

Both keys are optional; omit them when the workspace has no custom tools. When `custom_tools` is present, every entry needs a runtime from `approved_custom_tool_runtimes` and a manifest that parses as JSON and declares `name`, `description`, `command`, `inputSchema`, and `outputSchema`. A declared `secret_file` also needs a committed `*.template.*` sibling, and a manifest holding a credential-shaped value is rejected — a manifest is meant to be committed, so a leaked one has already leaked. Paths resolve from the `.devbuddy` root.

Read `references/custom-tools.md` before proposing, registering, or calling one.
