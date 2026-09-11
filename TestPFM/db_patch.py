"""
สลับ Database ของ app ให้เป็น SQLite ไฟล์ local แทน MySQL/TiDB จริง — ไม่ต้องพึ่ง Docker/MySQL เลย
(หลักการเดียวกับที่ Backend/tests/conftest.py ใช้ SQLite in-memory สำหรับ pytest)

รับประกันว่า process นี้จะไม่มีทางไปแตะ TiDB Cloud production ไม่ว่า Backend/.env จะตั้งค่า
DB_HOST/DB_USER/... ไว้เป็นอะไรก็ตาม เพราะ engine ถูกสร้างขึ้นใหม่ทับของเดิมตรงนี้เลย

⚠️ ข้อจำกัดที่ต้องรู้: SQLite ล็อกทั้งไฟล์ตอนเขียน (ต่างจาก MySQL/TiDB ที่ lock ระดับแถว)
   ที่ concurrency สูงมากๆ ตัวเลข throughput จาก load test ผ่าน DB นี้อาจ "ต่ำกว่า" ของจริงบน
   MySQL/TiDB เพราะ SQLite เองกลายเป็นคอขวดเทียม ไม่ใช่ตัว pipeline โค้ดเรา — ใช้ตัวเลขนี้เทียบ
   "relative" ระหว่างการรันแต่ละครั้งได้ (เช่น ก่อน/หลังแก้โค้ด) แต่อย่าฟันธงว่าคือ capacity จริง
   ของ production ถ้าต้องการตัวเลขที่แม่นตรงกับ production ให้ใช้ docker-compose.testdb.yml
   (MySQL) แทนแล้วชี้ Backend/.env ไปที่นั่น

ใช้: ต้องเรียก patch_database() ก่อน import app.main เสมอ (ดูตัวอย่างใน mock_server.py)
"""
from pathlib import Path

DEFAULT_DB_FILE = Path(__file__).resolve().parent / "testdata.db"


def patch_database(db_file: Path = DEFAULT_DB_FILE, echo: bool = False,
                    pool_size: int = 50, max_overflow: int = 100):
    from sqlalchemy import event
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

    import app.core.database as db_module

    # ต้องตั้ง pool_size/max_overflow ให้กว้างกว่า database.py ตัวจริง (10/20) เสมอ ไม่งั้นตอน
    # load test ที่ concurrency สูง จะเจอ "QueuePool limit ... connection timed out" ซึ่งเป็น
    # ข้อจำกัดปลอมของ pool เอง ไม่ใช่ของ pipeline/SQLite ที่กำลังพยายามวัดจริง
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_file}", echo=echo,
        pool_size=pool_size, max_overflow=max_overflow,
    )

    # เปิด WAL mode ลดปัญหา "database is locked" ตอนมี concurrent request จาก load test
    @event.listens_for(engine.sync_engine, "connect")
    def _set_pragmas(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    db_module.engine = engine
    db_module.AsyncSessionLocal = session_maker

    print(f"[db_patch] ใช้ SQLite local: {db_file} (รับประกันไม่แตะ production DB)")
    return engine
