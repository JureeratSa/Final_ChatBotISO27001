"""
Shared pytest fixtures — สร้าง FastAPI test app แยกจากของจริง
โดยสลับ DB ไปเป็น SQLite in-memory (ไม่แตะ TiDB Cloud ของ production)
"""
import sys
from pathlib import Path

# ให้ import "app.xxx" ได้เหมือนตอนรัน uvicorn จาก Backend/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

import app.core.database as db_module
from app.core.database import Base, get_db
from app.core.security import hash_password, create_access_token
from app.models.models import User
from app.routers import (
    auth, chat, public, admin_feedback, admin_unanswered, admin_rag, admin_stats,
    admin_forms, admin_announcements, admin_history, admin_auth,
    admin_documents, admin_settings, admin_rebuild
)


@pytest_asyncio.fixture
async def test_engine():
    """SQLite in-memory engine แยกต่างหากต่อ 1 เทส (StaticPool กันหลุด connection)"""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session_maker(test_engine, monkeypatch):
    """
    ผูก AsyncSessionLocal ของ app.core.database ให้ชี้มาที่ SQLite ทดสอบ
    เพราะ chat.py ใช้ `from app.core.database import AsyncSessionLocal` ตรงๆ
    ใน background task (save_history / save_unanswered)
    """
    maker = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(db_module, "AsyncSessionLocal", maker)
    return maker


@pytest_asyncio.fixture
async def app_instance(session_maker):
    """FastAPI app เปล่าๆ ที่ mount เฉพาะ router ที่จะเทส (ไม่รัน lifespan ของ main.py จริง)"""
    application = FastAPI()
    application.include_router(auth.router)
    application.include_router(chat.router)
    application.include_router(admin_documents.router)
    application.include_router(admin_settings.router)
    application.include_router(admin_rebuild.router)
    application.include_router(admin_feedback.router)
    application.include_router(admin_unanswered.router)
    application.include_router(admin_rag.router)
    application.include_router(admin_stats.router)
    application.include_router(admin_forms.router)
    application.include_router(admin_announcements.router)
    application.include_router(admin_history.router)
    application.include_router(admin_auth.router)
    application.include_router(public.router)

    async def _get_db_override():
        async with session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    application.dependency_overrides[get_db] = _get_db_override
    return application


@pytest_asyncio.fixture
async def client(app_instance):
    transport = ASGITransport(app=app_instance)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session(session_maker):
    async with session_maker() as session:
        yield session


# ─── User factory fixtures ─────────────────────────────────────────────────────

async def _create_user(session, *, username, password, display_name, role, department=None, is_active=True):
    user = User(
        username=username,
        password_hash=hash_password(password),
        display_name=display_name,
        role=role,
        department=department,
        is_active=is_active,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db_session):
    return await _create_user(
        db_session,
        username="sysadmin",
        password="Adm1n!2345",
        display_name="ผู้ดูแลระบบ",
        role="System Administrator",
    )


@pytest_asyncio.fixture
async def staff_user(db_session):
    return await _create_user(
        db_session,
        username="staff01",
        password="Staff!2345",
        display_name="เจ้าหน้าที่ ก",
        role="admin",
        department="งานสารสนเทศ",
    )


@pytest_asyncio.fixture
async def other_staff_user(db_session):
    return await _create_user(
        db_session,
        username="staff02",
        password="Staff!6789",
        display_name="เจ้าหน้าที่ ข",
        role="admin",
        department="งานทรัพยากรบุคคล",
    )


def auth_header(username: str) -> dict:
    """สร้าง Authorization header จาก username โดยไม่ต้องยิง /login จริง (unit-level shortcut)"""
    token = create_access_token({"sub": username})
    return {"Authorization": f"Bearer {token}"}
