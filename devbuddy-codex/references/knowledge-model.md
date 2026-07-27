# Knowledge Model

## Memory root

Resolve `<project-root>/.devbuddy/settings.yaml` first. By default, that same `.devbuddy/` directory contains `settings.yaml`, `KnowledgeBase.md`, the other three core memory files, and the typed folders. A configured external `memory_root` is used directly; do not add another `.devbuddy/` wrapper there. Canonical memory is never global or temporary.

Initialise a project root with `scripts/init_project_memory.py --project-root <project-root> --dry-run` first, then without `--dry-run` after approval. Use `--root <approved-external-memory-root>` for an external root. The script never overwrites an existing file.

## Layout and entities

The memory root contains `Context.md`, `BusinessContext.md`, `DecisionLog.md`, and `KnowledgeBase.md` directly at its root, plus typed folders and `tasks/` for task ledgers. Every canonical entity has an immutable typed key such as `REQ-001`, `BR-001`, `API-001`, `DB-001`, or `ADR-001`, plus owner, source/evidence, verification date, and confidence metadata.

Use `templates/knowledge-entity.md` for new entities. Add `devbuddy-ref: KEY-001` comments only when the key already exists. A task ID, slice name, or invented placeholder is never a knowledge key.

## Impact and ownership

Before a change that may affect canonical memory, return an impact analysis naming affected keys, relationships, proposed updates, unresolved uncertainty, and the consequence of not updating. The Orchestrator asks the user for Knowledge Impact Approval and keeps the branch `waiting_user` until approval. Do not write canonical knowledge from the analysis alone.

Every canonical artefact has one owner and a ledger lock before modification. Reviewer and QA verify references and health; the Orchestrator routes findings rather than fabricating entities.

Run `scripts/validate_knowledge.py --project-root <project-root>` after material memory changes and before closure. Use `--root <approved-external-memory-root>` for an external root. It checks core files, entity metadata, key format, dates, confidence, and duplicate IDs.
