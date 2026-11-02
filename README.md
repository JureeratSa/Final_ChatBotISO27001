# TUH Chatbot AI ("ขาหมู")

แชทบอทตอบคำถามบุคลากรจากเอกสารนโยบาย/ระเบียบ/ประกาศของโรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ (งานสารสนเทศ)
บอทค้นเอกสารที่เกี่ยวข้องก่อน แล้วให้ LLM ตอบจากเนื้อหานั้น พร้อมแนบลิงก์ PDF ที่ใช้ตอบ (RAG)

| ส่วน | โฟลเดอร์ | เทคโนโลยี |
|---|---|---|
| เว็บแชทบอท (บุคลากรใช้) | `apps/chat-web` | React + Vite + Tailwind |
| เว็บแอดมิน (จัดการเอกสาร/ดูสถิติ) | `apps/admin-web` | React + Vite + Tailwind |
| Backend API + ระบบค้นหา (RAG) | `services/api` | FastAPI, SQLAlchemy (async), ChromaDB, BM25 |
| ฐานข้อมูล | Microsoft SQL Server (ย้ายจาก TiDB Cloud เมื่อ 2 พ.ย. 2569) | — |

## โครงสร้างโปรเจกต์

```
PJChatbot/
├── apps/
│   ├── chat-web/                 # เว็บแชทบอท
│   │   └── src/  components/ hooks/ utils/ App.jsx
│   └── admin-web/                # เว็บแอดมิน
│       └── src/  pages/ components/ hooks/ context/ layouts/ utils/ App.jsx
├── services/
│   └── api/                      # Backend
│       ├── app/
│       │   ├── main.py           # จุดเริ่มต้น: สร้าง FastAPI app, ใส่ middleware, รวม router
│       │   ├── api/              # endpoint (1 ไฟล์ต่อ 1 หน้าที่) — รับ request แล้วเรียก services/
│       │   │   └── deps.py       # get_current_user: ตรวจ token ของแอดมิน
│       │   ├── services/         # logic ของระบบ (ตอบคำถาม, rebuild, แผนก, audit log, ...)
│       │   ├── rag/              # ระบบค้นหาเอกสาร (ดูหัวข้อ "RAG ทำงานอย่างไร")
│       │   ├── core/             # config, ฐานข้อมูล, ความปลอดภัย, rate limit
│       │   ├── models/models.py  # ตารางในฐานข้อมูล
│       │   ├── schemas/          # รูปแบบข้อมูลเข้า/ออกของ API (Pydantic)
│       │   └── utils/            # เวลาไทย, sanitize HTML
│       ├── alembic/              # migration ของฐานข้อมูล
│       ├── scripts/              # สคริปต์ดูแลระบบ (SQL Server, ลบไฟล์ค้าง)
│       ├── sql/                  # SQL สร้างตารางบน SQL Server (สร้างอัตโนมัติ)
│       └── Dockerfile
├── infra/
│   ├── docker/                   # Dockerfile + nginx ของเว็บ
│   └── scripts/
│       ├── dev.py                # รันแบบ dev
│       └── seed_volumes.py       # คัดลอกข้อมูลเดิมเข้า Docker volume (ครั้งเดียว)
├── docs/                         # คู่มือ, รายงาน, SDD, เอกสาร RAG
├── docker-compose.yml            # รันทั้งระบบ (production)
└── .github/workflows/ci.yml      # ตรวจว่าทุกส่วน build ได้
```

## RAG ทำงานอย่างไร

ทุกอย่างอยู่ใน `services/api/app/rag/` และ `services/api/app/services/chat_service.py`

**ตอนแอดมินอัปโหลดเอกสาร** (หน้า "จัดการเอกสาร")
1. `rag/ocr.py` ดึงข้อความทุกหน้า — หน้าที่เป็นภาพสแกนจะ OCR ด้วย Typhoon
2. แอดมินกดอนุมัติทีละขั้น: ข้อความดิบ → ข้อความที่คลีนแล้ว → ตัวอย่าง chunk → ใช้งาน (`services/document_service.py`)
3. `rag/indexer.py` แบ่งทุกเอกสารเป็น chunk แล้วสร้างดัชนี 2 แบบ:
   ChromaDB (เวกเตอร์ความหมายจาก `BAAI/bge-m3`) และ BM25 (คำตรงตัว ตัดคำไทยด้วย PyThaiNLP)

**ตอนผู้ใช้ถาม** (`POST /api/search`)
1. ตรงกับ FAQ ที่แอดมินตั้งคำตอบไว้ → ตอบเลย
2. `rag/retriever.py` ค้นทั้ง 2 ดัชนี แล้วรวมอันดับด้วย Weighted RRF (BM25 0.6 / Dense 0.4)
3. `rag/answer.py` ส่ง chunk ที่ได้ + ประวัติแชทให้ LLM ตอบ แล้วเลือกเฉพาะเอกสารที่ LLM บอกว่าใช้จริงมาแนบ
4. ตอบไม่ได้ → บันทึกให้แอดมินแก้ (สอนคำค้น / สอนคำตอบ) ในหน้า "คำถามที่บอทตอบไม่ได้"

## รันระบบ

### Production (Docker)

```bash
docker compose up -d --build
```
เปิดใช้งานที่ `https://<ชื่อเครื่อง>/` (แชทบอท) และ `https://<ชื่อเครื่อง>/admin/` (แอดมิน)
รายละเอียด (HTTPS, ใบรับรอง, volume, สำรองข้อมูล) อยู่ใน [docs/DOCKER.md](docs/DOCKER.md)

### Dev (ปิด Docker ก่อน เพราะใช้ port เดียวกัน)

ครั้งแรก:
```bash
cd services/api
pip install -r requirements.txt
cp .env.example .env          # ใส่ค่าจริง (DB_*, JWT_SECRET_KEY, LITELLM_*) — ไม่มีค่า default ของ secret ในโค้ด
alembic upgrade head          # ฐานข้อมูลใหม่ที่ยังไม่มีตาราง
```

รัน (3 terminal):
```bash
python infra/scripts/dev.py api      # Backend API  → http://localhost:8000
python infra/scripts/dev.py chat     # แชทบอท       → http://localhost:5173
python infra/scripts/dev.py admin    # แอดมิน       → http://localhost:5174
```
Vite รันจากไดรฟ์ Z: ไม่ได้ สคริปต์จึงคัดลอกเว็บไปรันที่ `C:\Users\<user>\tuh-*` และคอยคัดลอกไฟล์ที่แก้ให้อัตโนมัติ

ตอน dev ข้อมูล (`uploads/`, `index_db/`) อยู่ที่รากของโปรเจกต์ — ไม่ใช่ชุดเดียวกับใน Docker volume

### บัญชีแอดมินแรก

ถ้ายังไม่มีผู้ใช้ในฐานข้อมูลเลย ระบบจะสร้างบัญชีจาก `INITIAL_ADMIN_USERNAME` / `INITIAL_ADMIN_PASSWORD` ใน `.env`
ไม่ตั้งรหัสไว้ → สุ่มรหัสให้ในไฟล์ `initial_admin_password.txt` (อ่านแล้วลบทิ้ง) และบังคับเปลี่ยนตอนล็อกอินครั้งแรก

## ฐานข้อมูล (Alembic)

แก้ตารางใน `services/api/app/models/models.py` แล้วสร้าง migration ทุกครั้ง (ห้ามแก้ schema ตรงๆ):
```bash
cd services/api
alembic revision --autogenerate -m "อธิบายสั้นๆ ว่าเปลี่ยนอะไร"
# ตรวจไฟล์ที่ได้ใน alembic/versions/ ก่อนเสมอ
alembic upgrade head
```
ดู revision ปัจจุบัน: `alembic current` — เรื่องเฉพาะของ SQL Server: [docs/SQLSERVER_MIGRATION.md](docs/SQLSERVER_MIGRATION.md)

⚠️ ฐานข้อมูล SQL Server **ใช้ร่วมกับระบบอื่น** — แชทบอทเป็นเจ้าของเฉพาะตารางใน `models.py` ห้ามแตะตารางอื่นเด็ดขาด
(Alembic ถูกตั้งไม่ให้เสนอ drop ตารางที่ไม่ใช่ของเราแล้ว แต่ตรวจไฟล์ migration ทุกครั้งก่อน upgrade)

## ความปลอดภัย (สรุป)

- แอดมินล็อกอินได้ JWT access token อายุ 15 นาที — logout แล้ว token ใบนั้นใช้ต่อไม่ได้, เปลี่ยนรหัสผ่านแล้ว token เก่าทุกใบใช้ไม่ได้
- รหัสผ่าน: bcrypt, ต้องผ่านเกณฑ์ความซับซ้อน, หมดอายุทุก 90 วัน, ล็อกชั่วคราวเมื่อเดาผิดหลายครั้ง
- แอดมินแผนกเห็น/แก้ได้เฉพาะข้อมูลของแผนกตัวเอง (`services/department_scope.py`) — ทุกการแก้ไขบันทึกใน audit log
- secret ทั้งหมดอยู่ใน `services/api/.env` เท่านั้น (repo นี้เป็น public)
- PDF ฉบับร่างเปิดได้เฉพาะแอดมิน — คนทั่วไปเปิดได้เฉพาะเอกสารที่ใช้งานอยู่
