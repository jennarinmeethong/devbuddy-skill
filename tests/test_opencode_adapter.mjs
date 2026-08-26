import assert from "node:assert/strict"
import { readFile } from "node:fs/promises"
import plugin from "../plugin/devbuddy-core/opencode/index.js"

const hooks = new Map()
const ctx = {
  session: { hook: async (name, callback) => hooks.set(name, callback) },
  tool: { hook: async (name, callback) => hooks.set(name, callback) },
}
await plugin.setup(ctx)
assert.equal(plugin.id, "devbuddy.core")
const context = { system: "host policy" }
await hooks.get("context")(context)
assert.match(context.system, /DevBuddy core contract is active/)
await assert.rejects(() => hooks.get("execute.before")({ tool: "devbuddy.database.postgresql.read", input: {} }), /database_id/)
await hooks.get("execute.before")({ tool: "devbuddy.database.postgresql.read", input: { database_id: "billing", approval: { target: "billing", approved: true } } })
const result = {}
await hooks.get("execute.after")({ tool: "devbuddy.database.postgresql.read", result })
assert.equal(result.untrusted_result, true)

const manifest = JSON.parse(await readFile(new URL("../plugin/devbuddy-core/opencode/package.json", import.meta.url)))
assert.equal(manifest.name, "@devbuddy/opencode-plugin")
assert.equal(manifest.type, "module")
assert.equal(manifest.exports, "./index.js")
assert.ok(manifest.files.includes("index.js"))

const agentManifest = JSON.parse(await readFile(new URL("../plugin/devbuddy-core/opencode/plugin.json", import.meta.url)))
assert.equal(agentManifest.agents.length, 25)
for (const agent of agentManifest.agents) {
  const source = await readFile(new URL(`../plugin/devbuddy-core/opencode/${agent.slice(2)}`, import.meta.url), "utf8")
  assert.match(source, /mode: subagent|# DevBuddy Orchestrator/)
}
