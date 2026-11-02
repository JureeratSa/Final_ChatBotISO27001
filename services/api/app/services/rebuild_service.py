"""
สร้างดัชนีค้นหาใหม่ (rebuild) เบื้องหลัง + ลบเอกสารออกจากดัชนี

rebuild รันใน thread ของ BackgroundTasks (ไม่ใช่ event loop) จึงคุยกับฐานข้อมูลด้วย engine แบบ sync
ความคืบหน้าเก็บในหน่วยความจำ — AdminWeb ดึงไปแสดงผ่าน /api/admin/documents/index_status
"""
import json
import logging
import re
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Optional

from sqlalchemy import create_engine, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import Document, SystemSettings
from app.rag.answer import get_retriever, reload_retriever
from app.services.document_service import parse_exclude_pages

logger = logging.getLogger(__name__)


async def get_or_create_settings_row(db: AsyncSession) -> SystemSettings:
    cfg = (await db.execute(select(SystemSettings).where(SystemSettings.id == "config"))).scalar_one_or_none()
    if not cfg:
        cfg = SystemSettings(id="config")
        db.add(cfg)
        await db.flush()
    return cfg


# ─── ฐานข้อมูลแบบ sync (ใช้ใน thread ของ rebuild) ───────────────────────────

@contextmanager
def sync_connection():
    # เรียกไม่บ่อย (ต้น/ท้าย rebuild) — เปิด engine ใหม่ทุกครั้ง ไม่ต้องเก็บไว้ข้าม thread
    engine = create_engine(settings.DATABASE_URL_SYNC, **settings.DB_ENGINE_OPTIONS)
    try:
        with engine.begin() as conn:
            yield conn
    finally:
        engine.dispose()


def save_rebuild_status(status: str, message: str, duration: Optional[float] = None) -> None:
    values = {"rebuild_status": status, "rebuild_message": message}
    if duration is not None:
        values["last_build_duration"] = duration
    try:
        with sync_connection() as conn:
            table = SystemSettings.__table__
            if conn.execute(update(table).where(SystemSettings.id == "config").values(**values)).rowcount == 0:
                conn.execute(table.insert().values(id="config", **values))
    except Exception as e:
        logger.error("[Rebuild] บันทึกสถานะไม่สำเร็จ: %s", e)


def load_documents_for_rebuild() -> list:
    """สถานะ + หน้าที่ละเว้นของทุกเอกสาร — โหลดไม่ได้ให้ rebuild ล้ม (ดีกว่านำเข้าทุกไฟล์แบบไม่รู้สถานะ)"""
    with sync_connection() as conn:
        rows = conn.execute(select(Document.filename, Document.status, Document.exclude_pages)).all()
    return [{"filename": f, "status": s, "exclude_pages": parse_exclude_pages(ex)} for f, s, ex in rows]


def save_durations(durations: dict) -> None:
    """เวลาที่ใช้สกัดคำ/ทำ embedding ของแต่ละเอกสาร (แสดงในหน้าเอกสาร)"""
    if not durations:
        return
    try:
        with sync_connection() as conn:
            for filename, values in durations.items():
                conn.execute(update(Document.__table__).where(Document.filename == filename).values(**values))
    except Exception as e:
        logger.error("[Rebuild] บันทึกเวลาประมวลผลไม่สำเร็จ: %s", e)


# ─── ลบเอกสารออกจากดัชนี ─────────────────────────────────────────────────────

def cache_file_prefix(filename: str) -> str:
    """ชื่อไฟล์ cache ของ rebuild ใน uploads/cache (ต้องตรงกับ _cache_file ใน rag/indexer.py)"""
    return re.sub(r'[^\w฀-๿\.\-]', '_', filename) + "_"


def delete_document_leftovers(filename: str) -> None:
    """ลบ cache chunk+embedding และ chunk ใน sample_chunks.json ของไฟล์ที่ถูกลบ"""
    cache_dir = Path(settings.UPLOADS_DIR) / "cache"
    if cache_dir.is_dir():
        for f in cache_dir.iterdir():
            if f.name.startswith(cache_file_prefix(filename)) and f.suffix == ".json":
                try:
                    f.unlink()
                except OSError as e:
                    logger.error("[Delete] ลบ %s ไม่สำเร็จ: %s", f.name, e)

    chunks_path = Path(settings.CHUNKS_FILE)
    if chunks_path.exists():
        try:
            data = json.loads(chunks_path.read_text(encoding="utf-8"))
            kept = [c for c in data if (c.get("metadata") or {}).get("source") != filename]
            if len(kept) != len(data):
                chunks_path.write_text(json.dumps(kept, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error("[Delete] แก้ sample_chunks.json ไม่สำเร็จ: %s", e)


def delete_from_search_index(filename: str) -> None:
    """ลบ chunk ของเอกสารออกจาก BM25 + ChromaDB ทันที (ไม่ต้อง rebuild ทั้งคลัง)"""
    from app.rag.retriever import delete_document_from_index
    try:
        removed = delete_document_from_index(filename, retriever=get_retriever())
        logger.info("[Delete] ลบ %s chunk ของ '%s' ออกจากดัชนีแล้ว", removed, filename)
    except Exception as e:
        logger.error("[Delete] ลบ '%s' ออกจากดัชนีไม่สำเร็จ: %s", filename, e)
    delete_document_leftovers(filename)


# ─── rebuild + ความคืบหน้า ───────────────────────────────────────────────────

_rebuild_lock = threading.Lock()      # rebuild ทีละรอบ — สองรอบพร้อมกันจะเขียนดัชนีทับกัน
_progress_lock = threading.Lock()
_progress = {"running": False, "queued": 0, "percent": 0, "stage": "", "error": None}
_pending: Dict[str, float] = {}       # เอกสารที่รอเข้าดัชนี {filename: เวลาที่ mark}


def mark_pending(filename: str) -> None:
    with _progress_lock:
        _pending[filename] = time.time()


def _set_progress(percent: Optional[float] = None, stage: Optional[str] = None, **extra) -> None:
    with _progress_lock:
        if percent is not None:
            _progress["percent"] = max(0, min(100, int(percent)))
        if stage is not None:
            _progress["stage"] = stage
        _progress.update(extra)


def get_index_status() -> dict:
    """indexed = เอกสารที่ retriever ที่ใช้ตอบอยู่ตอนนี้มี chunk ของไฟล์นั้นจริง"""
    chunks = getattr(get_retriever(), "bm25_chunks", None) or []
    indexed = {(c.get("metadata") or {}).get("source") for c in chunks}
    indexed.discard(None)
    with _progress_lock:
        return {**_progress, "pending": sorted(_pending), "indexed": sorted(indexed)}


def rebuild_in_background() -> None:
    """ใส่เป็น BackgroundTasks — ถ้ามีรอบที่รันอยู่จะรอคิว"""
    with _progress_lock:
        _progress["queued"] += 1
    with _rebuild_lock:
        with _progress_lock:
            _progress["queued"] -= 1
        _run_rebuild()


def _run_rebuild() -> None:
    from app.rag.indexer import rebuild   # โหลดช้า (langchain/pythainlp) — import ตอนใช้
    start = time.time()
    _set_progress(0, "กำลังเริ่มสร้างฐานข้อมูล", running=True, error=None)
    try:
        save_rebuild_status("processing", "กำลัง rebuild index...")
        # rebuild() รายงาน 0–100% → แสดงเป็น 0–95% ส่วน 95–100% คือโหลด retriever ใหม่
        durations = rebuild(documents=load_documents_for_rebuild(),
                            progress=lambda pct, stage: _set_progress(pct * 0.95, stage))
        save_durations(durations or {})

        _set_progress(95, "กำลังโหลดฐานข้อมูลใหม่เข้าระบบค้นหา")
        reload_retriever()

        # เอกสารที่ mark ก่อนเริ่มรอบนี้อยู่ในดัชนีแล้ว — ที่ mark ระหว่างรันรอรอบถัดไป
        with _progress_lock:
            for name, marked_at in list(_pending.items()):
                if marked_at <= start:
                    del _pending[name]

        duration = round(time.time() - start, 2)
        _set_progress(100, "เสร็จสิ้น", running=False)
        save_rebuild_status("success", f"Rebuild สำเร็จใน {duration} วินาที", duration=duration)
    except Exception as e:
        logger.exception("[Rebuild] ผิดพลาด")
        _set_progress(stage="ผิดพลาด", running=False, error=str(e))
        save_rebuild_status("error", f"เกิดข้อผิดพลาด: {e}")
