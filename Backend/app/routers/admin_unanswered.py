"""
TUH Chatbot AI — Admin Router: Unanswered Queries
แยกออกมาจาก Backend/app/routers/admin.py — Endpoint/logic เหมือนเดิมทุกตัวอักษร
ย้าย business logic ไปที่ app/services/unanswered_service.py
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.routers.auth import get_current_user
from app.models.models import User, UnansweredQuery
from app.schemas.schemas import UnansweredResponse, UnansweredUpdate, UnansweredSubmit
from app.services.unanswered_service import record_unanswered_query, analyze_query

router = APIRouter(prefix="/api/admin", tags=["admin"])


class AnalyzeQueryRequest(BaseModel):
    query: str


@router.get("/unanswered", response_model=List[UnansweredResponse])
async def get_unanswered(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(UnansweredQuery).order_by(UnansweredQuery.count.desc()))
    items = result.scalars().all()
    return [UnansweredResponse(
        id=u.id, query=u.query, count=u.count, status=u.status,
        timestamp=u.timestamp.strftime("%Y-%m-%d %H:%M:%S") if u.timestamp else ""
    ) for u in items]


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
    result = await db.execute(select(UnansweredQuery).where(UnansweredQuery.id == query_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="ไม่พบรายการนี้")
    item.status = body.status
    await db.commit()
    await db.refresh(item)
    return UnansweredResponse(
        id=item.id, query=item.query, count=item.count, status=item.status,
        timestamp=item.timestamp.strftime("%Y-%m-%d %H:%M:%S") if item.timestamp else ""
    )


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
