"""
จุดเริ่มต้นของ Backend API (FastAPI)

ตอนเปิดเซิร์ฟเวอร์: สร้างตารางที่ยังไม่มี → สร้างบัญชีแอดมินแรก (ถ้ายังไม่มีผู้ใช้เลย) → โหลดดัชนีค้นหา
รันด้วย: uvicorn app.main:app --port 8000   (โฟลเดอร์ services/api)
"""
import asyncio
import logging
import re
import secrets
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import null, select

from app.api import (
    announcements, auth, chat, documents, feedback, forms, history, public, rebuild,
    settings as settings_api, stats, unanswered, users,
)
from app.core.config import settings
from app.core.database import AsyncSessionLocal, create_tables
from app.core.logging import setup_logging
from app.core.security import hash_password
from app.models.models import User
from app.rag.answer import load_retriever
from app.services.audit_service import AuditLogMiddleware

if sys.platform == "win32":
    # รัน dev บน Windows: event loop แบบ Proactor มีปัญหากับ SSL ของ aiomysql (WinError 87)
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

setup_logging()
logger = logging.getLogger(__name__)


async def create_first_admin() -> None:
    """ยังไม่มีผู้ใช้เลย → สร้างบัญชีแอดมินจาก INITIAL_ADMIN_USERNAME / INITIAL_ADMIN_PASSWORD ใน .env
    ไม่ได้ตั้งรหัสไว้ → สุ่มรหัสให้ เขียนลงไฟล์ initial_admin_password.txt (ไม่พิมพ์ลง log) และบังคับเปลี่ยนตอนล็อกอินแรก"""
    async with AsyncSessionLocal() as session:
        if (await session.execute(select(User).limit(1))).scalar_one_or_none():
            return
        password = settings.INITIAL_ADMIN_PASSWORD or secrets.token_urlsafe(12)
        admin = User(username=settings.INITIAL_ADMIN_USERNAME, password_hash=hash_password(password),
                     display_name="แอดมิน สารสนเทศ", role="System Administrator", is_active=True)
        if not settings.INITIAL_ADMIN_PASSWORD:
            admin.password_changed_at = null()   # NULL = ต้องเปลี่ยนรหัสตอนล็อกอินครั้งแรก
        session.add(admin)
        await session.commit()

    if settings.INITIAL_ADMIN_PASSWORD:
        logger.info("สร้างบัญชีแอดมินเริ่มต้นแล้ว (%s)", settings.INITIAL_ADMIN_USERNAME)
        return
    secret_file = Path(settings.DATA_DIR) / "initial_admin_password.txt"
    secret_file.write_text(
        f"username: {settings.INITIAL_ADMIN_USERNAME}\npassword: {password}\n"
        "ล็อกอินครั้งแรกแล้วระบบจะให้ตั้งรหัสใหม่ — จากนั้นลบไฟล์นี้ทิ้ง\n",
        encoding="utf-8",
    )
    secret_file.chmod(0o600)
    logger.info("สร้างบัญชีแอดมินเริ่มต้นแล้ว (%s) — รหัสผ่านอยู่ในไฟล์ %s (อ่านแล้วลบทิ้ง)",
                settings.INITIAL_ADMIN_USERNAME, secret_file)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("%s v%s starting...", settings.APP_NAME, settings.APP_VERSION)
    Path(settings.UPLOADS_DIR).mkdir(parents=True, exist_ok=True)
    await create_tables()          # สร้างเฉพาะตารางที่ยังไม่มี — การแก้ schema ใช้ Alembic
    await create_first_admin()
    load_retriever()               # ยังไม่เคย rebuild = ไม่มีดัชนี บอทยังเปิดได้แต่ตอบโดยไม่มีเอกสาร
    logger.info("%s is ready", settings.APP_NAME)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)


# ─── CORS ─────────────────────────────────────────────────────────────────────
# Docker: เว็บและ API อยู่ origin เดียวกันผ่าน Caddy (https://<host>/ และ /api/) ไม่ต้องใช้ CORS
# ที่เหลือนี้สำหรับรัน dev: Vite dev server (5173/5174) เรียก API ที่ port 8000 ข้าม origin

_octet = r"(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])"
# เครื่องในวง LAN ของโรงพยาบาล (172.30.x.x) + ชื่อเครื่องเซิร์ฟเวอร์ใน CORS_EXTRA_HOSTS
_lan_hosts = "|".join(
    [rf"172\.30\.{_octet}\.{_octet}"]
    + [re.escape(h.strip()) for h in settings.CORS_EXTRA_HOSTS.split(",") if h.strip()]
)

# AuditLogMiddleware เพิ่มก่อน CORS เพื่อให้ CORS อยู่ชั้นนอกสุด
app.add_middleware(AuditLogMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:5173", "http://localhost:5174",
                   "http://127.0.0.1:5173", "http://127.0.0.1:5174"],
    allow_origin_regex=rf"(?i)^http://(?:{_lan_hosts}):(?:5173|5174)$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Routers ──────────────────────────────────────────────────────────────────
# ไฟล์ใน uploads/ ไม่ได้เปิดเป็น static — ส่งออกผ่าน endpoint ที่ตรวจสิทธิ์แล้วเท่านั้น

for module in (public, chat, auth, users, documents, forms, announcements, settings_api,
               rebuild, feedback, unanswered, history, stats):
    app.include_router(module.router)
