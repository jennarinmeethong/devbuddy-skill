# DevBuddy Claude Code adapter

DevBuddy is an explicitly invoked Claude Code skill for policy-driven software delivery. The Orchestrator is the main session; it assesses the task, selects the role graph, and dispatches specialist subagents with an approved model and effort level recorded per slice.

Two platform mechanics shape this adapter:

- **Effort is fixed per agent definition.** Claude Code sets reasoning effort in the `effort` frontmatter field, not as a per-call parameter, so the adapter ships one subagent per role and effort tier — 9 roles x 6 tiers = 54 definitions. Choosing `devbuddy-<role>-<effort>` *is* choosing the effort level.
- **Model is chosen per call.** The Agent tool's `model` parameter overrides frontmatter, so agent definitions deliberately leave `model` unset and `scripts/validate_skill_metadata.py` rejects any that pin one. Minimum-sufficient model selection stays a live decision the ledger records.

`SKILL.md` carries `disable-model-invocation: true`, so only an explicit `/devbuddy` opens the workflow. The approval gates assume a user who chose to start a delivery task.

## Install

Preview the exact file list first:

```bash
python3 scripts/install_claude_adapter.py
```

Apply only after reviewing the dry run:

```bash
python3 scripts/install_claude_adapter.py --apply
```

The default target is `~/.claude`: the skill lands in `skills/devbuddy/` and the 54 definitions in `agents/`. Use `--claude-root <path>` for another approved configuration root. The installer refuses to overwrite any file it cannot identify as a DevBuddy artefact; `--replace-recognized-skill` narrows that refusal to a skill root that already identifies itself as DevBuddy. Restart or refresh the session afterwards so `/devbuddy` and the `devbuddy-*` agents load.

Only the self-contained scripts are installed (`SKILL_SCRIPTS` in the installer). The conformance and manual checkers compare this adapter against `devbuddy-source-of-truth/`, which no install contains, so they stay repository-only.

## Configure a workspace

Select a `.devbuddy` workspace and register repositories with stable project IDs. Shared canonical knowledge lives in `knowledge-base/`; task ledgers and the runtime tools copied from `templates/project-tools/` live in `tasks/` and `tools/`. The default Claude allowlist is `claude-haiku-4.5`, `claude-sonnet-5`, `claude-opus-5`, and `claude-fable`, with six effort levels from `low` through `ultracode`; a workspace may narrow that allowlist but never widen it silently.

```bash
python3 scripts/init_project_memory.py --devbuddy-root <workspace>/.devbuddy --project fe=../frontend --project be=../backend --dry-run
```

Re-run without `--dry-run` after reviewing the planned writes, then:

```bash
python3 <workspace>/.devbuddy/tools/validate_project_settings.py <workspace>/.devbuddy/settings.yaml
python3 <workspace>/.devbuddy/tools/bootstrap_knowledge.py --devbuddy-root <workspace>/.devbuddy --project-id fe --dry-run
python3 <workspace>/.devbuddy/tools/validate_knowledge.py --devbuddy-root <workspace>/.devbuddy
```

Bootstrap appends a labelled observation section for one registered project without replacing another project's observations, and never invents typed canonical entities. When `settings_version` is stale, use `--upgrade-settings --dry-run` and then `--upgrade-settings` to add missing current defaults without overwriting workspace values. Use `--migrate-layout --dry-run` before moving a legacy layout into `knowledge-base/`.

## Register a custom tool

A workspace may own tools of its own — a read-only database query executable, a log fetcher, a schema differ. Declare each one in the workspace `custom_tools` list with an approved runtime, so the Orchestrator knows which executables it may call, the shape of each call, and where the host's credentials live:

```yaml
tools:
  approved_custom_tool_runtimes: [python, dotnet]
custom_tools:
  - name: readonly_database_query
    runtime: dotnet
    manifest: tools/db-query-tool/tool.json
    secret_file: tools/db-query-tool/appsettings.json
```

`validate_project_settings.py` checks the manifest declares `name`, `description`, `command`, `inputSchema`, and `outputSchema`, that the runtime is approved, that a declared `secret_file` has a committed `*.template.*` sibling, and that no credential-shaped value has been pasted into the manifest. An unregistered or platform-unavailable tool is a `waiting_user` block. Read [references/custom-tools.md](references/custom-tools.md) first.

### Bundled custom tools

`templates/project-tools/<name>/` holds ready-made custom tools. They are opt-in: unlike the five Python runtime tools, a bundled tool may need another runtime and a build step, so workspace initialisation never seeds one silently.

```bash
python3 scripts/init_project_memory.py --devbuddy-root <workspace>/.devbuddy --seed-custom-tool db-query-tool --dry-run
```

Re-run without `--dry-run` to copy it into `<workspace>/.devbuddy/tools/`. Seeding refuses to overwrite an existing copy, because the host may have edited or built inside it. Build output (`bin/`, `obj/`, `releases/`) and any host-owned `appsettings.json` or generated `tool.json` are never copied in either direction.

`db-query-tool` is a self-contained .NET 8 read-only SQL Server query executable: one JSON request on stdin, one JSON response on stdout, a single validated `SELECT`/CTE per call, and rejection of writes, DDL, execution, temporary and cross-database sources, hints, and `SELECT INTO` before anything reaches the database. After seeding:

```bash
cd <workspace>/.devbuddy/tools/db-query-tool
cp appsettings.template.json appsettings.json    # then fill in your read-only principal
./build-release.sh
```

The build produces `osx-arm64`, `win-x64`, and `linux-x64` bundles, each with a generated `tool.json` whose `command` points at that platform's executable — that generated manifest is the one you register in `custom_tools`. Run `dotnet test` in `db-query-tool.tests/` to check the SQL guard before trusting it. Requires the .NET 8 SDK; nothing is installed for you.

## Verify an install

These ship with the skill and run from the skill root:

```bash
python3 scripts/validate_skill_metadata.py .
python3 scripts/run_scenarios.py tests/scenarios.json
```

## Develop this adapter

Run from this directory, with the `devbuddy-source-of-truth/` sibling present:

```bash
python3 scripts/generate_agents.py --check
python3 scripts/validate_skill_metadata.py . --exercise-task-memory
python3 scripts/check_adapter_conformance.py
python3 scripts/validate_manual.py manual
python3 -m unittest discover tests -v
```

`generate_agents.py` regenerates the 54 definitions from `roles/`; `--check` asserts the committed files still match. Cross-adapter conformance lives in the source repository:

```bash
python3 ../devbuddy-source-of-truth/scripts/check_semantic_conformance.py
python3 ../devbuddy-source-of-truth/scripts/check_adapter_checklists.py --template ../devbuddy-source-of-truth/templates/adapter-implementation-checklist.md adapter-implementation-checklist.md ../devbuddy-codex/adapter-implementation-checklist.md
```

## Use

```text
/devbuddy <task>
/devbuddy loop <task>
/devbuddy analyze <project>
```

Pass the complete task after the command; the Orchestrator picks the route. The `<role>` and `owner` forms are advanced overrides for deliberately constraining routing. If a required `devbuddy-<role>-<effort>` subagent is missing, or either the model or the effort level cannot be verified, the slice becomes `waiting_user` — the Orchestrator never substitutes itself for a specialist, because that would remove the independent verification the approval gates rely on.

## Layout

| Path | Contents |
|---|---|
| `SKILL.md` | Orchestrator entrypoint, required sequence, dispatch blocks, core policy |
| `settings.yaml` | Adapter identity, governance, orchestration transport, approved model and effort allowlists |
| `agents/` | 54 generated `devbuddy-<role>-<effort>.md` subagent definitions |
| `roles/` | Orchestrator plus 9 canonical role workflows, the generator's source |
| `references/` | Dispatch contract, policy, routing, settings, knowledge model, task memory, loop engineering, custom tools |
| `schemas/` | JSON Schema for a project's `.devbuddy/settings.yaml` |
| `scripts/` | Installer, generator, validators, workspace initializer, task-memory tool |
| `templates/` | Slice record, task ledger, knowledge entity, the `project-tools/` runtime payload, and opt-in bundled custom tools |
| `tests/` | Workspace, task-memory, settings, metadata, and installer regression tests plus static scenarios |
| `manual/` | Bilingual Thai/English offline manual |
