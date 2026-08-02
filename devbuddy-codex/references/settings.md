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
