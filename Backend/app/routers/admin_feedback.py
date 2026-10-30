"""
TUH Chatbot AI — Admin Router: Feedback
แยกออกมาจาก Backend/app/routers/admin.py (เดิมรวมทุก domain ไว้ไฟล์เดียว 1549 บรรทัด)
แยก business logic ไปที่
app/services/feedback_service.py เท่านั้น ไม่ได้เปลี่ยนพฤติกรรม
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.rate_limit import rate_limit_dependency
from app.routers.auth import get_current_user
from app.models.models import User, Feedback, ChatHistory
from app.schemas.schemas import FeedbackResponse, FeedbackSubmit
from app.services.feedback_service import upsert_feedback
from app.services.department_scope import history_scope_filter
from app.services.audit_service import add_audit_detail
from app.utils.timeutil import thai_str  # เวลาในฐานข้อมูลเป็น UTC — แสดงเป็นเวลาไทย


async def _scoped_feedback_query(db: AsyncSession, user: User, department: Optional[str] = None):
    """ความพึงพอใจผูกกับประวัติคำตอบ (history_id) — แอดมินแผนกเห็นเฉพาะของคำตอบที่อยู่ในแผนกตัวเอง
    (feedback ที่ไม่ผูกกับประวัติใด เช่นแบบประเมินภาพรวม เห็นแค่ SuperAdmin)"""
    query = select(Feedback)
    scope = await history_scope_filter(db, user, department)
    if scope is not None:
        query = query.join(ChatHistory, Feedback.history_id == ChatHistory.id).where(scope)
    return query

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/feedback", response_model=List[FeedbackResponse])
async def get_feedback(
    department: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = await _scoped_feedback_query(db, current_user, department)
    result = await db.execute(query.order_by(Feedback.timestamp.desc()))
    items = result.scalars().all()
    return [FeedbackResponse(
        id=f.id, rating=f.rating, stars=f.stars, comment=f.comment, query=f.query, answer=f.answer,
        timestamp=thai_str(f.timestamp) or "",
        history_id=f.history_id
    ) for f in items]


@router.post("/feedback/submit", status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(rate_limit_dependency)])
async def submit_feedback(body: FeedbackSubmit, db: AsyncSession = Depends(get_db)):
    """User submits feedback (ไม่ต้องการ auth)"""
    await upsert_feedback(db, body)
    return {"success": True}


@router.delete("/feedback/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feedback(
    feedback_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = await _scoped_feedback_query(db, current_user)
    result = await db.execute(query.where(Feedback.id == feedback_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="ไม่พบ Feedback นี้")
    add_audit_detail(feedback_rating=item.rating, question=(item.query or "")[:200] or None)
    await db.delete(item)
    await db.commit()
