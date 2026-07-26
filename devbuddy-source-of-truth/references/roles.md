# Role Catalogue

Read the relevant file in `roles/` before dispatching or changing a role.

| Role | Owns | Primary outputs |
|---|---|---|
| Orchestrator | task control plane | ledger, graph, routing, approval state |
| BA/PM | business scope | requirements, rules, flows, priority |
| UX/UI | interaction design | journeys, screens, states |
| Architect | technical design | architecture, contracts, ADRs |
| Developer | implementation | code, scoped configuration, developer tests |
| QA | independent quality | strategy, cases, evidence, defects |
| Security | security controls | threat model, findings, review evidence |
| DevOps/SRE | operations | pipelines, runbooks, releases, incidents |
| DBA/Data | data safety | schema/data plans, migration evidence |
| Reviewer | independent review | findings and review outcome |

The Orchestrator coordinates only. Every specialist reads relevant verified context, works within authority, self-checks, updates approved knowledge, and returns `templates/handoff.md`.
