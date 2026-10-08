"""
TUH Chatbot AI — Rebuild Service
แยกจาก app/routers/admin_rebuild.py / admin_documents.py (เดิมอยู่ใน Backend/app/routers/admin.py)

หมายเหตุสำคัญสำหรับเทส: test_rebuild_status.py และ test_documents_ownership.py
monkeypatch ชื่อ _trigger_rebuild_background / _delete_from_search_index โดยแพตช์ที่
โมดูลที่ "เรียกใช้" (admin_rebuild / admin_documents) ไม่ใช่ที่นี่ — เพราะ
`from app.services.rebuild_service import _trigger_rebuild_background` เป็นการผูกชื่อ
เข้ากับ namespace ของโมดูลปลายทางตอน import ครั้งเดียว แพตช์ที่นี่จะไม่มีผลกับ
reference ที่ผูกไปแล้วในโมดูลอื่น
"""
import logging
import time
from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import SystemSettings

logger = logging.getLogger(__name__)


async def _get_or_create_settings_row(db: AsyncSession) -> SystemSettings:
    result = await db.execute(select(SystemSettings).where(SystemSettings.id == "config"))
    cfg = result.scalar_one_or_none()
    if not cfg:
        cfg = SystemSettings(id="config")
        db.add(cfg)
        await db.flush()
    return cfg


def _sync_update_rebuild_status(status: str, message: str, duration: Optional[float] = None):
    """
    เขียนสถานะ rebuild ลง DB แบบ sync — เรียกจาก _trigger_rebuild_background() ซึ่งรันอยู่ใน
    thread pool ของ BackgroundTasks (ไม่ใช่ event loop) จึงใช้ AsyncSession ตรงๆ ไม่ได้
    ใช้ DATABASE_URL_SYNC (pymysql) แยกต่างหาก เปิด/ปิด engine ทุกครั้งเพราะเรียกไม่บ่อย
    (แค่ตอนเริ่ม/จบ rebuild หนึ่งรอบ) ไม่คุ้มที่จะเก็บ engine ไว้เป็น singleton ข้าม thread
    """
    from sqlalchemy import create_engine, update as sql_update

    sync_engine = create_engine(settings.DATABASE_URL_SYNC)
    try:
        with sync_engine.begin() as conn:
            values = {"rebuild_status": status, "rebuild_message": message}
            if duration is not None:
                values["last_build_duration"] = duration
            result = conn.execute(
                sql_update(SystemSettings.__table__).where(SystemSettings.id == "config").values(**values)
            )
            if result.rowcount == 0:
                conn.execute(SystemSettings.__table__.insert().values(id="config", **values))
    except Exception as e:
        logger.error("[Rebuild Status Write Error] %s", e)
    finally:
        sync_engine.dispose()


def _delete_from_search_index(filename: str):
    """ลบ chunk ของเอกสาร filename ออกจากดัชนี BM25 + ChromaDB ทันที (ไม่ rebuild ทั้งคลังใหม่)
    เรียกเป็น background task ตอนลบเอกสาร (ดู delete_document / delete_document_post) — ปิดช่องว่าง
    เดิมที่การลบเอกสารเชื่อมกับ ChromaDB ผ่านการสั่ง rebuild ทั้งคลังเท่านั้น (ดู Admin/emb.py
    :func:`delete_document_from_index` สำหรับเหตุผลเต็ม)"""
    try:
        import sys
        admin_parent = str(Path(settings.ADMIN_DIR).parent)
        if admin_parent not in sys.path:
            sys.path.insert(0, admin_parent)

        from Admin.emb import delete_document_from_index
        from app.services.rag_service import get_retriever

        removed = delete_document_from_index(filename, retriever=get_retriever())
        logger.info("[Delete Index] ลบ %s chunk ของ '%s' ออกจากดัชนีค้นหาแล้ว", removed, filename)
    except Exception as e:
        logger.error("[Delete Index Error] ลบ '%s' ออกจากดัชนีค้นหาไม่สำเร็จ: %s", filename, e)


def _sync_load_documents() -> list:
    """รายการเอกสาร (สถานะ + หน้าที่ละเว้น) จาก TiDB ส่งให้ Admin.rebuild_db.rebuild() — แทน
    db_documents.json เดิมที่เลิกใช้แล้ว (ว่างเปล่า) ซึ่งทำให้ rebuild นำเข้า PDF ทุกไฟล์รวมที่ปิดใช้งาน
    และไม่ละเว้นหน้าที่แอดมินตั้งไว้ — โหลดไม่ได้ให้ล้มทั้ง rebuild แทนการนำเข้าทุกไฟล์แบบเงียบๆ"""
    from sqlalchemy import create_engine
    from app.models.models import Document
    from app.services.document_service import _parse_exclude_pages

    sync_engine = create_engine(settings.DATABASE_URL_SYNC)
    try:
        with sync_engine.connect() as conn:
            rows = conn.execute(
                select(Document.filename, Document.status, Document.exclude_pages)
            ).all()
    finally:
        sync_engine.dispose()
    return [{"filename": f, "status": s, "exclude_pages": _parse_exclude_pages(ex)} for f, s, ex in rows]


def _sync_save_durations(durations: dict) -> None:
    """บันทึกเวลาสกัดคำ/ทำ embedding ของแต่ละเอกสารลง documents (เดิมเขียนลง db_documents.json)"""
    if not durations:
        return
    from sqlalchemy import create_engine, update as sql_update
    from app.models.models import Document

    sync_engine = create_engine(settings.DATABASE_URL_SYNC)
    try:
        with sync_engine.begin() as conn:
            for filename, values in durations.items():
                conn.execute(sql_update(Document.__table__).where(Document.filename == filename).values(**values))
    except Exception as e:
        logger.error("[Rebuild Durations Write Error] %s", e)
    finally:
        sync_engine.dispose()


def _trigger_rebuild_background():
    """Background thread สำหรับ Rebuild Index"""
    start = time.time()
    try:
        import sys
        admin_parent = str(Path(settings.ADMIN_DIR).parent)
        if admin_parent not in sys.path:
            sys.path.insert(0, admin_parent)

        from Admin.rebuild_db import rebuild
        _sync_update_rebuild_status("processing", "กำลัง rebuild index...")
        durations = rebuild(documents=_sync_load_documents())
        _sync_save_durations(durations or {})

        from app.services.rag_service import reload_retriever
        reload_retriever()

        duration = round(time.time() - start, 2)
        _sync_update_rebuild_status("success", f"Rebuild สำเร็จใน {duration} วินาที", duration=duration)
    except Exception as e:
        _sync_update_rebuild_status("error", f"เกิดข้อผิดพลาด: {e}")
