"""
ความพึงพอใจของผู้ใช้ (กดถูกใจ/ไม่ถูกใจ, แบบประเมินดาว)

  POST /api/admin/feedback/submit   UserWeb ส่ง (ไม่ต้องล็อกอิน)
  GET  /api/admin/feedback          หน้า "ความพึงพอใจ" ของ AdminWeb
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.rate_limit import rate_limit_dependency
from app.models.models import ChatHistory, Feedback, User
from app.schemas.schemas import FeedbackResponse, FeedbackSubmit
from app.services.department_scope import history_scope_filter
from app.services.feedback_service import upsert_feedback
from app.utils.timeutil import thai_str

router = APIRouter(prefix="/api/admin", tags=["feedback"])


@router.post("/feedback/submit", status_code=status.HTTP_201_CREATED, dependencies=[Depends(rate_limit_dependency)])
async def submit_feedback(body: FeedbackSubmit, db: AsyncSession = Depends(get_db)):
    await upsert_feedback(db, body)
    return {"success": True}


@router.get("/feedback", response_model=List[FeedbackResponse])
async def list_feedback(department: Optional[str] = None,
                        current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """แอดมินแผนกเห็นเฉพาะ feedback ของคำตอบในแผนกตัวเอง
    (feedback ที่ไม่ผูกกับคำตอบใด เช่นแบบประเมินภาพรวม เห็นแค่ SuperAdmin)"""
    query = select(Feedback)
    scope = await history_scope_filter(db, current_user, department)
    if scope is not None:
        query = query.join(ChatHistory, Feedback.history_id == ChatHistory.id).where(scope)
    items = (await db.execute(query.order_by(Feedback.timestamp.desc()))).scalars().all()
    return [FeedbackResponse(id=f.id, rating=f.rating, stars=f.stars, comment=f.comment, query=f.query,
                             answer=f.answer, timestamp=thai_str(f.timestamp) or "", history_id=f.history_id)
            for f in items]
