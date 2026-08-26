---
name: devbuddy
description: Deprecated DevBuddy compatibility entrypoint. It only guides migration to the DevBuddy Claude Code Plugin.
disable-model-invocation: true
argument-hint: migrate <workspace>
---

# Legacy DevBuddy migration shim

This standalone skill is migration-only. Do not use it for delivery work, do
not dispatch legacy agents, and never invoke legacy SQL or custom tools.

For `/devbuddy migrate <workspace>`, first make a read-only inventory of the
old skill and `<workspace>/.devbuddy`. Install and reload the
`devbuddy-claude-code` Plugin, then use
`/devbuddy-claude-code:devbuddy migrate <workspace>`. The Plugin workflow
maps legacy documents to typed knowledge documents, retains the old documents
as evidence, generates collision-resistant entity keys, previews every file
move, and requires explicit approval for every apply step.

For any other `/devbuddy` request, tell the user to install the Plugin and use
`/devbuddy-claude-code:devbuddy` instead. Do not attempt a compatibility
delivery workflow.
