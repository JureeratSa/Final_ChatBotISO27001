"""
TUH Chatbot AI v2 — FastAPI Main Application Entry Point
Tech Lead Architecture: FastAPI + Pydantic + SQLAlchemy Async + PostgreSQL
"""
import os
import sys
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

# Fix WinError 87 asyncio SSL bug on Windows
if sys.platform == 'win32':
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.database import create_tables
from app.core.security import hash_password
from app.routers import auth, chat, admin


# ─── Application Lifespan ─────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """รันเมื่อ Application เริ่มต้นและปิดตัว"""
    # ─ Startup ─
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} starting...")

    # 1. สร้างตาราง Database
    await create_tables()
    print("✅ Database tables created/verified")

    # 2. สร้าง Default Admin User (ถ้ายังไม่มี)
    await init_default_admin()
    print("✅ Admin user initialized")

    # 3. Migrate ข้อมูลจาก JSON files เก่า (ถ้ามี)
    await migrate_from_json()
    print("✅ Data migration from JSON completed")

    # 4. โหลด RAG Retriever
    try:
        from app.services.rag_service import load_retriever
        load_retriever()
    except Exception as e:
        print(f"⚠️  RAG Retriever not loaded: {e}")

    print(f"✅ {settings.APP_NAME} is ready!")
    yield

    # ─ Shutdown ─
    print(f"👋 {settings.APP_NAME} shutting down...")


# ─── Default Admin Init ───────────────────────────────────────────────────────

async def init_default_admin():
    """สร้าง Admin user เริ่มต้น (admin / admin1234) ถ้ายังไม่มีในระบบ"""
    from app.core.database import AsyncSessionLocal
    from app.models.models import User
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).limit(1))
        if result.scalar_one_or_none() is None:
            default_admin = User(
                username="admin",
                password_hash=hash_password("admin1234"),
                display_name="แอดมิน สารสนเทศ",
                role="System Administrator",
                is_active=True
            )
            session.add(default_admin)
            await session.commit()
            print("✅ Default admin user created (admin/admin1234)")


# ─── JSON Migration ───────────────────────────────────────────────────────────

async def migrate_from_json():
    """
    Migrate ข้อมูลจาก JSON files เดิมเข้า PostgreSQL
    รันครั้งเดียวตอน startup — ตรวจสอบว่า DB ว่างก่อน migrate
    """
    import json
    from app.core.database import AsyncSessionLocal
    from app.models.models import (
        SystemSettings, Document, Feedback, UnansweredQuery,
        ChatHistory, Form as FormModel, Announcement
    )
    from sqlalchemy import select

    # Path ของ JSON files เดิม (หาแบบ dynamic)
    try:
        base_dir = Path(__file__).parents[3]
        old_backend_dir = base_dir / "user" / "backend" / "db"
    except Exception:
        old_backend_dir = Path("/app/user/backend/db")

    if not old_backend_dir.exists():
        return  # ไม่มี JSON files เดิม

    async with AsyncSessionLocal() as session:
        # ─ Migrate Settings ─
        result = await session.execute(select(SystemSettings).where(SystemSettings.id == "config"))
        if not result.scalar_one_or_none():
            settings_file = old_backend_dir / "db_settings.json"
            if settings_file.exists():
                data = json.loads(settings_file.read_text(encoding="utf-8"))
                cfg = SystemSettings(
                    id="config",
                    model_name=data.get("model_name", "google/gemini-2.5-flash"),
                    temperature=float(data.get("temperature", 0.4)),
                    max_tokens=int(data.get("max_tokens", 1000)),
                    top_k=int(data.get("top_k", 3)),
                    system_prompt=data.get("system_prompt"),
                    welcome_message=data.get("welcome_message"),
                    chat_greeting=data.get("chat_greeting"),
                    custom_faqs=json.dumps(data.get("custom_faqs", []), ensure_ascii=False),
                    predefined_faqs=json.dumps(data.get("predefined_faqs", []), ensure_ascii=False),
                )
                session.add(cfg)

        # ─ Migrate Documents ─
        docs_file = old_backend_dir / "db_documents.json"
        if docs_file.exists():
            docs_count = await session.execute(
                select(Document).limit(1)
            )
            if not docs_count.scalar_one_or_none():
                docs_data = json.loads(docs_file.read_text(encoding="utf-8"))
                for d in docs_data:
                    doc = Document(
                        filename=d.get("filename", ""),
                        display_name=d.get("display_name"),
                        status=d.get("status", "Active"),
                        pages=d.get("pages"),
                        size=d.get("size"),
                        exclude_pages=",".join(map(str, d.get("exclude_pages", []))),
                    )
                    session.add(doc)

        # ─ Migrate Feedback ─
        feedback_file = old_backend_dir / "db_feedback.json"
        if feedback_file.exists():
            fb_count = await session.execute(select(Feedback).limit(1))
            if not fb_count.scalar_one_or_none():
                fb_data = json.loads(feedback_file.read_text(encoding="utf-8"))
                for f in fb_data:
                    session.add(Feedback(
                        id=f.get("msgId", f"fb-{int(__import__('time').time()*1000)}"),
                        rating=f.get("rating", "like"),
                        comment=f.get("comment"),
                        query=f.get("query"),
                    ))

        # ─ Migrate Unanswered ─
        unans_file = old_backend_dir / "db_unanswered.json"
        if unans_file.exists():
            unans_count = await session.execute(select(UnansweredQuery).limit(1))
            if not unans_count.scalar_one_or_none():
                unans_data = json.loads(unans_file.read_text(encoding="utf-8"))
                for u in unans_data:
                    session.add(UnansweredQuery(
                        id=u.get("id", f"unans-{int(__import__('time').time()*1000)}"),
                        query=u.get("query", ""),
                        count=u.get("count", 1),
                        status=u.get("status", "Pending")
                    ))

        await session.commit()


# ─── FastAPI App ──────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="TUH Chatbot AI — RAG-based Hospital Welfare Assistant",
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)


# ─── Middleware ───────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Routers ──────────────────────────────────────────────────────────────────

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(admin.router)


# ─── Health Check ─────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


@app.get("/api/forms/download/{filename}")
async def download_form_file(filename: str):
    form_path = Path(settings.UPLOADS_DIR) / "forms" / filename
    if not form_path.exists():
        raise HTTPException(status_code=404, detail="ไม่พบไฟล์แบบฟอร์มนี้")
    return FileResponse(
        path=str(form_path),
        filename=filename.split("_", 1)[-1],
        media_type="application/pdf"
    )


# ─── Serve Static PDF Files ───────────────────────────────────────────────────

uploads_path = Path(settings.UPLOADS_DIR)
if uploads_path.exists():
    app.mount("/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
