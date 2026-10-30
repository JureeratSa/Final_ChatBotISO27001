"""
TUH Chatbot AI — Admin Router: Stats
แยกออกมาจาก Backend/app/routers/admin.py
เป็น read-only aggregation ข้าม 4 model (ChatHistory, Feedback, UnansweredQuery, Document)
ไม่แยก service layer เพราะไม่มี business rule ที่ซับซ้อนพอจะซ่อน แค่ query นับจำนวนตรงๆ
"""
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.routers.auth import get_current_user
from app.models.models import User, ChatHistory, Feedback, UnansweredQuery, Document
from app.schemas.schemas import StatsResponse
from app.services.department_scope import department_column_filter, history_scope_filter, scope_department
from app.utils.timeutil import thai_day_range_utc

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    department: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # แอดมินแผนกเห็นตัวเลขเฉพาะของแผนกตัวเอง (กรองชุดเดียวกับหน้าประวัติ/เอกสาร/คำถามที่ตอบไม่ได้)
    dept = scope_department(current_user, department)
    history_scope = await history_scope_filter(db, current_user, department)
    doc_scope = department_column_filter(Document.department, dept)
    unans_scope = department_column_filter(UnansweredQuery.department, dept)

    def _history(q):
        return q if history_scope is None else q.where(history_scope)

    def _feedback(q):
        if history_scope is None:
            return q
        return q.join(ChatHistory, Feedback.history_id == ChatHistory.id).where(history_scope)

    def _where(q, clause):
        return q if clause is None else q.where(clause)

    total_queries = (await db.execute(_history(select(func.count(ChatHistory.id))))).scalar() or 0
    total_likes = (await db.execute(_feedback(select(func.count(Feedback.id)).where(Feedback.rating == "like")))).scalar() or 0
    total_dislikes = (await db.execute(_feedback(select(func.count(Feedback.id)).where(Feedback.rating == "dislike")))).scalar() or 0
    total_unanswered = (await db.execute(_where(select(func.count(UnansweredQuery.id)), unans_scope))).scalar() or 0
    total_documents = (await db.execute(_where(select(func.count(Document.id)), doc_scope))).scalar() or 0
    active_documents = (await db.execute(
        _where(select(func.count(Document.id)).where(Document.status == "Active"), doc_scope)
    )).scalar() or 0

    # "วันนี้" ตามเวลาไทย — timestamp ในฐานข้อมูลเป็น UTC เดิมนับตามวันของ UTC ช่วงตี 0–7 ของไทยจึงนับผิดวัน
    day_start, day_end = thai_day_range_utc()
    queries_today = (await db.execute(_history(
        select(func.count(ChatHistory.id)).where(
            ChatHistory.timestamp >= day_start, ChatHistory.timestamp < day_end
        )
    ))).scalar() or 0

    avg_rt_result = await db.execute(_history(select(func.avg(ChatHistory.response_time))))
    avg_rt = avg_rt_result.scalar() or 0.0

    return StatsResponse(
        total_queries=total_queries,
        total_likes=total_likes,
        total_dislikes=total_dislikes,
        total_unanswered=total_unanswered,
        total_documents=total_documents,
        active_documents=active_documents,
        queries_today=queries_today,
        avg_response_time=round(float(avg_rt), 3)
    )
