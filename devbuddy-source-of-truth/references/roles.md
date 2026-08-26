# Role Catalogue

Read the relevant file in `roles/` before dispatching or changing a role.

| Role | Owns | Primary outputs |
|---|---|---|
| Orchestrator | task control plane | ledger, graph, routing, approval state |
| BA/PM | business scope | requirements, rules, flows, priority |
| Requirements Analyst | requirements clarity | stories, acceptance criteria, traceability |
| UX/UI | interaction design | journeys, screens, states |
| Architect | technical design | architecture, contracts, ADRs |
| Developer | implementation | code, scoped configuration, developer tests |
| Frontend Engineer | client implementation | accessible UI, client tests, UI evidence |
| Backend Engineer | service implementation | APIs, service tests, operational evidence |
| QA | independent quality | strategy, cases, evidence, defects |
| Security | security controls | threat model, findings, review evidence |
| Vulnerability Scanner | vulnerability discovery | triaged findings and remediation evidence |
| Compliance & Policy | control conformance | control mapping, gaps, audit evidence |
| Security Incident Response | security response | incident timeline, containment, recovery |
| DevOps/SRE | operations | pipelines, runbooks, releases, incidents |
| DevOps Engineer | delivery automation | CI/CD, deployment and rollback evidence |
| Cloud Infrastructure | cloud platform | IaC, resilience and recovery plan |
| Site Reliability | reliability | SLOs, observability, incident coordination |
| DBA/Data | data safety | schema/data plans, migration evidence |
| Data Pipeline | data movement | ETL/ELT design, quality and lineage evidence |
| Data Analyst | data interpretation | reproducible analysis and insights |
| Model Evaluator | AI evaluation | metrics, safety and model-evaluation evidence |
| Helpdesk Support | first-line support | diagnosis, user guidance and escalation |
| Knowledge Base | knowledge curation | verified guides, FAQs and content health |
| Reviewer | independent review | findings and review outcome |
| Code Reviewer | code review | code-level findings and review outcome |

The Orchestrator coordinates only. Every specialist reads relevant verified context, works within authority, self-checks, updates approved knowledge, and returns a record matching `schemas/slice-record.schema.json`. The original broad roles remain valid compatibility presets; use a specialised role when the task has a clear ownership boundary.
