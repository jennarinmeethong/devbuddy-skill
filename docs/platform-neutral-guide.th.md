# คู่มือ DevBuddy แบบไม่ผูกแพลตฟอร์ม

DevBuddy แยกสัญญากลางของงานส่งมอบออกจากกลไกของ host โดย policy, หลักฐานงาน, approval, ownership ของ role และ package/profile เป็นส่วนกลาง ส่วน Codex, Claude Code และ OpenCode มีหน้าที่ map เฉพาะการติดตั้ง การเรียกใช้ และการส่งงานให้ subagent

## ใช้ profile บนทุก host ที่รองรับ

เลือก host adapter ก่อน แล้วจึงเพิ่ม profile แบบ portable ให้ workspace ตัว resolver เป็น read-only โดยปริยาย และแสดง package/role ที่จะเลือกก่อนเขียนไฟล์เสมอ

```text
python3 scripts/profile_resolver.py --list
python3 scripts/profile_resolver.py product-delivery --platform <host>
python3 scripts/profile_resolver.py product-delivery --platform <host> --devbuddy-root <workspace>/.devbuddy --apply
python3 scripts/profile_resolver.py --add-profile data-ai --platform <host> --devbuddy-root <workspace>/.devbuddy --apply
python3 scripts/profile_resolver.py --remove-profile data-ai --platform <host> --devbuddy-root <workspace>/.devbuddy --apply
python3 scripts/profile_resolver.py --status --devbuddy-root <workspace>/.devbuddy
```

`<host>` คือ `codex`, `claude-code` หรือ `opencode` หาก profile หรือ package ไม่รองรับ host ที่เลือก resolver จะหยุดพร้อมข้อผิดพลาด การลบ profile จะคำนวณ dependency ใหม่ จึงเก็บ shared dependency ไว้จนไม่มี profile ใดใช้งานแล้ว

## Preset บทบาท

catalog กลางมีทั้ง role เดิมเพื่อความเข้ากันได้ และ role เฉพาะทาง: Requirements Analyst, Frontend/Backend Engineer, Code Reviewer, DevOps, Cloud Infrastructure, SRE, Data Pipeline, Data Analyst, Model Evaluator, Vulnerability Scanner, Compliance & Policy, Security Incident Response, Helpdesk Support และ Knowledge Base

ใช้ `product-delivery`, `cloud-operations`, `data-ai` หรือ `support-knowledge` เพื่อให้ Orchestrator เลือกชุด role ที่เหมาะสม Profile เป็นเพียง metadata สำหรับเลือกความสามารถ ไม่ได้ให้สิทธิ์ tool, ค่าใช้จ่าย, การเขียน, production, data หรือ external action เพิ่มเอง

สำหรับ OpenCode ให้ materialize preset ที่เลือกไปยัง project หลังติดตั้ง adapter:

```text
python3 <plugin-directory>/scripts/materialize_agents.py --preset data-ai --project-root <project>
python3 <plugin-directory>/scripts/materialize_agents.py --preset data-ai --project-root <project> --apply
```

คำสั่งแรกเป็น dry run และคำสั่งที่สองจะไม่เขียนทับ agent file เดิม

## การ map ตาม host

| เรื่อง | Codex | Claude Code | OpenCode |
|---|---|---|---|
| contract กลาง | `devbuddy-core` | `devbuddy-core` | `devbuddy-core` |
| native adapter | `devbuddy-codex` | `devbuddy-claude-code` | `plugin/devbuddy-core/opencode` |
| เรียกใช้งาน | `$devbuddy <task>` | `/devbuddy-claude-code:devbuddy <task>` | entry point ของ host adapter |
| profile composition | `scripts/profile_resolver.py` | `scripts/profile_resolver.py` | `scripts/profile_resolver.py` |

เก็บคำสั่ง install, update, reload และ discovery ที่เฉพาะ host ไว้ในส่วนติดตั้งของ README อย่าใส่ไวยากรณ์คำสั่งของ host ใด host หนึ่งลงใน portable policy, role, profile, schema หรือหลักฐานงาน
