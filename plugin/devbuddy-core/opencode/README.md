# DevBuddy OpenCode adapter

Install directly from this repository with OpenCode's Git package syntax:

```text
opencode plugin 'github:jennarinmeethong/devbuddy-skill#v1.0.2::path:plugin/devbuddy-core/opencode' --global
```

The `::path:` selector installs this adapter directory rather than the whole
monorepo. Pin an approved release tag or full commit SHA in place of `v1.0.2`.
Omit `--global` to install into the current project. For local discovery,
place or link this directory's `index.js` in `.opencode/plugins/`. For npm
distribution, publish `@devbuddy/opencode-plugin` and add the package name to
OpenCode's plugin configuration.

The adapter registers context and tool lifecycle hooks. It does not select a model or embed provider transport logic. Database operations require `database_id` and a target-specific approval object before the host tool executes.

The package also ships an Orchestrator plus 24 specialist Markdown-agent presets. OpenCode discovers project agents below `.opencode/agents/`, so copy or link only the selected presets into `.opencode/agents/devbuddy/` after resolving a DevBuddy profile; their IDs then become `devbuddy/<role>`. The profiles `product-delivery`, `cloud-operations`, `data-ai`, and `support-knowledge` expose the intended specialist sets. These files are policy prompts, not permission grants.
