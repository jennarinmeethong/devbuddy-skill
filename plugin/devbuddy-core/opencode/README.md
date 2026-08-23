# DevBuddy OpenCode adapter

For local discovery, place or link this directory’s `index.js` in `.opencode/plugins/`. For npm distribution, publish `@devbuddy/opencode-plugin` and add the package name to OpenCode’s plugin configuration.

The adapter registers context and tool lifecycle hooks. It does not select a model or embed provider transport logic. Database operations require `database_id` and a target-specific approval object before the host tool executes.
