# Knowledge Model

## Memory root

Resolve the selected `.devbuddy/settings.yaml` first. A DevBuddy workspace may register multiple source repositories under `workspace.projects`; relative paths resolve from the parent of `.devbuddy`. Canonical memory is shared below `.devbuddy/knowledge-base/`, while task state and executable tools remain in `.devbuddy/tasks/` and `.devbuddy/tools/`.

```text
<devbuddy-root>/
|- settings.yaml
|- knowledge-base/
|  |- Context.md
|  |- KnowledgeBase.md
|  |- domains/ features/ requirements/ flows/ business-rules/ screens/
|  |- technical/{architecture,apis,database,events,integrations}/
|  `- tests/ decisions/ releases/ incidents/
|- tasks/
`- tools/
```

## Runtime-tool boundary

After bootstrap, delivery tasks invoke only the five built-in scripts directly below `<devbuddy-root>/tools/`: `init_project_memory.py`, `bootstrap_knowledge.py`, `task_memory.py`, `validate_project_settings.py`, and `validate_knowledge.py`. Confirm their `tools/manifest.json` hashes before each call. The exception is the one-time installed-skill initializer that creates this folder; it is available only for an explicitly requested workspace setup and must start with `--dry-run`.

The automatic DevBuddy allowance covers help, validation, dry-run, repository inventory, and task-lifecycle calls for a current user-started task. It does not suppress a Codex or Claude platform permission prompt, authorize any external/destructive action, or remove the required gate for workspace writes and canonical knowledge.

## Entity metadata

Use `templates/knowledge-entity.md`. IDs are immutable and globally unique. Every entity has a non-empty `project_ids` list; one shared fact may name multiple registered projects. Recommended prefixes: `DOM`, `FEAT`, `REQ`, `FLOW`, `BR`, `SCR`, `API`, `DB`, `EVT`, `TEST`, `ADR`, `REL`, and `INC`.

New IDs use `<prefix>-<suffix>`, where `<suffix>` is 8 random characters from Crockford's Base32 alphabet (`0-9A-HJKMNP-TV-Z`, excluding `I L O U` to avoid misreads). Generate one independently per entity, for example: `python3 -c "import secrets; print(''.join(secrets.choice('0123456789ABCDEFGHJKMNPQRSTVWXYZ') for _ in range(8)))"`. This lets contributors on separate branches or repositories mint IDs without a shared counter, so two people never collide when their knowledge-base changes merge. Existing sequential IDs (e.g. `REQ-001`) are immutable and are never renamed to the new style.

## Index

Keep `Index.md` at the knowledge-base root: one line per entity, `- <id>: <one-sentence summary>`, seeded from `templates/knowledge-index.md`. Update its row in the same change that creates or edits the entity — this is what lets a reader find the right key without opening files that turn out irrelevant, and a stale row is worse than a missing one. `validate_knowledge.py` checks both directions: every indexed id must resolve to a real entity, and every entity must have an index row.

## Ownership

- Architect: technical context, architecture, contracts, ADRs.
- BA/PM: business context, requirements, flows, business rules.
- QA: test strategy, cases, evidence, traceability.
- DevOps/SRE: releases, runbooks, incidents, operational context.
- DBA/Data: database/data models, migrations, integrity evidence.

Owners propose canonical-memory changes only after user-approved Knowledge Impact Approval. The Orchestrator/`owner` is the sole canonical-memory writer and applies approved proposals with evidence. Keep current facts canonical; mark superseded decisions rather than deleting history.

`Context.md` and `KnowledgeBase.md` are the only bootstrap files. They hold reviewable inventory and shared observations, respectively. Put durable business context in the typed `domains/`, `requirements/`, `flows/`, and `business-rules/` entities; put durable decisions in typed `decisions/` entities. `BusinessContext.md` and `DecisionLog.md` from an older layout are optional legacy notes, not required inputs and never created or updated automatically.

## Impact approval

Before a potentially relevant implementation change, identify affected keys, references, relationships, evidence, proposed updates, and consequences. The Orchestrator presents this to the user. Keep the branch `waiting_user` until the user approves or clarifies it.

## Health and migration

Validate IDs, YAML metadata, relations, the Index, `devbuddy-ref` comments, owners, sources, dates, and confidence. Schema/key/folder migrations need a versioned plan, approved backup, rollback, user approval, and validation.

Use `analyze <project-id>` or `.devbuddy/tools/bootstrap_knowledge.py --devbuddy-root <root> --project-id <id> --dry-run` to prepare a reviewable repository inventory. It may identify manifests, runtimes, likely source/test directories, candidate commands, and architecture references, but it must not infer business intent or create typed knowledge entities. After approval, `--apply` appends a project-labelled observation section without replacing observations for other projects.
