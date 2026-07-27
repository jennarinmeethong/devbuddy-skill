# Bundled Python Tools

All bundled scripts use only Python's standard library. Confirm `python` is available before use. Do not install packages automatically.

| Script | Purpose | Safe invocation |
|---|---|---|
| `validate_settings.py` | Validate required DevBuddy settings keys and schema version. | `python scripts/validate_settings.py settings.yaml` |
| `init_project_memory.py` | Create a minimal, non-overwriting project-memory layout. | `python scripts/init_project_memory.py --project-root <project-root> --dry-run` or `--root <approved-external-memory-root>` |
| `validate_knowledge.py` | Validate core memory files and typed knowledge metadata/IDs. | `python scripts/validate_knowledge.py <memory-root>` |
| `check_adapter_checklists.py` | Verify every common change ID appears in each adapter checklist and incomplete entries have remarks. | `python scripts/check_adapter_checklists.py --template templates/adapter-implementation-checklist.md <adapter-checklist> ...` |
| `check_manual_conformance.py` | Verify required bilingual manual pages, language metadata, version metadata, and stylesheet. | `python scripts/check_manual_conformance.py manual` |
| `sync_adapter_checklist.py` | Add missing source checklist items to an adapter checklist without replacing existing entries. | `python scripts/sync_adapter_checklist.py templates/adapter-implementation-checklist.md <adapter-checklist>` |

Run `--help` before using unfamiliar options. Validation scripts are read-only. Checklist synchronisation writes only to the adapter checklist passed by the user-approved workflow; review the target and Git policy before running it.
