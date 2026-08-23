# DevBuddy Plugin and Optional Packages Plan

สถานะเอกสาร: Implemented and release-validated (2026-08-23)
ขอบเขต: Codex plugin, OpenCode adapter, portable skills, profile packages และ read-only database tools  
หลักการสำคัญ: additive-only, preserve existing source, explicit approval สำหรับ mutation และ least privilege

## 1. Objective

โครงการนี้มีเป้าหมายเพื่อเพิ่ม DevBuddy ให้เป็น plugin พร้อมชุด optional packages และ skills ที่ติดตั้งแยกได้ โดยแยกความสามารถที่ใช้ร่วมกันได้ออกจาก adapter ของแต่ละ platform อย่างชัดเจน

เป้าหมายหลักมีดังนี้:

- เพิ่ม DevBuddy เป็น plugin และชุด optional packages ที่จัด composition ได้ตาม profile
- แยก portable skills จาก platform adapters เพื่อให้ logic หลักใช้งานซ้ำได้
- รองรับทั้ง Codex และ OpenCode โดยไม่ผูก core เข้ากับ transport หรือชื่อ API ของ platform ใด platform หนึ่ง
- เก็บ source, adapter และเอกสารเดิมไว้ทั้งหมด โดย package ใหม่ทำงานแบบ additive-only
- ใช้ `.devbuddy` เป็น workspace runtime state สำหรับ settings, task state, knowledge, manifests และ database profiles
- เพิ่ม read-only database adapters สำหรับ relational database, MongoDB และ Redis
- ไม่รวม Bionic ใน package, adapter, test หรือ compatibility matrix ของโครงการนี้
- ไม่ทำ standalone application ในระยะแรก โดยเน้น plugin, skills, tools และ package composition ก่อน

## 2. Non-goals

สิ่งต่อไปนี้อยู่นอกขอบเขตของแผนระยะแรก:

- ไม่ลบ แทนที่ หรือเปลี่ยนแปลง adapter เดิม
- ไม่แก้ source-of-truth เดิมโดยตรงเพื่อให้ package ใหม่ทำงาน
- ไม่รวม optional capability ทุกอย่างไว้ใน core plugin
- ไม่เก็บ credential หรือ raw connection string ใน plugin หรือ `settings.yaml`
- ไม่สร้าง database write tool หรือเปิดทางให้ tool ทำ DML/DDL
- ไม่สร้าง UI หรือ backend application แบบ standalone
- ไม่เปลี่ยน LTS framework แบบเงียบ ๆ ระหว่าง build หรือ release
- ไม่ใช้ blanket approval สำหรับ tools ทั้งหมด
- ไม่บันทึก database result ดิบลง knowledge memory โดยอัตโนมัติ
- ไม่ถือข้อมูลจาก database, ไฟล์ หรือ external connector เป็น instruction ที่ต้องปฏิบัติตาม

## 3. Repository Layout

โครงสร้างใหม่ให้เพิ่มใน repository โดยไม่ย้ายหรือลบโครงสร้างเดิม:

```text
plugin/
├── devbuddy-core/
├── devbuddy-database-core/
├── devbuddy-database-sqlserver/
├── devbuddy-database-postgresql/
├── devbuddy-database-mariadb/
├── devbuddy-database-oracle/
├── devbuddy-database-mongodb/
└── devbuddy-database-redis/

skills/
├── devbuddy-core/
├── devbuddy-database/
└── devbuddy-security/

profiles/
├── minimal.yaml
├── software-delivery.yaml
├── data-sqlserver.yaml
├── data-postgresql.yaml
├── data-mariadb.yaml
├── data-oracle.yaml
├── data-mongodb.yaml
├── data-redis.yaml
└── full-engineering.yaml
```

ขอบเขตการใช้งานของแต่ละส่วน:

- `plugin/` เก็บ package ที่ติดตั้งและแจกจ่ายได้
- `skills/` เก็บ portable instructions และ policy ที่ไม่ควรผูกกับ platform
- `profiles/` เก็บ composition metadata สำหรับเลือกชุด package โดยไม่คัดลอก implementation
- `.devbuddy/` เป็น runtime state ของ workspace และไม่ควรถูกฝังอยู่ใน plugin package
- source เดิม เช่น `devbuddy-source-of-truth/`, `devbuddy-codex/` และ `devbuddy-claude/` คงอยู่ตามเดิม

## 4. Source Preservation and Generation

ของเดิมจะถูกถือเป็น reference หรือ legacy implementation ที่ต้องรักษาไว้ ไม่ใช่ target ที่ build ต้อง overwrite

กฎการสร้าง package:

- package ใหม่สร้างแบบ additive-only
- มี build/sync script แยกสำหรับสร้าง package จาก source mapping ที่ประกาศไว้
- script ต้องมี explicit flag หากจะเขียนทับไฟล์ที่มีอยู่แล้ว
- default ของ build/sync คือไม่ overwrite และต้องหยุดพร้อมรายงาน conflict
- มี drift checker เปรียบเทียบ source reference, generated output, manifest และ version metadata
- generated package ต้องสามารถสร้างซ้ำได้จาก input เดิมอย่าง deterministic เท่าที่ทำได้
- build package ต้องไม่แก้ source เดิมโดยอัตโนมัติ
- generated files ต้องระบุ provenance, source revision และ generation timestamp ใน metadata ที่ไม่ปนกับ runtime secret
- การลบหรือย้าย source เดิมไม่ใช่ส่วนหนึ่งของ generation workflow

ผลลัพธ์ขั้นต่ำของ generation workflow:

1. ตรวจ source mapping และ package manifest
2. ตรวจว่า target path อยู่ในพื้นที่ package ใหม่
3. ตรวจ drift และ dependency conflict
4. สร้าง package ใน staging output
5. รัน manifest, skill และ compatibility validation
6. เขียนลง target เฉพาะเมื่อ target ไม่มีอยู่ หรือมี explicit overwrite flag
7. สร้าง generation report และสรุปไฟล์ที่เปลี่ยน

## 5. Core Plugin

`devbuddy-core` เป็นส่วนที่ต้องทำงานได้โดยไม่มี optional package ใด ๆ และเป็น portability boundary ของระบบ

ความรับผิดชอบของ core:

- portable `SKILL.md` และ instruction contract
- policy และ approval workflow
- risk classification ของงานและ operation
- task ledger และ lifecycle state
- knowledge impact assessment
- scope validation
- evidence และ closure criteria
- Thai user-facing status และ progress message
- English internal artefacts เช่น manifest, schema, audit metadata และ machine-readable report

core ต้องกำหนด contract ที่ platform adapter นำไป map ได้ เช่น:

- task identity และ task state
- requested operation, risk และ approval state
- allowed workspace scope
- required evidence
- tool permission tier
- completion, blocked และ waiting states

ต้องตัด platform-specific behavior ออกจาก core ได้แก่:

- `$devbuddy`
- Codex Agent tool
- Claude agent naming
- Codex `model`/`reasoning_effort` transport
- provider-specific request envelope
- lifecycle hook ที่มีเฉพาะ platform ใด platform หนึ่ง

core ไม่ควรเรียก database adapter โดยตรง หากไม่มี database package และ profile ที่เปิดใช้งานอย่างชัดเจน

## 6. Platform Adapters

### 6.1 Codex

Codex adapter ต้อง:

- สร้าง OpenAI plugin manifest ที่ถูกต้องตาม plugin contract
- bundle หรือ reference `devbuddy-core` skill
- expose optional companion packages ผ่าน manifest และ profile metadata
- map core task lifecycle ไปยัง Codex task/session lifecycle
- ประกาศ tools, permissions และ runtime dependencies อย่างตรวจสอบได้
- แยก development-time skill dependency ออกจาก runtime dependency
- ไม่แก้ไข `devbuddy-codex/`

Codex adapter ห้าม hard-code model หรือ reasoning transport ลงใน portable core โดย transport mapping ต้องอยู่ใน adapter layer เท่านั้น

### 6.2 OpenCode

OpenCode adapter ต้องเพิ่มองค์ประกอบต่อไปนี้:

- OpenCode skill ที่ map core behavior ไปยัง OpenCode context
- agents/subagents สำหรับ role ที่จำเป็น
- custom tools ที่ห่อ core tool contract
- plugin hooks สำหรับ initialization, task lifecycle, approval และ closure
- mapping ของ permissions, model/provider และ task lifecycle
- รองรับทั้ง local plugin และ npm package distribution
- แยก compatibility test สำหรับ OpenCode plugin API โดยเฉพาะ

OpenCode adapter ต้องไม่คัดลอก business logic ของ core มาไว้ใน agent หลายตัว หากเป็น logic เดียวกันให้เรียก portable skill หรือ shared package

Compatibility test ต้องครอบคลุมอย่างน้อย:

- plugin discovery และ manifest loading
- skill loading
- tool registration และ permission mapping
- agent/subagent invocation
- hook order และ error propagation
- local package installation
- npm package installation metadata
- version mismatch และ unsupported API behavior

## 7. Optional Packages

ความสามารถที่ไม่จำเป็นต่อ core ต้องแยกเป็น package หรือ skill เพื่อให้ผู้ใช้เลือกติดตั้งแบบ optional ได้:

```text
devbuddy-core
devbuddy-database-*
devbuddy-security
devbuddy-documents
devbuddy-browser
devbuddy-deployment
devbuddy-project-management
```

รายการ package ที่วางแผนไว้:

- `devbuddy-core`: workflow, policy, task และ evidence baseline
- `devbuddy-database-core`: common database contract, limits, redaction และ manifest schema
- `devbuddy-database-*`: adapter ของแต่ละ engine
- `devbuddy-security`: security review, secret boundary และ risk checks
- `devbuddy-documents`: document-oriented workflows และ connector integration points
- `devbuddy-browser`: browser research/inspection workflow โดยต้องมี permission boundary
- `devbuddy-deployment`: deployment planning และ environment checks
- `devbuddy-project-management`: mapping ไปยัง project-management connector ที่ผู้ใช้เลือก

กฎของ optional package:

- core ต้องทำงานได้แม้ไม่มี optional package
- การติดตั้งต้องเลือกได้ราย package หรือผ่าน profile
- package ต้องประกาศ dependencies, permissions, runtime และ compatibility version
- package ที่ไม่ติดตั้งต้องไม่ทำให้ core discovery หรือ core validation ล้มเหลว
- profile เป็น composition metadata ไม่ใช่ codebase ที่คัดลอก logic ซ้ำ
- optional package ต้องไม่เพิ่ม approval ให้ tool โดยอัตโนมัติ

## 8. `.devbuddy` Workspace Runtime

`.devbuddy` ยังจำเป็นและเป็น runtime state ของ workspace ไม่ใช่ส่วนหนึ่งของ plugin package:

```text
.devbuddy/
├── settings.yaml
├── knowledge-base/
├── tasks/
└── tools/
    ├── manifest.json
    └── databases/
```

`.devbuddy` ใช้เก็บ:

- project registry
- workspace settings
- task state และ task ledger
- canonical knowledge
- runtime tools
- tool manifests
- database profiles
- approval state และ version state

plugin package ห้ามเก็บสิ่งต่อไปนี้:

- task ledger ของผู้ใช้
- knowledge ของ workspace
- secret หรือ credential
- user-specific settings
- database credential หรือ raw connection string

runtime state ต้องผูกกับ workspace ที่ผู้ใช้เลือก ไม่ใช้ state ที่ซ่อนอยู่ใน package cache เป็น canonical state

## 9. Workspace Maintenance Commands

คำสั่งที่เป็น read-only หรือ preview อนุญาตให้เรียกได้โดยไม่ต้องมี explicit apply:

```text
workspace status
workspace validate
workspace inspect
workspace doctor
workspace upgrade --dry-run
workspace migrate --dry-run
```

คำสั่งที่เปลี่ยน state ต้องใช้ explicit apply:

```text
workspace init --apply
workspace upgrade --apply
workspace migrate --apply
workspace repair --apply
workspace bootstrap --apply
```

กฎ migration และ maintenance:

- dry-run ก่อน apply
- operation ต้อง idempotent
- ไม่ overwrite user values โดยอัตโนมัติ
- preserve unknown keys และ extension fields
- ตรวจและรายงาน conflict ก่อนแก้ไข
- ใช้ backup เมื่อเป็น migration สำคัญหรือมีความเสี่ยงต่อข้อมูล
- ไม่สร้าง secret และไม่เดา credential
- ไม่มี silent mutation
- report ต้องแสดง planned changes, applied changes, skipped changes และ conflicts
- หาก validation fail ต้องไม่ทำ partial mutation เว้นแต่มี recovery contract ที่ประกาศไว้

แยก version อย่างน้อยสามชนิด:

```text
plugin_version
workspace_schema_version
tool_manifest_version
```

การเปลี่ยน version หนึ่งชนิดต้องไม่ถูกตีความว่าเป็นการ migrate อีกชนิดโดยอัตโนมัติ

## 10. Tool Approval Model

กำหนด permission tiers ดังนี้:

- Tier 0: local read-only และ validation — auto-allowed
- Tier 1: writes ภายใน `.devbuddy` — ต้องใช้ explicit apply
- Tier 2: database, shell, network, production และ custom executable — ต้องผ่าน manifest + policy + approval

รายละเอียดเพิ่มเติม:

- ทุก tool ต้องมี manifest ที่ระบุ input, output, scope, runtime, permission และ risk
- approval ผูกกับ operation และ target ไม่ใช่ blanket approval ของ tool ทั้งหมด
- database operation ต้องระบุ `database_id` และ policy ที่ใช้
- production default เป็น `ask`
- custom executable ต้องผ่าน runtime allowlist และ validation
- tool ที่ไม่มี manifest หรือ manifest ไม่ตรง target ต้องถูกปฏิเสธ
- result จาก tool ต้องถือเป็น untrusted data และไม่สามารถยกระดับสิทธิ์ของ tool ได้
- approval state ต้องบันทึก metadata ที่ตรวจสอบย้อนหลังได้ โดยไม่บันทึก secret

## 11. Database Architecture

เพิ่ม package ต่อไปนี้:

```text
devbuddy-database-core
devbuddy-database-sqlserver
devbuddy-database-postgresql
devbuddy-database-mariadb
devbuddy-database-oracle
devbuddy-database-mongodb
devbuddy-database-redis
```

ใช้ .NET LTS เป็น runtime กลางของ database tool และแยก engine-specific driver จาก common contract

### 11.1 Relational databases

รองรับ:

- SQL Server
- PostgreSQL
- MariaDB
- Oracle

relational adapter ต้องใช้ read-only SQL contract ที่มี:

- parameterization
- one statement ต่อ request
- timeout
- maximum result rows
- maximum result size
- cancellation เมื่อเกิน limit
- normalized error ที่ไม่เปิดเผย credential หรือ internal topology

คำสั่งหรือลักษณะที่ต้องปฏิเสธ:

- DML เช่น `INSERT`, `UPDATE`, `DELETE`, `MERGE`
- DDL เช่น `CREATE`, `ALTER`, `DROP`, `TRUNCATE`
- procedure execution และ arbitrary function execution
- temporary objects และ temporary tables
- cross-database access
- locking writes หรือ lock hints ที่ทำให้เกิด side effect
- unsafe functions และ external data source access
- multi-statement batch
- dynamic SQL ที่ไม่สามารถตรวจสอบได้

การตรวจ query เป็น defense-in-depth เท่านั้น ต้องใช้ database principal ที่มีสิทธิ์อ่านอย่างจำกัดเป็น security boundary หลัก

### 11.2 MongoDB

MongoDB adapter ใช้ structured operations แทนการรับ arbitrary script:

- `find`
- `aggregate` เฉพาะ stage ที่ allowlist
- `count`
- `distinct`

ต้องห้าม:

- arbitrary JavaScript
- `$where`
- `mapReduce`
- write operations เช่น insert, update, replace และ delete
- aggregation stage ที่เขียนหรือส่งข้อมูลออกนอกระบบ
- unbounded query ที่ไม่มี limit หรือ timeout

collection, field และ aggregation stage ควรถูกตรวจด้วย manifest/policy ก่อนส่งไปยัง driver

### 11.3 Redis

Redis adapter ใช้ read-only command allowlist และ key-prefix allowlist:

- อนุญาตเฉพาะคำสั่งอ่านที่ประกาศไว้ใน adapter manifest
- บังคับ key prefix เพื่อจำกัด namespace
- จำกัดจำนวน key, response size และ timeout
- รองรับการตรวจ command argument ก่อนส่งไปยัง server

ต้องห้าม:

- write commands
- `FLUSHDB` และ `FLUSHALL`
- `CONFIG`
- `EVAL` และ script execution
- module/admin commands
- replication, persistence หรือ server reconfiguration commands
- command ที่ใช้สำรวจหรือข้าม boundary ของ production namespace

## 12. Multi-database Settings

เพิ่ม field `databases` แบบ backward-compatible โดย metadata ใน `settings.yaml` ต้องอ้างอิง secret file เท่านั้น:

```yaml
databases:
  - id: billing-prod
    engine: postgresql
    environment: production
    adapter_package: devbuddy-database-postgresql
    manifest: tools/databases/billing-prod/tool.json
    secret_file: tools/databases/billing-prod/appsettings.json
    approval: ask
    allowed_schemas: [reporting]
    max_rows: 500
    timeout_seconds: 30
```

กฎของ database registry:

- ทุก database ต้องมี unique ID ภายใน workspace
- การเรียกใช้ต้องระบุ `database_id` ทุกครั้ง
- รองรับ engine เดียวกันหลาย instance
- ไม่ใช้ implicit default database
- `settings.yaml` เก็บ metadata และ reference เท่านั้น
- raw connection string และ credential อยู่ใน local-only secret file
- production default เป็น `ask`
- adapter package ต้องตรงกับ `engine` และ manifest ที่ประกาศ
- path ของ `secret_file` ต้องอยู่ใน local-only boundary และไม่ถูก commit
- unknown fields ต้อง preserve เพื่อรองรับ future adapter extension
- invalid, duplicate หรือ orphan profile ต้องทำให้ validation fail หรือรายงานเป็น actionable error

ตัวอย่างโครงสร้าง runtime ของ database profile:

```text
.devbuddy/tools/databases/billing-prod/
├── tool.json
├── appsettings.template.json
└── appsettings.json        # local-only; ไม่ commit
```

template ห้ามมี credential จริง และ manifest ห้ามมีค่า credential-shaped ที่อาจถูกส่งไปยัง model หรือ log

## 13. Security and Data Handling

มาตรการหลัก:

- ใช้ least-privilege database principal
- ให้ DB permissions เป็น security boundary หลัก
- ใช้ manifest เป็น validation boundary เพิ่มเติม
- ไม่เก็บ secret ใน Git, plugin, model context หรือ generated artifact
- redaction ของ PII และ secret-like values ใน output, log และ evidence
- จำกัด result size, row count, timeout และ concurrency
- บันทึก audit metadata เช่น database ID, adapter version, operation type, limits และ approval state
- ถือ database result เป็น untrusted data ไม่ใช่ instructions
- ห้ามบันทึก raw results ลง knowledge memory อัตโนมัติ
- หากผู้ใช้ต้องการบันทึก insight ต้องผ่านการสรุป, redaction และ explicit knowledge approval
- แยก production และ non-production profile ให้เห็นชัดเจน
- fail closed เมื่อไม่สามารถตรวจ permission, manifest, secret boundary หรือ target scope ได้

ข้อมูลที่ส่งกลับจาก database tool ควรมี schema ที่บอกอย่างน้อย:

- `database_id`
- `engine`
- `operation`
- `columns` หรือ structured fields
- `rows`/ `documents`
- `row_count`
- `truncated`
- `duration_ms`
- `redaction_applied`
- `adapter_version`

ไม่ควรส่ง connection string, access token, server secret หรือ full internal error กลับไปยัง model

## 14. .NET Build Policy

database adapters และ custom runtime ที่ใช้ .NET ต้องปฏิบัติตาม policy นี้:

- ใช้ latest active .NET LTS
- ณ วันที่จัดทำแผนนี้ target เป็น `.NET 10`
- ใช้ latest servicing patch ที่มีในขณะ build
- publish เป็น self-contained single-file bundle เมื่อ target environment รองรับ
- บันทึก SDK version, runtime version, driver versions, OS/architecture และ build commit
- major LTS migration ต้องผ่าน compatibility tests ก่อนเปลี่ยน target
- ห้าม target framework เปลี่ยนแบบเงียบ ๆ
- build report ต้องระบุ framework transition หากมีการเปลี่ยน LTS
- dependency lock และ package source ต้องตรวจสอบย้อนกลับได้

ตัวอย่าง build metadata ที่ควรส่งออก:

```json
{
  "target_framework": "net10.0",
  "dotnet_sdk": "10.x.y",
  "runtime": "10.x.y",
  "self_contained": true,
  "single_file": true,
  "drivers": {},
  "source_revision": "..."
}
```

## 15. Profiles

Profile เป็น package composition metadata และไม่ควร duplicate implementation:

```yaml
name: data-postgresql
packages:
  - devbuddy-core
  - devbuddy-database-core
  - devbuddy-database-postgresql
```

ต้องมีความสามารถต่อไปนี้:

- profile schema
- dependency resolver
- dry-run installer
- version compatibility check
- conflict detection
- permission summary ก่อนติดตั้ง
- install, uninstall และ upgrade behavior ที่ชัดเจน
- profile test matrix
- report รายการ package ที่เพิ่ม, คงอยู่, ถูกถอด หรือรอ approval

resolver ต้องตรวจ:

- package name และ version ที่มีอยู่จริง
- dependency graph และ cyclic dependency
- platform compatibility
- runtime compatibility
- permission escalation
- conflict ระหว่าง tool ID, skill ID, manifest schema และ hook
- optional dependency ที่หายไปโดยไม่ทำให้ core พัง

installer ต้องรองรับ dry-run และต้องไม่แก้ workspace หรือ package cache จนกว่าจะมี explicit apply/approval

## 16. External Companion Plugins/Skills

external plugin/skill ไม่บังคับใน core และควรติดตั้งตาม profile หรือความต้องการของผู้ใช้เท่านั้น

คำแนะนำตาม profile:

- Software delivery: GitHub และ Codex Security
- Project management: เลือกหนึ่งจาก Atlassian Rovo, Asana, ClickUp หรือ Trello
- Documents: Google Drive, Dropbox หรือ Box
- Deployment: Cloudflare, Vercel หรือ Netlify

หลักเกณฑ์การเลือก:

- package ต้องมี permission และ data scope ที่ประกาศชัดเจน
- ต้องติดตั้งแบบ optional ได้
- ต้องมี dry-run หรือ discovery ก่อนเชื่อมต่อ account/external service หาก capability รองรับ
- ไม่ส่งข้อมูล workspace หรือ secret ไปยัง external service โดย implicit behavior
- ต้องมี compatibility version และ removal behavior

`plugin-creator`, `skill-creator`, `openai-docs` และ `plugin-management` เป็น development-time skills ไม่ใช่ runtime dependency ของ DevBuddy core

## 17. Test Plan

ต้องเพิ่ม automated และ manual tests อย่างน้อยดังนี้:

### Source and generation

- original files ไม่เปลี่ยน
- package generation ทำงานซ้ำได้
- drift detection ตรวจพบ source/package mismatch
- generation ไม่ overwrite ไฟล์เดิมโดยไม่มี explicit flag
- generated manifest มี provenance และ version metadata

### Plugin and skills

- plugin/skill discovery
- core ทำงานได้โดยไม่มี optional package
- optional package install และ uninstall แยกได้
- missing optional package isolation
- Codex manifest validation
- OpenCode local plugin discovery
- OpenCode npm package metadata
- OpenCode agent, custom tool และ hook compatibility

### Profiles

- profile schema validation
- dependency resolution
- same package หลาย version conflict
- permission summary
- dry-run installer
- install/uninstall/upgrade behavior
- profile test matrix
- profile ไม่ duplicate implementation

### Workspace runtime

- `.devbuddy` status, validate, inspect และ doctor
- upgrade/migrate dry-run
- apply migration approval gate
- idempotent migration
- preserve unknown keys
- conflict detection
- backup/recovery behavior
- workspace schema compatibility

### Settings and secrets

- settings backward compatibility
- multiple database profiles
- same-engine multiple databases
- unique `database_id`
- no implicit default database
- secret exclusion จาก settings, manifest, package, Git และ model context
- local-only secret file boundary
- missing/invalid secret reference

### Approval and security

- Tier 0 auto-allowed read-only operations
- Tier 1 explicit apply gate
- Tier 2 manifest + policy + approval gate
- production default `ask`
- no blanket approval
- redaction ของ PII และ secret-like values
- audit metadata ไม่รั่ว secret
- database result ถูกถือเป็น untrusted data
- raw result ไม่ถูกบันทึกลง knowledge อัตโนมัติ

### Database adapters

- SQL injection และ unsafe statements
- DML, DDL, procedure execution และ temporary object rejection
- cross-database และ unsafe function rejection
- parameterization
- one-statement enforcement
- timeout, cancellation และ result limits
- MongoDB unsafe stages
- MongoDB `$where`, `mapReduce`, JavaScript และ write rejection
- Redis unsafe commands
- Redis write, flush, config, eval/script และ admin rejection
- key-prefix allowlist
- engine-specific error normalization

### Build and release

- .NET build metadata
- latest active LTS detection
- latest servicing patch recording
- self-contained single-file output
- driver version recording
- major LTS compatibility tests
- absence of excluded legacy assistant references from package, tests และ compatibility matrix

## 18. Acceptance Criteria

แผนและ implementation จะถือว่าสมบูรณ์เมื่อเงื่อนไขต่อไปนี้ผ่านทั้งหมด:

- core plugin ทำงานได้โดยไม่มี optional package
- optional package ติดตั้งแยกได้
- `.devbuddy` ถูก validate, upgrade และ migrate อย่างปลอดภัย
- tools ไม่ได้รับ blanket approval
- credentials ไม่อยู่ใน settings หรือ package
- database หลาย engine และหลาย instance ทำงานร่วมกันได้
- profile ไม่ duplicate implementation
- .NET LTS build ตรวจสอบย้อนกลับได้
- ของเดิมไม่มีการแก้ไข ลบ หรือแทนที่
- Bionic ไม่มีอยู่ใน package, docs, tests หรือ compatibility matrix ของ implementation ที่ส่งมอบ
- Codex และ OpenCode adapter แยกจาก portable core อย่างชัดเจน
- source generation ตรวจ drift และไม่ overwrite โดยไม่มี explicit flag
- database tool ทุกตัวเป็น read-only และ fail closed เมื่อ policy ไม่ชัดเจน
- production database profile ใช้ approval default เป็น `ask`
- task, knowledge และ user-specific runtime state ไม่ถูกฝังใน plugin package

## 19. Implementation Sequence

ลำดับการทำงานที่แนะนำ:

1. กำหนด package, skill, profile และ manifest schemas
2. สร้าง source mapping, additive generation workflow และ drift checker
3. แยก portable `devbuddy-core` และ approval contract
4. สร้าง Codex manifest/adapter โดยไม่แตะ adapter เดิม
5. สร้าง OpenCode skill, agents, tools และ hooks พร้อม compatibility tests
6. สร้าง `devbuddy-database-core` และ common result/limit/redaction contract
7. ย้ายแนวคิด read-only SQL contract ไปยัง SQL Server, PostgreSQL, MariaDB และ Oracle adapters
8. เพิ่ม structured MongoDB adapter
9. เพิ่ม Redis read-only command adapter และ key-prefix enforcement
10. เพิ่ม `.devbuddy` database registry, secret references และ workspace maintenance operations
11. เพิ่ม profile resolver, installer dry-run และ permission summary
12. เพิ่ม optional companion package metadata
13. รัน test matrix, source preservation check และ release validation
14. สร้าง package artifacts และ documentation ที่ trace ได้ถึง source revision

แต่ละช่วงต้องรักษา additive-only rule และหยุดเมื่อพบ conflict ที่อาจทำให้ source เดิมถูก overwrite

## 20. Definition of Done

ก่อน release ต้องมีหลักฐานอย่างน้อย:

- manifest validation report
- source preservation/diff report
- drift checker report
- plugin discovery report ของ Codex และ OpenCode
- profile dependency and permission report
- workspace migration dry-run report
- database adapter safety test report
- secret exclusion scan report
- .NET build metadata และ reproducibility information
- compatibility test report
- รายการ known limitations และ required user approvals

การ release จะทำได้เมื่อ evidence ทั้งหมดผ่านและไม่มี unresolved critical security, data-loss หรือ source-preservation issue

## 21. Implementation Status

สถานะ: Completed

หลักฐานการตรวจ release ล่าสุดอยู่ที่ `reports/release-validation.json` และครอบคลุม package validation, secret exclusion, source preservation, drift detection, architecture tests, OpenCode compatibility และ .NET database build

ข้อกำหนดก่อนใช้งาน database กับระบบจริง: ผู้ใช้ต้องสร้าง local-only `appsettings.json`, ใช้ database principal แบบ read-only และให้ approval แบบผูกกับ target สำหรับ Tier 2 ทุกครั้ง
