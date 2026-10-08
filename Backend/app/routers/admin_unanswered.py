"""
TUH Chatbot AI — Admin Router: Unanswered Queries
แยกออกมาจาก Backend/app/routers/admin.py — Endpoint/logic เหมือนเดิมทุกตัวอักษร
ย้าย business logic ไปที่ app/services/unanswered_service.py
"""
import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.routers.auth import get_current_user
from app.models.models import User, UnansweredQuery
from app.schemas.schemas import UnansweredResponse, UnansweredUpdate, UnansweredSubmit
from app.services.unanswered_service import record_unanswered_query, analyze_query, apply_unanswered_update
from app.services.taught_keywords_service import invalidate_cache as invalidate_taught_keywords

router = APIRouter(prefix="/api/admin", tags=["admin"])


class AnalyzeQueryRequest(BaseModel):
    query: str


def _fmt(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None


def _to_response(u: UnansweredQuery) -> UnansweredResponse:
    return UnansweredResponse(
        id=u.id, query=u.query, count=u.count, status=u.status,
        timestamp=_fmt(u.timestamp) or "",
        resolution_type=u.resolution_type,
        ignore_reason=u.ignore_reason,
        note=u.note,
        resolved_by=u.resolver.display_name if u.resolver else None,
        resolved_at=_fmt(u.resolved_at),
        search_keywords=json.loads(u.search_keywords or "[]"),
    )


@router.get("/unanswered", response_model=List[UnansweredResponse])
async def get_unanswered(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(UnansweredQuery)
        .options(selectinload(UnansweredQuery.resolver))
        .order_by(UnansweredQuery.count.desc())
    )
    return [_to_response(u) for u in result.scalars().all()]


@router.post("/unanswered/submit", status_code=status.HTTP_201_CREATED)
async def submit_unanswered(body: UnansweredSubmit, db: AsyncSession = Depends(get_db)):
    """User-facing endpoint: บันทึกคำถามที่ระบบตอบไม่ได้"""
    await record_unanswered_query(db, body)
    return {"success": True}


@router.put("/unanswered/{query_id}", response_model=UnansweredResponse)
async def update_unanswered(
    query_id: str,
    body: UnansweredUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(UnansweredQuery)
        .options(selectinload(UnansweredQuery.resolver))
        .where(UnansweredQuery.id == query_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="ไม่พบรายการนี้")
    apply_unanswered_update(item, body, current_user)
    await db.commit()
    invalidate_taught_keywords()
    await db.refresh(item)
    await db.refresh(item, attribute_names=["resolver"])
    return _to_response(item)


@router.delete("/unanswered/{query_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_unanswered(
    query_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(UnansweredQuery).where(UnansweredQuery.id == query_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="ไม่พบรายการนี้")
    await db.delete(item)
    await db.commit()


@router.post("/unanswered/analyze")
async def analyze_unanswered_query(
    payload: AnalyzeQueryRequest,
    current_user: User = Depends(get_current_user)
):
    """
    ใช้ AI วิเคราะห์คำถามที่ตอบไม่ได้ ก่อนแอดมินเขียนคำตอบ FAQ ด้วยมือ
    คืนค่า: is_valid_query (เป็นคำถามจริงหรือขยะ/ทักทาย) + suggested_keywords (คำค้นหาแนะนำ)
    ถ้าไม่มี LLM API key หรือเรียกไม่สำเร็จ ให้ fallback เป็นค่าที่ไม่ทำให้ UI พัง แทนการโยน error
    """
    return await analyze_query(payload.query)
