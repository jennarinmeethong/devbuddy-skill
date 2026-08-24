# สถาปัตยกรรม DevBuddy แบบ Plugin-first

DevBuddy ติดตั้งผ่าน Plugin/profile ของ host เดียวต่อการติดตั้ง โดย
`devbuddy-core` เป็น dependency ที่ bundle อยู่ภายใน ไม่ใช่ผลิตภัณฑ์ที่ผู้ใช้
ติดตั้งแยกเอง

| Host | Platform ID | คำสั่งใช้งาน |
|---|---|---|
| Codex | `codex` | `$devbuddy <task>` |
| Claude Code | `claude-code` | `/devbuddy-claude-code:devbuddy <task>` |
| OpenCode | `opencode` | adapter entry point ของ OpenCode |

Claude Code namespace skill ของ Plugin จึงไม่สามารถใช้ชื่อ bare
`/devbuddy` สำหรับ Plugin ใหม่ได้. Legacy installer ทั้ง Claude และ Codex
แสดง migration report แบบ read-only ก่อนเสมอ; คำสั่ง `--apply` เดิมยังติดตั้ง
standalone path ได้ในช่วง DevBuddy 1.x (และใช้ `--legacy-install` ได้เช่นกัน). การ rollback คือ
disable/remove Plugin หรือ profile โดยไฟล์ legacy เดิมยังคงอยู่.

ดูรายละเอียด owner, provenance, permission tier, migration schedule และ
เงื่อนไขก่อน removal ได้ที่ `plugin-first-architecture.md`.
