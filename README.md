# DevBuddy Skill

DevBuddy is a policy-driven software-delivery orchestrator with platform adapters for Claude Code and Codex.

## Repository layout

- `devbuddy-source-of-truth/` — common policies, roles, memory model, contracts, and checklist template
- `devbuddy-claude/` — Claude Code `/devbuddy` adapter with 27 role/effort agents
- `devbuddy-codex/` — Codex `$devbuddy` adapter with one role profile per role and per-call model/effort selection

## Validate

Run from the repository root:

```text
python3 devbuddy-source-of-truth/scripts/validate_settings.py devbuddy-source-of-truth/settings.yaml
python3 devbuddy-source-of-truth/scripts/check_adapter_checklists.py --template devbuddy-source-of-truth/templates/adapter-implementation-checklist.md devbuddy-claude/adapter-implementation-checklist.md devbuddy-codex/adapter-implementation-checklist.md
python3 devbuddy-source-of-truth/scripts/check_semantic_conformance.py
python3 -m unittest discover devbuddy-source-of-truth/tests -v
python3 -m unittest discover devbuddy-claude/tests -v
python3 -m unittest discover devbuddy-codex/tests -v
```

## Install

Claude uses a dry-run-first installer:

```text
python3 devbuddy-claude/scripts/install_claude_adapter.py
python3 devbuddy-claude/scripts/install_claude_adapter.py --apply
```

Codex uses the equivalent installer:

```text
python3 devbuddy-codex/scripts/install_codex_adapter.py
python3 devbuddy-codex/scripts/install_codex_adapter.py --apply
```

Both installers accept a platform configuration root and refuse non-DevBuddy file collisions. Initialise a selectable `.devbuddy` workspace with repeatable `--project id=path` values. Shared canonical knowledge lives under `.devbuddy/knowledge-base/`; task ledgers and project-local Python tools live under `.devbuddy/tasks/` and `.devbuddy/tools/`.

Prepare a reviewable knowledge inventory from an existing repository with the read-only-by-default bootstrap:

```text
python3 devbuddy-source-of-truth/scripts/init_project_memory.py --devbuddy-root <workspace>/.devbuddy --project fe=../frontend --project be=../backend --dry-run
python3 <workspace>/.devbuddy/tools/bootstrap_knowledge.py --devbuddy-root <workspace>/.devbuddy --project-id fe --dry-run
```

Bootstrap writes only `Context.md` and `KnowledgeBase.md` after explicit `--apply`, never overwrites non-empty existing files, and does not invent typed canonical entities or business policy. For a dedicated knowledge repository, register each source repository in its `.devbuddy/settings.yaml` and run bootstrap once per `--project-id`.
