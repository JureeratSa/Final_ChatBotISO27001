"""
TUH Chatbot AI — Database Connection (async SQLAlchemy + TiDB Cloud MySQL)
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator

from app.core.config import settings

# Async Engine (TiDB Serverless requires SSL)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    connect_args={"ssl": True}
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
    """
    สร้างตารางที่ยังไม่มีตอน startup (เผื่อกรณี dev/CI ที่ยังไม่เคยรัน migration เลย)

    หมายเหตุ: การเปลี่ยนแปลง schema จริง (เพิ่ม/แก้/ลบคอลัมน์ใน DB ที่มีข้อมูลอยู่แล้ว)
    ต้องทำผ่าน Alembic migration เท่านั้น (`alembic revision --autogenerate` แล้ว
    `alembic upgrade head`) — ดู Backend/README ส่วน Database Migrations
    เดิมโค้ดตรงนี้ต่อท้ายด้วย ALTER TABLE ... try/except: pass ทีละคอลัมน์ทุกครั้งที่มีคนเพิ่ม
    field ใหม่ใน models.py ซึ่งกลืน error จริงทิ้งหมด (ต่อ DB ไม่ติด, สิทธิ์ไม่พอ ฯลฯ ก็จะเงียบ
    เหมือนสำเร็จ) และไม่มีที่มาให้ตรวจสอบว่า schema ปัจจุบันอยู่สถานะไหน — Alembic migration
    history แก้ปัญหานี้แทนแล้ว metadata.create_all() ที่เหลือไว้ตรงนี้เป็นแค่ safety net
    สำหรับ dev/CI ที่รัน SQLite ชั่วคราว ไม่ได้มีหน้าที่ปรับ schema ของ DB ที่มีอยู่แล้ว
    (create_all ไม่แก้ไข/เพิ่มคอลัมน์ในตารางที่มีอยู่แล้วอยู่แล้ว เพิ่มเฉพาะตารางที่ยังไม่มี)
    """
    from app.models import models  # noqa
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
