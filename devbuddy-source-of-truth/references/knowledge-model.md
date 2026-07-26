# Knowledge Model

## Memory root

Resolve `<project-root>/.devbuddy/settings.yaml` first. Its `memory_root` may point to an external approved location. Canonical memory is never global or temporary.

```text
<memory-root>/
|- Context.md
|- BusinessContext.md
|- DecisionLog.md
|- KnowledgeBase.md
|- domains/ features/ requirements/ flows/ business-rules/ screens/
|- technical/{architecture,apis,database,events,integrations}/
|- tests/ decisions/ releases/ incidents/
`- tasks/
```

## Entity metadata

Use `templates/knowledge-entity.md`. IDs are immutable and globally unique. Recommended prefixes: `DOM`, `FEAT`, `REQ`, `FLOW`, `BR`, `SCR`, `API`, `DB`, `EVT`, `TEST`, `ADR`, `REL`, and `INC`.

## Ownership

- Architect: technical context, architecture, contracts, ADRs.
- BA/PM: business context, requirements, flows, business rules.
- QA: test strategy, cases, evidence, traceability.
- DevOps/SRE: releases, runbooks, incidents, operational context.
- DBA/Data: database/data models, migrations, integrity evidence.

Owners update canonical memory only after user-approved Knowledge Impact Approval. Keep current facts canonical; mark superseded decisions rather than deleting history.

## Impact approval

Before a potentially relevant implementation change, identify affected keys, references, relationships, evidence, proposed updates, and consequences. The Orchestrator presents this to the user. Keep the branch `waiting_user` until the user approves or clarifies it.

## Health and migration

Validate IDs, YAML metadata, relations, `devbuddy-ref` comments, owners, sources, dates, and confidence. Schema/key/folder migrations need a versioned plan, approved backup, rollback, user approval, and validation.
