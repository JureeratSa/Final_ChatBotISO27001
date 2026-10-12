"""
TUH Chatbot AI — Database Connection (async SQLAlchemy + TiDB Cloud MySQL)
จัดการการเชื่อมต่อฐานข้อมูลแบบ Asynchronous I/O รองรับ High-Concurrency
- Database: TiDB Cloud (Serverless MySQL)
- Driver: aiomysql (Async) / pymysql (Sync)
- ORM: SQLAlchemy 2.0 (Mapped Column Syntax)
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator

from app.core.config import settings

# ─── 1. Async Database Engine ──────────────────────────────────────────────────
# ตั้งค่า Connection Pool และเปิดใช้งาน SSL สำหรับ TiDB Serverless
# - pool_size=10: จำนวน Connection หลักที่เปิดค้างไว้ใน Pool
# - max_overflow=20: จำนวน Connection ชั่วคราวที่เปิดเพิ่มได้เมื่อมี Request หนาแน่น
# - pool_pre_ping=True: ทดสอบ Ping ตรวจสอบ Connection ก่อนส่งให้ Query ป้องกัน Connection หลุด
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    connect_args={"ssl": True}
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

