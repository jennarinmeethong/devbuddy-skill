# DevBuddy platform-neutral guide

DevBuddy separates the delivery contract from host mechanics. The portable contract covers policy, task evidence, approval gates, role ownership, and package/profile composition. Codex, Claude Code, and OpenCode adapters only map installation, invocation, and subagent transport.

## Use a profile on any supported host

Choose the host adapter first, then layer one or more portable profiles into the workspace. The resolver is read-only by default and prints the exact package and role selection before it writes anything.

```text
python3 scripts/profile_resolver.py --list
python3 scripts/profile_resolver.py product-delivery --platform <host>
python3 scripts/profile_resolver.py product-delivery --platform <host> --devbuddy-root <workspace>/.devbuddy --apply
python3 scripts/profile_resolver.py --add-profile data-ai --platform <host> --devbuddy-root <workspace>/.devbuddy --apply
python3 scripts/profile_resolver.py --remove-profile data-ai --platform <host> --devbuddy-root <workspace>/.devbuddy --apply
python3 scripts/profile_resolver.py --status --devbuddy-root <workspace>/.devbuddy
```

`<host>` is `codex`, `claude-code`, or `opencode`. The resolver rejects a profile or package that is incompatible with the selected host. Removing a profile recalculates the complete graph, so a shared dependency stays installed until the last profile using it is removed.

## Role presets

The portable role catalogue includes compatibility roles plus specialised presets for Requirements Analysis; Frontend and Backend Engineering; Code Review; DevOps, Cloud Infrastructure, and Site Reliability; Data Pipeline, Data Analysis, and Model Evaluation; Vulnerability Scanning, Compliance & Policy, and Security Incident Response; Helpdesk Support; and Knowledge Base curation.

Use `product-delivery`, `cloud-operations`, `data-ai`, or `support-knowledge` to expose the relevant role set to the Orchestrator. Profiles describe selection only; they do not grant tools, cost, write, production, data, or external permissions.

For OpenCode, materialize the selected role presets into the project directory after installing the adapter:

```text
python3 <plugin-directory>/scripts/materialize_agents.py --preset data-ai --project-root <project>
python3 <plugin-directory>/scripts/materialize_agents.py --preset data-ai --project-root <project> --apply
```

The first command is a dry run and the second refuses to overwrite an existing agent file.

## Host mapping

| Concern | Codex | Claude Code | OpenCode |
|---|---|---|---|
| Portable contract | `devbuddy-core` | `devbuddy-core` | `devbuddy-core` |
| Native adapter | `devbuddy-codex` | `devbuddy-claude-code` | `plugin/devbuddy-core/opencode` |
| Invocation | `$devbuddy <task>` | `/devbuddy-claude-code:devbuddy <task>` | Host adapter entry point |
| Profile composition | `scripts/profile_resolver.py` | `scripts/profile_resolver.py` | `scripts/profile_resolver.py` |

Keep host-specific install, update, reload, and discovery commands in the host installation section of the README. Do not embed one host's command syntax in portable policies, role definitions, profile files, schemas, or task evidence.
