"""
Endpoint สาธารณะ (ไม่ต้องล็อกอิน) ที่ UserWeb เรียก

  GET /api/health                       ใช้ตรวจว่าเซิร์ฟเวอร์ทำงาน (healthcheck ของ Docker)
  GET /api/forms/download/{filename}    ดาวน์โหลดแบบฟอร์ม
  GET /api/documents/serve/{filename}   เปิด PDF (?hl=chunk_id,... = ไฮไลท์ส่วนที่ใช้ตอบ)
  GET /api/announcements/active         ประกาศที่อยู่ในช่วงเวลาแสดงผล
"""
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import safe_path
from app.models.models import Announcement, Document
from app.rag.highlight import find_chunks, highlight_pdf, parse_chunk_ids
from app.utils.timeutil import THAI_TZ

logger = logging.getLogger(__name__)
router = APIRouter(tags=["public"])


@router.get("/api/health")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}


@router.get("/api/forms/download/{filename}")
async def download_form_file(filename: str):
    try:
        form_path = safe_path(Path(settings.UPLOADS_DIR) / "forms", filename)
    except Exception:
        raise HTTPException(status_code=400, detail="ชื่อไฟล์ไม่ถูกต้อง")
    if not form_path.exists():
        raise HTTPException(status_code=404, detail="ไม่พบไฟล์แบบฟอร์มนี้")
    # ไฟล์เก็บเป็น "<timestamp>_<ชื่อจริง>" — ตอนดาวน์โหลดใช้ชื่อจริง
    return FileResponse(str(form_path), filename=filename.split("_", 1)[-1], media_type="application/pdf")


async def active_document_path(db: AsyncSession, filename: str) -> Path:
    """คนทั่วไปเปิดได้เฉพาะเอกสารที่สถานะ Active (บอทใช้ตอบอยู่) — ร่าง/ปิดใช้งาน ตอบ 404 เหมือนไม่มีไฟล์"""
    file_path = safe_path(Path(settings.UPLOADS_DIR), filename)
    status = (await db.execute(
        select(Document.status).where(Document.filename == file_path.name)
    )).scalar_one_or_none()
    if status != "Active" or not file_path.is_file():
        raise HTTPException(status_code=404, detail="ไม่พบไฟล์ PDF นี้")
    return file_path


@router.get("/api/documents/serve/{filename}")
async def serve_document(filename: str, hl: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    file_path = await active_document_path(db, filename)
    if hl:
        chunks = find_chunks(file_path.name, parse_chunk_ids(hl))
        if chunks:
            try:
                data = await asyncio.to_thread(highlight_pdf, str(file_path), chunks)
                return Response(content=data, media_type="application/pdf", headers={"Cache-Control": "no-store"})
            except Exception as e:
                # ไฮไลท์ไม่สำเร็จ ยังเปิดเอกสารได้ตามปกติ
                logger.warning("[PDF Highlight] %s: %s", filename, e)
    return FileResponse(str(file_path), media_type="application/pdf")


def is_announcement_active(start_date: Optional[str], end_date: Optional[str], now: datetime) -> bool:
    """start/end เก็บเป็นสตริง "YYYY-MM-DD" หรือ "YYYY-MM-DDTHH:MM" (เวลาไทยตามที่แอดมินกรอก)
    รูปแบบ ISO เรียงตามตัวอักษรตรงกับลำดับเวลา จึงเทียบสตริงตรงๆ ได้"""
    start, end = start_date or "", end_date or ""
    if len(start) == 10:
        start += "T00:00"
    if len(end) == 10:
        end += "T23:59"
    if len(start) == 16 and len(end) == 16:
        return start <= now.strftime("%Y-%m-%dT%H:%M") <= end
    today = now.strftime("%Y-%m-%d")
    return start <= today <= end


@router.get("/api/announcements/active")
async def active_announcements(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(Announcement).order_by(Announcement.pinned.desc(), Announcement.created_at.desc())
    )).scalars().all()
    now = datetime.now(THAI_TZ)   # เซิร์ฟเวอร์ (Docker) ใช้เวลา UTC แต่แอดมินกรอกช่วงเวลาเป็นเวลาไทย
    return [
        {"id": a.id, "title": a.title, "content": a.content,
         "start_date": a.start_date, "end_date": a.end_date, "pinned": a.pinned}
        for a in rows if is_announcement_active(a.start_date, a.end_date, now)
    ]
