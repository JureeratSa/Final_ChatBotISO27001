"""
คำถามที่บอทตอบไม่ได้ (หน้า "คำถามที่บอทตอบไม่ได้" ของ AdminWeb) — /api/admin/unanswered*

แอดมินแก้ได้ 3 วิธี: สอนคำค้นภาษาเอกสาร / สอนคำตอบ (FAQ) / ไม่แก้ (Ignored พร้อมเหตุผล)
แอดมินแผนกเห็นเฉพาะคำถามที่ระบบเดาว่าเป็นของแผนกตัวเอง — ที่เดาไม่ได้เห็นแค่ SuperAdmin
"""
import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import UnansweredQuery, User
from app.schemas.schemas import UnansweredResponse, UnansweredUpdate
from app.services.audit_service import add_audit_detail
from app.services.department_scope import check_department, department_column_filter, require_super_admin, scope_department
from app.services.taught_keywords_service import invalidate_cache as invalidate_taught_keywords
from app.services.unanswered_service import analyze_query, apply_unanswered_update
from app.utils.timeutil import thai_str

router = APIRouter(prefix="/api/admin", tags=["unanswered"])


class AnalyzeQueryRequest(BaseModel):
    query: str


class UnansweredDepartmentRequest(BaseModel):
    department: Optional[str] = None      # None/"" = ยังไม่ระบุแผนก


def _to_response(u: UnansweredQuery) -> UnansweredResponse:
    return UnansweredResponse(
        id=u.id, query=u.query, count=u.count, status=u.status,
        timestamp=thai_str(u.timestamp) or "",
        resolution_type=u.resolution_type,
        ignore_reason=u.ignore_reason,
        note=u.note,
        resolved_by=u.resolver.display_name if u.resolver else None,
        resolved_at=thai_str(u.resolved_at),
        search_keywords=json.loads(u.search_keywords or "[]"),
        department=u.department,
    )


async def _get_item(db: AsyncSession, query_id: str) -> UnansweredQuery:
    item = (await db.execute(
        select(UnansweredQuery).options(selectinload(UnansweredQuery.resolver)).where(UnansweredQuery.id == query_id)
    )).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="ไม่พบรายการนี้")
    return item


async def _reload(db: AsyncSession, item: UnansweredQuery) -> UnansweredQuery:
    await db.refresh(item)
    await db.refresh(item, attribute_names=["resolver"])   # ชื่อคนปิดรายการ (relationship)
    return item


@router.get("/unanswered", response_model=List[UnansweredResponse])
async def list_unanswered(department: Optional[str] = None,
                          current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    query = (select(UnansweredQuery).options(selectinload(UnansweredQuery.resolver))
             .order_by(UnansweredQuery.count.desc()))
    scope = department_column_filter(UnansweredQuery.department, scope_department(current_user, department))
    if scope is not None:
        query = query.where(scope)
    return [_to_response(u) for u in (await db.execute(query)).scalars().all()]


@router.put("/unanswered/{query_id}", response_model=UnansweredResponse)
async def update_unanswered(query_id: str, body: UnansweredUpdate,
                            current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """เปลี่ยนสถานะ (Pending / Resolved / Ignored) พร้อมวิธีที่ใช้แก้"""
    item = await _get_item(db, query_id)
    add_audit_detail(question=(item.query or "")[:200], department=item.department)
    check_department(item.department, current_user, "คุณไม่มีสิทธิ์จัดการคำถามของแผนกอื่น")
    add_audit_detail(from_status=item.status, to_status=body.status,
                     resolution_type=body.resolution_type, ignore_reason=body.ignore_reason)
    apply_unanswered_update(item, body, current_user)
    await db.commit()
    invalidate_taught_keywords()          # คำค้นที่สอนมีผลกับการค้นทันที
    return _to_response(await _reload(db, item))


@router.put("/unanswered/{query_id}/department", response_model=UnansweredResponse)
async def update_unanswered_department(query_id: str, body: UnansweredDepartmentRequest,
                                       current_user: User = Depends(get_current_user),
                                       db: AsyncSession = Depends(get_db)):
    """ส่งคำถามต่อให้แผนกอื่น (ระบบเดาแผนกผิดหรือเดาไม่ได้) — SuperAdmin เท่านั้น"""
    require_super_admin(current_user, "เฉพาะ SuperAdmin เท่านั้นที่ส่งคำถามต่อให้แผนกอื่นได้")
    item = await _get_item(db, query_id)
    new_department = (body.department or "").strip() or None
    add_audit_detail(question=(item.query or "")[:200], from_department=item.department or "ยังไม่ระบุ",
                     to_department=new_department or "ยังไม่ระบุ")
    item.department = new_department
    await db.commit()
    return _to_response(await _reload(db, item))


@router.post("/unanswered/analyze")
async def analyze_unanswered_query(payload: AnalyzeQueryRequest, current_user: User = Depends(get_current_user)):
    """ให้ AI ดูว่าเป็นคำถามจริงไหม + เสนอคำค้นภาษาเอกสาร (ก่อนแอดมินสอนคำค้น)"""
    return await analyze_query(payload.query)
