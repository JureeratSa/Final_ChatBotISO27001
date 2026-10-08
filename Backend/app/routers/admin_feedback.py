"""
TUH Chatbot AI — Admin Router: Feedback
แยกออกมาจาก Backend/app/routers/admin.py (เดิมรวมทุก domain ไว้ไฟล์เดียว 1549 บรรทัด)
แยก business logic ไปที่
app/services/feedback_service.py เท่านั้น ไม่ได้เปลี่ยนพฤติกรรม
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.routers.auth import get_current_user
from app.models.models import User, Feedback
from app.schemas.schemas import FeedbackResponse, FeedbackSubmit
from app.services.feedback_service import upsert_feedback

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/feedback", response_model=List[FeedbackResponse])
async def get_feedback(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Feedback).order_by(Feedback.timestamp.desc()))
    items = result.scalars().all()
    return [FeedbackResponse(
        id=f.id, rating=f.rating, stars=f.stars, comment=f.comment, query=f.query, answer=f.answer,
        timestamp=f.timestamp.strftime("%Y-%m-%d %H:%M:%S") if f.timestamp else "",
        history_id=f.history_id
    ) for f in items]


@router.post("/feedback/submit", status_code=status.HTTP_201_CREATED)
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
    result = await db.execute(select(Feedback).where(Feedback.id == feedback_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="ไม่พบ Feedback นี้")
    await db.delete(item)
    await db.commit()
