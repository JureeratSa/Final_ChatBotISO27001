"""
TUH Chatbot AI — Admin Router: Announcements
แยกออกมาจาก Backend/app/routers/admin.py
ไม่แยก service layer (ตามแผน) — sanitize_html import คงอยู่ตรงนี้เหมือนเดิม
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.utils.sanitize import sanitize_html
from app.routers.auth import get_current_user
from app.models.models import User, Announcement
from app.schemas.schemas import AnnouncementResponse, AnnouncementCreate, AnnouncementUpdate
from app.services.department_scope import require_super_admin
from app.services.audit_service import add_audit_detail

_SUPER_ONLY = "ประกาศเป็นส่วนกลางของระบบ เฉพาะ SuperAdmin เท่านั้นที่จัดการได้"

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/announcements", response_model=list[AnnouncementResponse])
async def get_announcements(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """ประกาศทั้งหมดสำหรับหน้าจัดการของแอดมิน (รวมที่หมดอายุ/ยังไม่ถึงวัน) — ต้องล็อกอิน
    เดิมเปิดให้คนทั่วไปเรียกได้ (security audit L5) — ผู้ใช้แชทบอทใช้ /api/announcements/active ที่คืนเฉพาะที่กำลังประกาศ"""
    result = await db.execute(
        select(Announcement).order_by(Announcement.pinned.desc(), Announcement.created_at.desc())
    )
    return result.scalars().all()


@router.post("/announcements", response_model=AnnouncementResponse, status_code=status.HTTP_201_CREATED)
async def create_announcement(
    body: AnnouncementCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    require_super_admin(current_user, _SUPER_ONLY)
    data = body.model_dump()
    data["content"] = sanitize_html(data.get("content"))  # กัน Stored XSS จาก CKEditor ก่อนเก็บ DB
    ann = Announcement(**data)
    add_audit_detail(announcement=ann.title)
    ann.created_by = current_user.display_name or current_user.username
    ann.created_by_id = current_user.id
    db.add(ann)
    await db.commit()
    await db.refresh(ann)
    return ann


@router.put("/announcements/{ann_id}", response_model=AnnouncementResponse)
async def update_announcement(
    ann_id: int,
    body: AnnouncementUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    require_super_admin(current_user, _SUPER_ONLY)
    result = await db.execute(select(Announcement).where(Announcement.id == ann_id))
    ann = result.scalar_one_or_none()
    if not ann:
        raise HTTPException(status_code=404, detail="ไม่พบประกาศนี้")
    add_audit_detail(announcement_id=ann.id, announcement=ann.title)
    data = body.model_dump(exclude_none=True)
    if "content" in data:
        data["content"] = sanitize_html(data["content"])
    for field, value in data.items():
        setattr(ann, field, value)
    await db.commit()
    await db.refresh(ann)
    return ann


@router.delete("/announcements/{ann_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_announcement(
    ann_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    require_super_admin(current_user, _SUPER_ONLY)
    result = await db.execute(select(Announcement).where(Announcement.id == ann_id))
    ann = result.scalar_one_or_none()
    if not ann:
        raise HTTPException(status_code=404, detail="ไม่พบประกาศนี้")
    add_audit_detail(announcement_id=ann.id, announcement=ann.title)
    await db.delete(ann)
    await db.commit()


class LegacyAnnouncementCreateRequest(BaseModel):
    title: str
    content: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    category: Optional[str] = None
    pinned: bool = False


class LegacyAnnouncementUpdateRequest(BaseModel):
    id: int
    title: str
    content: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    category: Optional[str] = None
    pinned: bool = False


class LegacyAnnouncementDeleteRequest(BaseModel):
    id: int


@router.post("/announcements/create")
async def create_announcement_compatibility(
    payload: LegacyAnnouncementCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    require_super_admin(current_user, _SUPER_ONLY)
    add_audit_detail(announcement=payload.title)
    ann = Announcement(
        title=payload.title,
        content=sanitize_html(payload.content),
        start_date=payload.start_date,
        end_date=payload.end_date,
        category=payload.category,
        pinned=payload.pinned,
        created_by=current_user.display_name or current_user.username,
        created_by_id=current_user.id
    )
    db.add(ann)
    await db.commit()
    await db.refresh(ann)
    return ann


@router.post("/announcements/update")
async def update_announcement_compatibility(
    payload: LegacyAnnouncementUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    require_super_admin(current_user, _SUPER_ONLY)
    result = await db.execute(select(Announcement).where(Announcement.id == payload.id))
    ann = result.scalar_one_or_none()
    if not ann:
        raise HTTPException(status_code=404, detail="ไม่พบประกาศนี้")
    add_audit_detail(announcement_id=ann.id, announcement=ann.title)

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
async def delete_announcement_compatibility(
    payload: LegacyAnnouncementDeleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    require_super_admin(current_user, _SUPER_ONLY)
    result = await db.execute(select(Announcement).where(Announcement.id == payload.id))
    ann = result.scalar_one_or_none()
    if not ann:
        raise HTTPException(status_code=404, detail="ไม่พบประกาศนี้")
    add_audit_detail(announcement_id=ann.id, announcement=ann.title)

    await db.delete(ann)
    await db.commit()
    return {"success": True}
