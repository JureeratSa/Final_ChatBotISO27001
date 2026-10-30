"""
เชื่อมต่อฐานข้อมูล (async SQLAlchemy) — TiDB Cloud (MySQL) เป็นค่าเริ่มต้น, SQL Server เมื่อตั้ง DB_ENGINE=mssql
endpoint ขอ session ผ่าน Depends(get_db) — จบ request แล้ว commit ให้อัตโนมัติ (error = rollback)
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator

from app.core.config import settings
from app.core import mssql_types  # noqa: F401  — String/Text เป็น NVARCHAR บน SQL Server (ไม่มีผลกับ MySQL)

# ─── 1. Async Database Engine ──────────────────────────────────────────────────
# ตั้งค่า Connection Pool และเปิดใช้งาน SSL สำหรับ TiDB Serverless
# - pool_size=10: จำนวน Connection หลักที่เปิดค้างไว้ใน Pool
# - max_overflow=20: จำนวน Connection ชั่วคราวที่เปิดเพิ่มได้เมื่อมี Request หนาแน่น
# - pool_pre_ping=True: ทดสอบ Ping ตรวจสอบ Connection ก่อนส่งให้ Query ป้องกัน Connection หลุด
# SQL Server: การเข้ารหัสกำหนดใน URL (Encrypt / TrustServerCertificate — ดู config.py) ไม่ใช้ connect_args ssl
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    connect_args={} if settings.DB_ENGINE == "mssql" else {"ssl": True}
)

# ─── 2. Async Session Factory ──────────────────────────────────────────────────
# ตัวสร้าง Database Session สำหรับการทำงานแบบ Async
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # ไม่ expire attributes หลัง commit เพื่อให้อ่านค่าต่อได้
)


# ─── 3. Declarative Base Class ─────────────────────────────────────────────────
class Base(DeclarativeBase):
    """Base class หลักสำหรับ SQLAlchemy models ทั้งหมดในระบบ"""
    pass


# ─── 4. Database Session Dependency ────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI Dependency: จ่าย Database Session ให้กับ Route Handlers แต่ละตัว
    - เมื่อทำงานสำเร็จ: ทำการ commit() ข้อมูลลงฐานข้อมูลอัตโนมัติ
    - หากเกิด Exception: ทำการ rollback() ทันทีเพื่อป้องกันข้อมูลเสียหาย
    - เมื่อเสร็จสิ้น: ปิด Session และคืน Connection กลับ Pool เสมอ
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ─── 5. Table Initialization Helper ───────────────────────────────────────────
async def create_tables():
    """
    สร้างตารางฐานข้อมูลที่ยังไม่มีตอน Startup (Safety Net สำหรับกรณี Initial Setup)
    หมายเหตุ: สำหรับการเปลี่ยนแปลง Schema บน Production (เพิ่ม/ลดคอลัมน์)
    ให้ใช้ Alembic Migration เสมอ (alembic revision --autogenerate && alembic upgrade head)
    """
    from app.models import models  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

