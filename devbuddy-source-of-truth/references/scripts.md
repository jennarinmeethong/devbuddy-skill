# Bundled Python Tools

All bundled scripts use only Python's standard library. Confirm `python` is available before use. Do not install packages automatically.

| Script | Purpose | Safe invocation |
|---|---|---|
| `validate_settings.py` | Validate required DevBuddy settings keys and schema version. | `python scripts/validate_settings.py settings.yaml` |
| `init_project_memory.py` | Create a minimal, non-overwriting project-memory layout. | `python scripts/init_project_memory.py --project-root <project-root> --dry-run` or `--root <approved-external-memory-root>` |
| `bootstrap_knowledge.py` | Read-only scan of repository manifests, runtimes, source/test directories, commands, and architecture references; optionally write reviewable core observations. | `python scripts/bootstrap_knowledge.py --project-root <project-root> --dry-run` then `--apply` after review |
| `validate_knowledge.py` | Validate core memory files and typed knowledge metadata/IDs. | `python scripts/validate_knowledge.py --project-root <project-root>` or `--root <approved-external-memory-root>` |
| `task_memory.py` | Create/resume task ledgers, persist bounded handoffs, reserve/commit/release owner writes, check a specialist scope, and save read-only analysis. | `python scripts/task_memory.py --help` |
| `check_adapter_checklists.py` | Verify every common change ID appears in each adapter checklist and incomplete entries have remarks. | `python scripts/check_adapter_checklists.py --template templates/adapter-implementation-checklist.md <adapter-checklist> ...` |
| `check_manual_conformance.py` | Verify required bilingual manual pages, language metadata, version metadata, and stylesheet. | `python scripts/check_manual_conformance.py manual` |
| `check_semantic_conformance.py` | Detect drift in shared versions, roles, handoff fields, memory defaults, policy tokens, and platform transport mappings. | `python scripts/check_semantic_conformance.py` |
| `sync_adapter_checklist.py` | Add missing source checklist items to an adapter checklist without replacing existing entries. | `python scripts/sync_adapter_checklist.py templates/adapter-implementation-checklist.md <adapter-checklist>` |
| `sync_task_memory.py` | Copy the canonical task-memory protocol tool into both adapters. | `python scripts/sync_task_memory.py --dry-run` then without `--dry-run` after review |
| `verify_installed_adapters.py` | Verify installed Codex/Claude artifacts match the adapters; optionally exercise installed task-memory tools in a temporary project without a model call. | `python scripts/verify_installed_adapters.py --exercise-task-memory` |

Run `--help` before using unfamiliar options. Validation scripts are read-only. Checklist synchronisation writes only to the adapter checklist passed by the user-approved workflow; review the target and Git policy before running it.
