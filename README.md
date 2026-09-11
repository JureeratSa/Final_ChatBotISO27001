# TUH Chatbot AI

## การเริ่มต้นระบบใหม่ (Modern Reorganized Architecture)

### Stack
- **Backend**: FastAPI + TiDB Cloud (MySQL) + SQLAlchemy (async) + JWT Auth
- **Frontend (User/Admin)**: React + Vite + TailwindCSS
- **CI/CD**: GitHub Actions

---

## วิธีรันด้วย Scripts (แนะนำ)

รันคำสั่งต่อไปนี้ที่ root directory เพื่อเริ่มใช้งานเซิร์ฟเวอร์แบบ Local Development:

- **Backend**: `python run_backend.py`
- **Chatbot Frontend (User)**: `python run_user_web.py`
- **Admin Frontend**: `python run_admin_web.py`

**URLs:**
- Chatbot Frontend (User): [http://localhost:5173](http://localhost:5173)
- Admin Frontend: [http://localhost:5174](http://localhost:5174)
- Backend API: [http://localhost:8000](http://localhost:8000)

---

## วิธีรันแบบ Development (รันตรงด้วย CLI)

### Backend
```bash
cd Backend
pip install -r requirements.txt

# 1. คัดลอก .env.example เป็น .env แล้วใส่ค่าจริง (DB_*, JWT_SECRET_KEY เป็นต้น)
#    ไม่มีค่า default ในโค้ดแล้ว — app จะ start ไม่ขึ้นถ้าไม่ตั้งค่าพวกนี้ (ดู core/config.py)
cp .env.example .env

# 2. เตรียม schema ของ DB ก่อนรันครั้งแรก (ดูรายละเอียดใน "Database Migrations" ด้านล่าง)
alembic upgrade head

# uvicorn app.main:app --reload --port 8000
```

### User Web
```bash
cd UserWeb
npm install
npm run dev -- --port 5173
```

### Admin Web
```bash
cd AdminWeb
npm install
npm run dev -- --port 5174
```

Local dev ไม่ต้องตั้งค่าอะไรเพิ่ม (frontend หา backend จาก hostname ปัจจุบันอัตโนมัติ) —
ตอน deploy จริงหลัง HTTPS/reverse proxy หรือ backend คนละโดเมน ให้คัดลอก `.env.example`
เป็น `.env.local` ในแต่ละโฟลเดอร์แล้วตั้งค่า `VITE_API_URL` (ดูรายละเอียดในไฟล์นั้น)

---

## Database Migrations (Alembic)

Schema ของ DB จัดการผ่าน Alembic แล้ว (ก่อนหน้านี้ startup โค้ดใน `core/database.py` ต่อท้ายด้วย
`ALTER TABLE ... try/except: pass` ทีละคอลัมน์ ซึ่งกลืน error จริงทิ้งและไม่มี history ให้ตรวจสอบ)

**DB ใหม่ที่ยังไม่มีตารางเลย** (เช่น TestPFM cluster ใหม่, เครื่อง dev เครื่องใหม่):
```bash
cd Backend
alembic upgrade head
```

**DB ที่มีตารางอยู่แล้วจากก่อนเปลี่ยนมาใช้ Alembic** (เช่น production/test cluster ปัจจุบัน) —
ห้ามรัน `upgrade head` ตรงๆ เพราะ migration แรกจะพยายาม `CREATE TABLE` ที่มีอยู่แล้วแล้ว fail
ให้ "แปะ" ว่า DB อยู่ที่ revision ล่าสุดแล้วโดยไม่รัน SQL จริงแทน (ทำครั้งเดียวตอน migrate มาใช้ Alembic):
```bash
cd Backend
alembic stamp head
```

**เพิ่ม/แก้ไข column ใหม่ในอนาคต** — แก้ `app/models/models.py` แล้วสร้าง migration:
```bash
alembic revision --autogenerate -m "อธิบายสั้นๆ ว่าเปลี่ยนอะไร"
# ตรวจไฟล์ที่ได้ใน alembic/versions/ ก่อนเสมอ (autogenerate เดาไม่ได้ทุกกรณี)
alembic upgrade head
```

ตรวจสอบ revision ปัจจุบันของ DB ที่ต่ออยู่: `alembic current` — ดู history ทั้งหมด: `alembic history`

---

## โครงสร้างโปรเจค

```
PJChatbot/
├── Backend/                    # FastAPI Backend
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── core/
│   │   │   ├── config.py        # Settings (pydantic-settings)
│   │   │   ├── database.py      # Async SQLAlchemy + TiDB Cloud
│   │   │   └── rate_limit.py    # Rate limiting (best-effort, in-memory)
│   │   ├── utils/
│   │   │   └── sanitize.py      # HTML sanitizer (nh3) กัน Stored XSS
│   │   └── routers/
│   │       ├── auth.py          # /api/auth/*
│   │       ├── chat.py          # /api/chat
│   │       └── admin.py         # /api/admin/*
│   ├── alembic/                  # DB schema migrations (ดู "Database Migrations" ด้านบน)
│   ├── alembic.ini
│   └── requirements.txt
├── UserWeb/                    # React User Chatbot Frontend
│   ├── src/
│   │   ├── App.jsx
│   │   └── components/
│   └── package.json
├── AdminWeb/                   # React Admin Portal Frontend
│   ├── src/
│   │   └── App.jsx
│   └── package.json
├── Admin/                      # Legacy Python RAG Toolset
│   ├── cleanData.py
│   ├── emb.py
│   └── rebuild_db.py
├── run_backend.py              # Backend Runner
├── run_user_web.py             # User Chatbot Frontend Runner
└── run_admin_web.py            # Admin Frontend Runner
```

---

## Default Credentials
- ตั้งค่า `INITIAL_ADMIN_USERNAME` / `INITIAL_ADMIN_PASSWORD` ใน `.env` ก่อน start ครั้งแรก
- ถ้าไม่ตั้ง `INITIAL_ADMIN_PASSWORD` ระบบจะสุ่มรหัสผ่านให้และ print ออก console ตอน startup
  ครั้งเดียวเท่านั้น (ไม่มี default แบบรู้ล่วงหน้าได้เช่น `admin1234` อีกต่อไป)
- เปลี่ยนรหัสผ่านใน Admin Panel ทันทีหลัง login (ขั้นต่ำ 8 ตัวอักษร)

---

## Security Notes
- JWT Access Token: อายุ 15 นาที
- JWT Refresh Token: อายุ 7 วัน  
- Passwords: hashed ด้วย bcrypt (cost factor 12)
- CORS: จำกัดเฉพาะ frontend URL
