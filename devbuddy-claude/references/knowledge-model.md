# Knowledge Model

## Memory root

Default root is `<project-root>/.devbuddy/`, containing `settings.yaml`, the four core memory files, typed folders, and task ledgers. Project settings may point directly elsewhere, including an Obsidian vault; do not add another `.devbuddy` wrapper to an external path. Resolve the locator before any read or write. Never use temporary or global storage for project knowledge.

Initialise a project root with `scripts/init_project_memory.py --project-root <project-root> --dry-run` first, then without `--dry-run` once the user approves the shown plan. Use `--root <approved-external-memory-root>` for an external path. The script never overwrites an existing file.

## Layout

```text
<memory-root>/
|- Context.md            # current technical understanding
|- BusinessContext.md    # current business understanding
|- DecisionLog.md        # decisions, rationale, alternatives, supersession
|- KnowledgeBase.md      # verified reusable lessons and anti-patterns
|- domains/ features/ requirements/ flows/ business-rules/ screens/
|- technical/{architecture,apis,database,events,integrations}/
|- tests/ decisions/ releases/ incidents/
`- tasks/                # one ledger per task; orchestration state, not knowledge
```

The four root files are concise canonical entry points; durable detail lives in the typed folders. Revise them rather than appending indefinitely. Mark superseded decisions with their successor and rationale instead of deleting them.

## Knowledge keys

Every canonical entity carries one immutable, globally unique key in its YAML `id`, using a type prefix: `DOM`, `FEAT`, `REQ`, `FLOW`, `BR`, `SCR`, `API`, `DB`, `EVT`, `TEST`, `ADR`, `REL`, `INC`. A retired key is never reused for a different entity.

Entities also record `owner`, `source` or evidence reference, `last_verified`, `confidence`, and relations. Do not assign a confidence level without evidence — unverified information stays unknown rather than becoming canonical knowledge. Use `templates/knowledge-entity.md`.

## Code references

When code, configuration, a migration, a test, or automation enforces, transforms, depends on, or verifies a knowledge entity, add a source comment naming its key:

```text
devbuddy-ref: BR-001, DB-042
```

Place it at the smallest meaningful scope — the function, class, query, migration, config block, or test that carries the relationship — not on every line. Comments contain keys only, never sensitive values or copied business data; the explanation lives in the linked entity.

Developer adds and updates these references during implementation. Reviewer and QA verify them. The Orchestrator records the declared relationships in the ledger.

## Knowledge Impact Approval

Before any change that may affect the knowledge platform, the responsible role analyses the impact and returns: the proposed change, affected keys and entities, the relationship or evidence for each impact, proposed knowledge updates, unresolved uncertainty, and the consequence of not updating.

The Orchestrator then asks the user to confirm or clarify, and holds the branch in `waiting_user`. Do not implement the change, and do not create, update, or remove canonical knowledge, from the impact analysis alone. After the user answers, record the decision in the ledger and `DecisionLog.md` where applicable; the owner role updates only what the user approved, then revalidates keys, references, and links.

A no-impact conclusion is a finding too — record the scope checked. Incomplete evidence is uncertainty, not a no-impact result.

## Ownership and locking

Every canonical artefact has exactly one owner role. Others contribute analysis, review, or proposed patches through handoffs. Before modifying an artefact, acquire a ledger lock naming the artefact/key, owner role, task ID, scope, and expiry. Two active tasks never mutate the same artefact concurrently; a conflicting task waits, is re-scoped, or goes to the user. A stale or uncertain lock is reported, never silently overridden.

## Health checks

Run `scripts/validate_knowledge.py <memory-root>` after material changes and before closure. It checks key format, uniqueness, and required metadata. Also look for broken links, missing owners, stale or superseded decisions, requirements and business rules without linked tests, APIs without ownership, and releases without evidence.

Report each finding with the affected entity, the inconsistent relationship, the impact, and the owner role. Route remediation through the Orchestrator; never fabricate missing knowledge to make a check pass.
