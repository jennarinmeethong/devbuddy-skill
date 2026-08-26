import assert from "node:assert/strict"
import { mkdtemp, readFile, rm, stat } from "node:fs/promises"
import { spawnSync } from "node:child_process"
import { tmpdir } from "node:os"
import { join } from "node:path"
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
assert.ok(manifest.files.includes("scripts"))

const agentManifest = JSON.parse(await readFile(new URL("../plugin/devbuddy-core/opencode/plugin.json", import.meta.url)))
assert.equal(agentManifest.agents.length, 25)
for (const agent of agentManifest.agents) {
  const source = await readFile(new URL(`../plugin/devbuddy-core/opencode/${agent.slice(2)}`, import.meta.url), "utf8")
  assert.match(source, /mode: subagent|# DevBuddy Orchestrator/)
}

const presets = JSON.parse(await readFile(new URL("../plugin/devbuddy-core/opencode/agent-presets.json", import.meta.url)))
assert.deepEqual(presets.presets["product-delivery"].slice(0, 2), ["requirements-analyst", "ba-pm"])

const project = await mkdtemp(join(tmpdir(), "devbuddy-opencode-"))
const materializer = new URL("../plugin/devbuddy-core/opencode/scripts/materialize_agents.py", import.meta.url)
const preview = spawnSync("python3", [materializer.pathname, "--preset", "data-ai", "--project-root", project], { encoding: "utf8" })
assert.equal(preview.status, 0, preview.stdout + preview.stderr)
await assert.rejects(stat(join(project, ".opencode", "agents", "devbuddy", "data-analyst.md")))
const applied = spawnSync("python3", [materializer.pathname, "--preset", "data-ai", "--project-root", project, "--apply"], { encoding: "utf8" })
assert.equal(applied.status, 0, applied.stdout + applied.stderr)
await stat(join(project, ".opencode", "agents", "devbuddy", "data-analyst.md"))
await rm(project, { recursive: true, force: true })
