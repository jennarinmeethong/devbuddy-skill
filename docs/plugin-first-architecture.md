# DevBuddy Plugin-first Architecture

**Decision record:** DBY-PLUGIN-001 · **Status:** implemented for Claude Code · **Compatibility window:** DevBuddy 1.x

## Verified Claude Code packaging decision

Claude Code distributes the adapter as the `devbuddy-claude-code` Plugin in the `devbuddy` marketplace. The canonical package identifier is `devbuddy-claude-code`; its compatibility identifier is `claude-code`. The Plugin uses the official `.claude-plugin/plugin.json`, `skills/`, and `agents/` layout. Marketplace install, update, uninstall, and discovery use:

```text
claude plugin install devbuddy-claude-code@devbuddy --scope user
claude plugin update devbuddy-claude-code@devbuddy
claude plugin uninstall devbuddy-claude-code@devbuddy --keep-data
claude plugin list --json
```

After install or update, `/reload-plugins` makes the payload available. Claude Code namespaces Plugin skills, so the supported explicit entrypoint is `/devbuddy-claude-code:devbuddy`, not the legacy unnamespaced `/devbuddy`. The old command remains only in the compatibility installer through 1.x.

## Compatibility matrix

| Host | Package/platform ID | Entry point | Dispatch/model/effort | Discovery and lifecycle |
|---|---|---|---|---|
| Codex | `codex` | `$devbuddy` | Generated Codex adapter; explicit model and reasoning-effort transport | `codex plugin list`; start a new thread after install or update |
| Claude Code | `claude-code` | `/devbuddy-claude-code:devbuddy` | Agent tool; explicit approved model; generated role/effort agents | `claude plugin list --json`, `/reload-plugins`, `claude plugin update/uninstall` |
| OpenCode | `opencode` | OpenCode adapter entry point | Existing OpenCode Plugin transport | Existing OpenCode Plugin workflow |

Every adapter uses `devbuddy-core` as its policy dependency. The Codex and Claude package source maps generate host commands and adapter assets from the recognized source directories; each package manifest records its transport contract. `disable-model-invocation: true` preserves Claude's explicit gate; Codex keeps the `$devbuddy` explicit entrypoint. Missing agents, models, effort, `rtk_required`, or approvals still fail closed.

Profiles select exactly one host when they declare `hosts`; the resolver rejects a different `--platform`. Existing profiles without `hosts` remain compatible and are filtered by each package's compatibility declaration.

The optional `devbuddy-database-core` package and every
`devbuddy-database-<engine>` adapter support all three platform IDs: `codex`,
`claude-code`, and `opencode`. Their execution policy is host-neutral: it
remains read-only and requires a selected adapter, a local least-privilege
principal, and target-specific Tier 2 approval.

## Runtime ownership inventory

| Asset boundary | Classification | Owner | Installation target |
|---|---|---|---|
| `skills/devbuddy-core/` | Portable policy | `devbuddy-core` | Bundled package source only |
| `skills/devbuddy-database/` | Portable policy | `devbuddy-database-core` | Bundled package source only |
| `plugin/devbuddy-claude-code/skills`, `agents`, policy references, schemas, and delivery scripts | Host adapter payload | `devbuddy-claude-code` | Claude Plugin cache via marketplace |
| `plugin/devbuddy-core/opencode/` | Host adapter payload | `devbuddy-core` | OpenCode Plugin location |
| `plugin/devbuddy-database-*/tool.json` and database runtime | Optional Tier 2 runtime | Database core and selected engine adapter | `.devbuddy/tools/` only after manifest/approval validation |
| `scripts/generate_packages.py`, validators, build/release scripts | Source-maintenance utility | Repository only | Never installed as delivery runtime |
| `devbuddy-claude/scripts/install_claude_adapter.py` and Codex equivalent | Deprecated compatibility shim | Legacy adapter | Existing host configuration, explicit legacy opt-in only |
| `.devbuddy/` | Workspace state | User workspace | Never package artifact |

Package generation emits a source revision and file hashes in `generation-report.json`; `check_package_drift.py` detects changes. Package and secret-exclusion validation prohibit credentials, knowledge, task state, and user-specific configuration in delivery artifacts.

## Migration and removal schedule

1. **1.x (current):** existing standalone installations keep working. Running either installer reports migration first; the historical `--apply` path remains compatible (and `--legacy-install` is an optional explicit spelling). No migration command overwrites or removes a host file.
2. **Before 2.0:** users install the marketplace Plugin, verify it with `claude plugin list --json`, run `/reload-plugins`, and invoke the namespaced command. Roll back by uninstalling with `--keep-data`; the legacy install remains untouched.
3. **2.0 removal gate:** remove standalone installation only after clean and legacy migration dry runs, unknown-file conflict tests, rollback evidence, package discovery evidence, and release validation have passed for the supported host versions. This repository does not collect usage telemetry; release approval must attach equivalent deployment evidence.
