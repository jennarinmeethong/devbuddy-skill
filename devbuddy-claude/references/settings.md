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
    - id: haiku
      rank: 1
      allowed_roles: [developer, qa]
      allowed_risks: [low]
    - id: sonnet
      rank: 2
      allowed_roles: [ba-pm, architect, developer, qa, security, reviewer]
      allowed_risks: [low, medium, high]
  approved_effort_levels:
    - id: low
      rank: 1
      allowed_roles: [developer, qa]
      allowed_risks: [low]
    - id: medium
      rank: 2
      allowed_roles: [ba-pm, architect, developer, qa, security, reviewer]
      allowed_risks: [low, medium, high]
```

Ranks are positive integers; lower means less capable or less costly. Every dispatched role and risk must be allowed by both the selected model entry and the selected effort entry. Validate the file with `scripts/validate_project_settings.py` before the first dispatch.

Do not add provider, price, credential, prompt, or personal data to settings.

## Custom tools

A workspace that owns custom tools declares them so the Orchestrator knows which executables are approved, what shape each call takes, and where the host's secrets live:

```yaml
tools:
  approved_custom_tool_runtimes: [python, dotnet]
custom_tools:
  - name: readonly_database_query
    runtime: dotnet
    manifest: tools/db-query-tool/tool.json
    secret_file: tools/db-query-tool/appsettings.json
```

Both keys are optional; a workspace with no custom tools omits them. When `custom_tools` is present the validator requires an approved runtime for every entry, a manifest that parses as JSON and declares `name`, `description`, `command`, `inputSchema`, and `outputSchema`, and — for a declared `secret_file` — a committed `*.template.*` sibling. It also refuses a manifest containing a credential-shaped value, because a manifest is meant to be committed and a leaked one has already leaked. Paths resolve from the `.devbuddy` root.

Read `references/custom-tools.md` before proposing, registering, or calling one.

## Budgets are not defaulted

`max_concurrency`, `task_timeout_seconds`, and `retry_limit` have no shipped default. They are commitments of the user's time and money, so DevBuddy asks rather than assumes. A missing budget is a dispatch block, not a value to invent.

## About the shipped allowlist

The adapter's own `settings.yaml` carries a ranked default of `haiku` / `sonnet` / `opus` and `low` / `medium` / `high` so the adapter is usable immediately. Treat it as an approval **boundary**, not a recommendation and not a cost waiver:

- A project may narrow it. Widening it, adding a provider, or adding a model with different privacy or cost behaviour is a new Cost Approval decision that needs the user.
- The allowlist says a pair is *permitted*, never that it is *appropriate*. The minimum-sufficient rule still picks the pair, per dispatch, with a recorded reason.
- Project settings override the adapter default. Where both define a model with the same `id`, the project entry wins entirely — the two are not merged.

## Resolution order

Explicit user instruction for the current task, then project settings, then the adapter `settings.yaml`, then platform defaults for non-semantic mechanics only. A platform default may never override a behavioural policy.

## Memory locator

`memory_root` accepts an absolute path or a path relative to the project root, including a path inside an Obsidian vault. It is the only memory information stored in the project file; project knowledge itself lives under the resolved root. Resolve the locator before any memory read or write.

Relative project paths resolve from the parent of `.devbuddy`. Shared canonical knowledge is always below `knowledge-base/`; tasks and tools remain siblings. Claude carries effort in the selected `devbuddy-<role>-<effort>` agent definition and carries model in the per-call Agent tool `model` parameter; an agent definition must not pin a model.
