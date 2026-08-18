"""
TUH Chatbot AI — Database Connection (async SQLAlchemy + PostgreSQL)
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator

from app.core.config import settings

# Async Engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

# Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class สำหรับ SQLAlchemy models ทั้งหมด"""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency สำหรับ inject database session เข้า FastAPI routes"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables():
    """สร้างตาราง Database ทั้งหมด (ใช้ตอน startup)"""
    from app.models import user, document, settings_model, feedback, unanswered, history, forms, announcements  # noqa
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
