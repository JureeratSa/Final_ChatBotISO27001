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

---

## โครงสร้างโปรเจค

```
PJChatbot/
├── Backend/                    # FastAPI Backend
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── core/
│   │   │   ├── config.py        # Settings (pydantic-settings)
│   │   │   └── database.py      # Async SQLAlchemy + TiDB Cloud
│   │   └── routers/
│   │       ├── auth.py          # /api/auth/*
│   │       ├── chat.py          # /api/chat
│   │       └── admin.py         # /api/admin/*
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
- **Admin**: `admin` / `admin1234`
- เปลี่ยนรหัสผ่านใน Admin Panel ทันทีหลัง login

---

## Security Notes
- JWT Access Token: อายุ 15 นาที
- JWT Refresh Token: อายุ 7 วัน  
- Passwords: hashed ด้วย bcrypt (cost factor 12)
- CORS: จำกัดเฉพาะ frontend URL
