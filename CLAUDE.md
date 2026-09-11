# TUH Chatbot AI — Project Instructions

แชทบอทของงานสารสนเทศ โรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ ประกอบด้วย 3 ส่วน:
- **Backend** (`Backend/`) — FastAPI + TiDB Cloud (MySQL) ผ่าน SQLAlchemy async + JWT Auth
- **UserWeb** (`UserWeb/`) — React + Vite แชทบอทที่ผู้ใช้ทั่วไป/บุคลากรเห็น
- **AdminWeb** (`AdminWeb/`) — React + Vite ระบบหลังบ้านสำหรับแอดมิน

โครงสร้างนี้เป็นผลจาก reorganize ล่าสุด (commit `f4b9f05`) — **ถ้าเจอเอกสารหรือโค้ดที่อ้างถึง `v2/frontend`, `v2/admin`, `run_v2_frontend.py`, `run_admin_server.py` ถือว่าล้าสมัย** ให้ใช้ path/คำสั่งจริงด้านล่างแทน

## รันระบบ (dev)
```bash
python run_backend.py      # Backend API   → http://localhost:8000
python run_user_web.py     # UserWeb       → http://localhost:5173
python run_admin_web.py    # AdminWeb      → http://localhost:5174
```
หรือรันตรงในแต่ละโฟลเดอร์ด้วย `npm run dev -- --port <5173|5174>` (frontend) / `uvicorn app.main:app --reload --port 8000` (backend) — ดูรายละเอียดเต็มใน [README.md](README.md)

Backend ต้องมี `Backend/.env` ก่อน start (คัดลอกจาก `.env.example`) ไม่มีค่า default ของ secret ใดๆ ในโค้ด

## กฎที่ต้องยึดถือเสมอ
1. **Database**: TiDB Cloud (MySQL) ผ่าน async SQLAlchemy เท่านั้น (`Backend/app/core/database.py`) — ห้ามใช้ SQLite/PostgreSQL ใน production path (SQLite ใช้ได้เฉพาะ `Backend/tests/conftest.py` สำหรับ pytest) เปลี่ยน schema ต้องผ่าน Alembic migration เสมอ (`alembic revision --autogenerate` → ตรวจไฟล์ → `alembic upgrade head`) ห้ามแก้ schema ตรงๆ
2. **RAG Pipeline**: รักษา HybridRetriever เดิมไว้ทุกกรณี (ChromaDB เก็บ dense vector, embed ด้วย `BAAI/bge-m3` + BM25 (lexical) + Weighted RRF, `Admin/emb.py` ซึ่งเป็น legacy toolset ที่ backend ยังเรียกใช้จริงผ่าน `Backend/app/services/rag_service.py` — ไม่ใช่ของที่ต้องลบทิ้ง — FAISS ถูกเอาออกจากโค้ดแล้ว (2026-09-11) ไม่มีเป็นทางเลือกสำรองอีกต่อไป) ห้ามแก้ pipeline นี้โดยไม่จำเป็นและไม่ได้รับอนุญาต
3. **UI/UX**: ห้ามเปลี่ยนหน้าตา/พฤติกรรมของ UserWeb (แชทบอท, http://localhost:5173) โดยไม่ได้รับอนุญาตจากผู้ใช้งานอย่างชัดเจน — AdminWeb แก้ได้อิสระกว่าตาม scope ที่ได้รับ
4. **Security**: JWT access token อายุ 15 นาที, refresh token อายุ 7 วัน — ห้ามลดค่า; secret (`DB_PASSWORD`, `JWT_SECRET_KEY` ฯลฯ) ต้องมาจาก `.env`/env var เท่านั้น ห้าม hardcode ค่าจริงลงไฟล์ที่ track ใน git (เคยมี production password หลุดมาจากจุดนี้มาก่อน); input ที่ render เป็น HTML ต้องผ่าน `Backend/app/utils/sanitize.py`
5. **Port**: UserWeb = 5173, AdminWeb = 5174, Backend API = 8000
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
