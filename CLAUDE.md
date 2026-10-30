# TUH Chatbot AI — Project Instructions

แชทบอทของงานสารสนเทศ โรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ ประกอบด้วย 3 ส่วน:
- **Backend** (`services/api/`) — FastAPI + TiDB Cloud (MySQL) ผ่าน SQLAlchemy async + JWT Auth, RAG อยู่ใน `services/api/app/rag/`
- **UserWeb** (`apps/chat-web/`) — React + Vite แชทบอทที่ผู้ใช้ทั่วไป/บุคลากรเห็น
- **AdminWeb** (`apps/admin-web/`) — React + Vite ระบบหลังบ้านสำหรับแอดมิน

โครงสร้างนี้เป็นผลจากการจัดระเบียบ 2026-10-30 (branch `refactor/clean-structure`) — **ถ้าเจอเอกสารที่อ้างถึง `Backend/`, `UserWeb/`, `AdminWeb/`, `Admin/emb.py`, `run_backend.py`, `deploy_xampp.py`, `web_testing/` ถือว่าล้าสมัย** ให้ใช้ path/คำสั่งด้านล่างแทน (โครงสร้างเต็มใน [README.md](README.md))

## รันระบบ (production = Docker ตั้งแต่ 2026-10-29)
```bash
docker compose up -d --build     # https://<host>/ (chat-web), /admin/ (admin-web), /api/ (services/api) ผ่าน Caddy
```
port 5173/5174/8080 บนเครื่องเป็นตัว redirect ไป HTTPS; backend เปิดเฉพาะ `127.0.0.1:8000` (รายละเอียด TLS/CA ใน docs/DOCKER.md)
ข้อมูล (ChromaDB, bm25.pkl, sample_chunks.json, uploads, โมเดล) อยู่ใน Docker volume `tuh-chatbot_*` ไม่ใช่โฟลเดอร์ `uploads/`/`index_db/` บนไดรฟ์ Z: — รายละเอียดใน [docs/DOCKER.md](docs/DOCKER.md)
XAMPP เลิกใช้แล้ว (Apache ต้องปิดไว้ เพราะ port 8080 เป็นของ redirect)

## รันระบบ (dev — ปิด Docker ก่อน เพราะใช้ port เดียวกัน)
```bash
python infra/scripts/dev.py api      # Backend API → http://localhost:8000
python infra/scripts/dev.py chat     # chat-web    → http://localhost:5173
python infra/scripts/dev.py admin    # admin-web   → http://localhost:5174
```
เว็บต้องรันผ่านสคริปต์นี้ (Vite รันจากไดรฟ์ Z: ไม่ได้ — สคริปต์คัดลอกไปรันที่ C: ให้) — ดูรายละเอียดใน [README.md](README.md)

Backend ต้องมี `services/api/.env` ก่อน start (คัดลอกจาก `.env.example`) ไม่มีค่า default ของ secret ใดๆ ในโค้ด

## กฎที่ต้องยึดถือเสมอ
1. **Database**: TiDB Cloud (MySQL) ผ่าน async SQLAlchemy เท่านั้น (`services/api/app/core/database.py`) — ห้ามใช้ SQLite/PostgreSQL (SQL Server เตรียมไว้แล้วแต่ยังไม่ใช้ ดู docs/SQLSERVER_MIGRATION.md) เปลี่ยน schema ต้องผ่าน Alembic migration เสมอ (`alembic revision --autogenerate` → ตรวจไฟล์ → `alembic upgrade head`) ห้ามแก้ schema ตรงๆ
2. **RAG Pipeline**: รักษา HybridRetriever เดิมไว้ทุกกรณี (ChromaDB เก็บ dense vector, embed ด้วย `BAAI/bge-m3` + BM25 (lexical) + Weighted RRF, โค้ดอยู่ที่ `services/api/app/rag/` — `retriever.py` (ค้นหา), `indexer.py` (สร้างดัชนี), `answer.py` (ตอบ), `ocr.py`; FAISS ถูกเอาออกแล้ว) ห้ามแก้ pipeline นี้โดยไม่จำเป็นและไม่ได้รับอนุญาต
3. **UI/UX**: ห้ามเปลี่ยนหน้าตา/พฤติกรรมของ UserWeb (แชทบอท, http://localhost:5173) โดยไม่ได้รับอนุญาตจากผู้ใช้งานอย่างชัดเจน — AdminWeb แก้ได้อิสระกว่าตาม scope ที่ได้รับ
4. **Security**: JWT access token อายุ 15 นาที — ห้ามลดค่า (ไม่มี refresh token: AdminWeb ล็อกอินที่ `/api/admin/login` ซึ่งออกแค่ access token มาตั้งแต่ต้น ส่วน `/api/auth/login`+`/refresh` ที่ไม่มีใครเรียกถูกลบไปตอนจัดระเบียบ); secret (`DB_PASSWORD`, `JWT_SECRET_KEY` ฯลฯ) ต้องมาจาก `.env`/env var เท่านั้น ห้าม hardcode ค่าจริงลงไฟล์ที่ track ใน git (เคยมี production password หลุดมาจากจุดนี้มาก่อน); input ที่ render เป็น HTML ต้องผ่าน `services/api/app/utils/sanitize.py`
5. **Port**: chat-web = 5173, admin-web = 5174, Backend API = 8000
6. **Branch**: อย่า push ตรงไปยัง `main` โดยไม่ได้รับอนุญาตจากผู้ใช้งาน — สร้าง branch แยกก่อนเสมอ
7. **Commit**: message ภาษาอังกฤษ, comment ในโค้ดได้ทั้งไทย/อังกฤษ

## ทีมงาน Sub-Agent (9 บทบาท + 1)
โปรเจกต์นี้มี subagent เฉพาะทางใน `.claude/agents/` — เรียกใช้ผ่าน Agent tool เมื่อประเภทงานตรงกับบทบาท แทนที่จะทำเองทั้งหมดในบทบาททั่วไป:

| Subagent | เมื่อไหร่ควรเรียก |
|---|---|
| `project-manager` | วางแผน sprint/backlog, เขียน User Story + Acceptance Criteria ก่อน feature ใหม่ |
| `system-analyst` | ออกแบบ architecture/data flow/API contract ก่อน implement |
| `business-analyst` | เก็บ requirement, ตรวจว่า feature ตอบโจทย์ธุรกิจโรงพยาบาลฯ |
| `hr-team-standards` | ปรับมาตรฐาน workflow/documentation ของโปรเจกต์ |
| `frontend-dev` | งาน React/Vite ใน UserWeb หรือ AdminWeb ที่มี scope ชัดเจนแล้ว |
| `backend-dev` | งาน FastAPI/API endpoint/TiDB schema ที่มี scope ชัดเจนแล้ว |
| `tech-lead` | รีวิวโค้ด/สถาปัตยกรรมก่อน merge breaking change, ตัดสินใจ technical direction |
| `senior-dev` | งาน full-stack ข้ามชั้น (frontend+backend พร้อมกัน), performance, test coverage |
| `security-engineer` | ตรวจ/แพตช์ security ของ API (auth, rate limit, input validation, CORS) |
| `code-cleanup-uxui` | คลีนโค้ด/รีแฟกเตอร์/ปรับ UX-UI ตาม brief ที่ชัดเจนแล้วเท่านั้น |

รายละเอียดเต็มของแต่ละบทบาท (ประสบการณ์, กฎเฉพาะ, วิธีทำงาน) อยู่ในไฟล์ `.claude/agents/<name>.md` แต่ละไฟล์ — เอกสารต้นฉบับที่ไม่ได้โหลดอัตโนมัติ (`.agents/rules/team.md`) ยังเก็บไว้เป็น reference แต่เนื้อหาที่เป็นมาตรฐานจริงให้ยึดตามไฟล์นี้และ `.claude/agents/*.md` เป็นหลัก
