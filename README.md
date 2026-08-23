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
python3 devbuddy-source-of-truth/scripts/sync_adapter_skills.py --check
python3 devbuddy-source-of-truth/scripts/validate_skill_contract.py
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

Bootstrap writes only `Context.md` and `KnowledgeBase.md` after explicit `--apply`, never overwrites non-empty existing files, and does not invent typed canonical entities or business policy. Business context and decisions belong in typed knowledge entities, so legacy `BusinessContext.md` and `DecisionLog.md` are no longer created or required. For a dedicated knowledge repository, register each source repository in its `.devbuddy/settings.yaml` and run bootstrap once per `--project-id`. Runtime task inputs and temporary artifacts must remain below `.devbuddy` on every supported platform.

## Plugin packages and profiles

The additive plugin implementation lives in `plugin/`, portable skills in `skills/`, and package composition profiles in `profiles/`. Existing adapters remain source-preserved.

Run the safety checks with the bundled Python runtime (or any Python 3.11+):

```text
python scripts/check_source_preservation.py
python scripts/generate_packages.py --apply
python scripts/check_package_drift.py
python scripts/validate_packages.py
python scripts/scan_secret_exclusion.py
python scripts/profile_resolver.py profiles/data-postgresql.yaml
python scripts/workspace.py init --devbuddy-root <workspace>/.devbuddy --apply
python scripts/workspace.py validate --devbuddy-root <workspace>/.devbuddy
python scripts/build_plugin.py --runtime win-x86 --apply
python scripts/build_plugin.py --runtime win-x64 --apply
python scripts/build_plugin.py --runtime win-arm64 --apply
python scripts/build_plugin.py --runtime linux-x64 --apply
python scripts/build_plugin.py --runtime linux-arm64 --apply
python scripts/build_plugin.py --runtime osx-x64 --apply
python scripts/build_plugin.py --runtime osx-arm64 --apply
node tests/test_opencode_adapter.mjs
python scripts/release_validate.py
```

`profile_resolver.py` is dry-run by default. Writing a selected composition requires `--apply --devbuddy-root <workspace>/.devbuddy`, and it refuses to overwrite an existing composition. `build_plugin.py` is the plugin-creation build step: it publishes the single self-contained database adapter with all supported database drivers into `plugin/devbuddy-database-core/runtime/<runtime>/`; database engine manifests select that shared, policy-enforced executable. Database requests must pass `scripts/validate_database_request.py` before an adapter attempts execution; the policy gate complements, never replaces, a least-privilege read-only database principal.
