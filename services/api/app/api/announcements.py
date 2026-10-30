"""
จัดการประกาศ (หน้า "ประกาศ" ของ AdminWeb) — /api/admin/announcements*
ประกาศเป็นของส่วนกลาง แก้ไขได้เฉพาะ SuperAdmin; ผู้ใช้แชทบอทดูผ่าน /api/announcements/active
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import Announcement, User
from app.schemas.schemas import AnnouncementResponse
from app.services.audit_service import add_audit_detail
from app.services.department_scope import require_super_admin
from app.utils.sanitize import sanitize_html

router = APIRouter(prefix="/api/admin", tags=["announcements"])

SUPER_ONLY = "ประกาศเป็นส่วนกลางของระบบ เฉพาะ SuperAdmin เท่านั้นที่จัดการได้"


class AnnouncementFields(BaseModel):
    title: str
    content: Optional[str] = None          # HTML จาก CKEditor — sanitize ก่อนเก็บเสมอ (กัน XSS)
    start_date: Optional[str] = None       # "YYYY-MM-DD" หรือ "YYYY-MM-DDTHH:MM"
    end_date: Optional[str] = None
    category: Optional[str] = None
    pinned: bool = False


class AnnouncementUpdateRequest(AnnouncementFields):
    id: int


class AnnouncementIdRequest(BaseModel):
    id: int


async def _get_announcement(db: AsyncSession, ann_id: int) -> Announcement:
    ann = (await db.execute(select(Announcement).where(Announcement.id == ann_id))).scalar_one_or_none()
    if not ann:
        raise HTTPException(status_code=404, detail="ไม่พบประกาศนี้")
    add_audit_detail(announcement_id=ann.id, announcement=ann.title)
    return ann


@router.get("/announcements", response_model=List[AnnouncementResponse])
async def list_announcements(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """ทุกประกาศ รวมที่หมดอายุแล้ว/ยังไม่ถึงวัน"""
    return (await db.execute(
        select(Announcement).order_by(Announcement.pinned.desc(), Announcement.created_at.desc())
    )).scalars().all()


@router.post("/announcements/create", response_model=AnnouncementResponse)
async def create_announcement(payload: AnnouncementFields,
                              current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    require_super_admin(current_user, SUPER_ONLY)
    add_audit_detail(announcement=payload.title)
    ann = Announcement(**payload.model_dump(), created_by=current_user.display_name or current_user.username,
                       created_by_id=current_user.id)
    ann.content = sanitize_html(payload.content)
    db.add(ann)
    await db.commit()
    await db.refresh(ann)
    return ann


@router.post("/announcements/update", response_model=AnnouncementResponse)
async def update_announcement(payload: AnnouncementUpdateRequest,
                              current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    require_super_admin(current_user, SUPER_ONLY)
    ann = await _get_announcement(db, payload.id)
    ann.title = payload.title
    ann.content = sanitize_html(payload.content)
    ann.start_date = payload.start_date
    ann.end_date = payload.end_date
    ann.pinned = payload.pinned
    if payload.category is not None:
        ann.category = payload.category
    await db.commit()
    await db.refresh(ann)
    return ann


@router.post("/announcements/delete")
async def delete_announcement(payload: AnnouncementIdRequest,
                              current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    require_super_admin(current_user, SUPER_ONLY)
    ann = await _get_announcement(db, payload.id)
    await db.delete(ann)
    await db.commit()
    return {"success": True}
