# TUH Chatbot AI v2

## การเริ่มต้นระบบใหม่ (v2 — Modern Architecture)

### Stack
- **Backend**: FastAPI + PostgreSQL + SQLAlchemy (async) + JWT Auth
- **Frontend**: React + Vite + TailwindCSS (Component-based)
- **Deploy**: Docker Compose
- **CI/CD**: GitHub Actions

---

## วิธีรันด้วย Docker Compose (แนะนำ)

```bash
cd v2

# Copy API key (ถ้ามี)
cp ../.env .env

# รัน services ทั้งหมด
docker compose up -d

# ดู logs
docker compose logs -f

# หยุด
docker compose down
```

**URLs:**
- Frontend: http://localhost:80
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/api/docs (debug mode only)

---

## วิธี Migrate ข้อมูลจาก v1 → v2

```bash
cd v2

# ติดตั้ง dependencies
pip install -r backend/requirements.txt

# รัน migration (PostgreSQL ต้องทำงานอยู่ก่อน)
python migrate_data.py
```

---

## วิธีรันแบบ Development (ไม่ใช้ Docker)

### Backend
```bash
cd v2/backend
pip install -r requirements.txt

# ตั้งค่า environment
export POSTGRES_HOST=localhost
export DEBUG=true

uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd v2/frontend
npm install
npm run dev
```

---

## โครงสร้างโปรเจค

```
v2/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── core/
│   │   │   ├── config.py        # Settings (pydantic-settings)
│   │   │   ├── database.py      # Async SQLAlchemy + PostgreSQL
│   │   │   └── security.py      # JWT + bcrypt
│   │   ├── models/
│   │   │   └── models.py        # SQLAlchemy ORM models
│   │   ├── schemas/
│   │   │   └── schemas.py       # Pydantic request/response schemas
│   │   ├── routers/
│   │   │   ├── auth.py          # /api/auth/* (JWT + User MGMT)
│   │   │   ├── chat.py          # /api/chat (RAG endpoint)
│   │   │   └── admin.py         # /api/admin/* (all admin APIs)
│   │   └── services/
│   │       └── rag_service.py   # HybridRetriever wrapper (async)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Main app (clean, ~200 lines)
│   │   ├── components/
│   │   │   ├── Chat/
│   │   │   │   ├── MessageBubble.jsx
│   │   │   │   └── InputBar.jsx
│   │   │   └── Admin/
│   │   │       └── AdminLogin.jsx
│   │   ├── hooks/
│   │   │   └── useChat.js       # Chat state management
│   │   ├── services/
│   │   │   └── api.js           # Axios + JWT auto-refresh
│   │   └── context/
│   │       └── AuthContext.jsx  # Auth state
│   ├── vite.config.js           # API proxy
│   └── Dockerfile
├── docker-compose.yml
└── migrate_data.py              # JSON → PostgreSQL migration
```

---

## Default Credentials
- **Admin**: `admin` / `admin1234`
- เปลี่ยนรหัสผ่านใน Admin Panel ทันทีหลัง deploy

---

## Security Notes (Cybersecurity Engineer)
- JWT Access Token: อายุ 15 นาที
- JWT Refresh Token: อายุ 7 วัน  
- Passwords: hashed ด้วย bcrypt (cost factor 12)
- CORS: จำกัดเฉพาะ frontend URL
- Rate limiting: ควรเพิ่ม nginx rate limit บน production
