"""
TUH Chatbot AI v2 — FastAPI Main Application Entry Point
Tech Lead Architecture: FastAPI + Pydantic + SQLAlchemy Async + PostgreSQL
"""
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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import create_tables
from app.core.security import hash_password
from app.core.logging_config import setup_logging
from app.routers import auth, chat, admin, public

setup_logging()
import logging  # noqa: E402
logger = logging.getLogger(__name__)


# ─── Application Lifespan ─────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """รันเมื่อ Application เริ่มต้นและปิดตัว"""
    # ─ Startup ─
    logger.info("🚀 %s v%s starting...", settings.APP_NAME, settings.APP_VERSION)

    # 1. สร้างตาราง Database (schema migration จริงจัดการด้วย Alembic แล้ว — ดู Backend/README)
    await create_tables()
    logger.info("✅ Database tables created/verified")

    # 2. สร้าง Default Admin User (ถ้ายังไม่มี)
    await init_default_admin()
    logger.info("✅ Admin user initialized")

    # หมายเหตุ: การ migrate ข้อมูลจาก JSON เดิม (v1) ย้ายไปเป็นสคริปต์แยกแล้ว เพราะเป็นงาน
    # one-shot ไม่ควรรันทุกครั้งที่ startup — รันด้วยมือครั้งเดียวตอน migrate จากระบบเก่า:
    #   cd Backend && python -m scripts.migrate_from_json

    # 3. โหลด RAG Retriever
    try:
        from app.services.rag_service import load_retriever
        load_retriever()
    except Exception as e:
        logger.warning("⚠️  RAG Retriever not loaded: %s", e)

    logger.info("✅ %s is ready!", settings.APP_NAME)
    yield

    # ─ Shutdown ─
    logger.info("👋 %s shutting down...", settings.APP_NAME)


# ─── Default Admin Init ───────────────────────────────────────────────────────

async def init_default_admin():
    """
    สร้าง Admin user เริ่มต้นถ้ายังไม่มีผู้ใช้ในระบบเลย
    ใช้ INITIAL_ADMIN_USERNAME / INITIAL_ADMIN_PASSWORD จาก .env ถ้าตั้งไว้
    ถ้าไม่ตั้ง INITIAL_ADMIN_PASSWORD ระบบจะสุ่มรหัสผ่านให้และ print ออก console
    ครั้งเดียวตอนนี้เท่านั้น (ไม่ใช้รหัสผ่านที่รู้ล่วงหน้าได้เช่น admin1234 อีกต่อไป)
    """
    import secrets
    from app.core.database import AsyncSessionLocal
    from app.models.models import User
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).limit(1))
        if result.scalar_one_or_none() is None:
            password = settings.INITIAL_ADMIN_PASSWORD
            generated = False
            if not password:
                password = secrets.token_urlsafe(12)
                generated = True

            default_admin = User(
                username=settings.INITIAL_ADMIN_USERNAME,
                password_hash=hash_password(password),
                display_name="แอดมิน สารสนเทศ",
                role="System Administrator",
                is_active=True
            )
            session.add(default_admin)
            await session.commit()
            if generated:
                logger.info("=" * 70)
                logger.info("✅ สร้างบัญชีแอดมินเริ่มต้นแล้ว: %s", settings.INITIAL_ADMIN_USERNAME)
                logger.info("🔑 รหัสผ่านที่สุ่มให้ (แสดงครั้งนี้ครั้งเดียว): %s", password)
                logger.info("   กรุณาบันทึกรหัสนี้ไว้แล้วเปลี่ยนรหัสผ่านทันทีหลัง login")
                logger.info("=" * 70)
            else:
                logger.info("✅ Default admin user created (%s)", settings.INITIAL_ADMIN_USERNAME)


# หมายเหตุ: การ migrate ข้อมูลจาก JSON เดิม (v1) ย้ายไปอยู่ที่ scripts/migrate_from_json.py แล้ว
# (รันด้วยมือครั้งเดียวตอนต้องการ ไม่ใช่ทุกครั้งที่ startup — ดูเหตุผลใน lifespan() ด้านบน)


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

# Configure explicit allowed origins for CORS security (CWE-942 mitigation)
allowed_origins = [
    settings.FRONTEND_URL,
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
]

# เครื่องในโรงพยาบาลเข้าถึง AdminWeb/UserWeb ผ่าน IP หลายเครื่องในวง LAN
# (subnet 172.30.0.0/16) ไม่ใช่แค่เครื่องเดียว — เดิม hardcode เฉพาะ
# 172.30.246.173 ทำให้เครื่องอื่นในวงเดียวกัน login ไม่ได้ (CORS block ตอนยิง
# POST /auth/login เพราะ Origin header ไม่ตรง allowlist แบบ exact-match)
# ใช้ allow_origin_regex แทน โดย anchor ทั้งสองด้าน (^...$) จำกัดเฉพาะ
# scheme http, host เป็น IPv4 รูปแบบ 172.30.x.x (x = 0-255 เท่านั้น, กัน
# bypass เช่น "http://172.30.1.1.evil.com") และพอร์ตเฉพาะ 5173/5174
# (UserWeb/AdminWeb dev server) เท่านั้น ไม่เปิดกว้างทุกพอร์ตหรือทุก subnet
_octet = r"(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])"
allowed_origin_regex = rf"^http://172\.30\.{_octet}\.{_octet}:(?:5173|5174)$"

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=allowed_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Routers ──────────────────────────────────────────────────────────────────
# (health check, file downloads, และ legacy compatibility endpoints ย้ายไปอยู่ที่
# app/routers/public.py แล้ว — main.py เดิมยาวเกือบ 300 บรรทัดเพราะมี route handler
# ปนอยู่กับ FastAPI app setup ทำให้หา entry point จริงยาก)

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(admin.router)
app.include_router(public.router)


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
