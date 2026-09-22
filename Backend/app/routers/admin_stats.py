"""
TUH Chatbot AI — Admin Router: Stats
แยกออกมาจาก Backend/app/routers/admin.py — Endpoint/logic เหมือนเดิมทุกตัวอักษร
เป็น read-only aggregation ข้าม 4 model (ChatHistory, Feedback, UnansweredQuery, Document)
ไม่แยก service layer เพราะไม่มี business rule ที่ซับซ้อนพอจะซ่อน แค่ query นับจำนวนตรงๆ
"""
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, Date

from app.core.database import get_db
from app.routers.auth import get_current_user
from app.models.models import User, ChatHistory, Feedback, UnansweredQuery, Document
from app.schemas.schemas import StatsResponse

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    total_queries = (await db.execute(select(func.count(ChatHistory.id)))).scalar() or 0
    total_likes = (await db.execute(select(func.count(Feedback.id)).where(Feedback.rating == "like"))).scalar() or 0
    total_dislikes = (await db.execute(select(func.count(Feedback.id)).where(Feedback.rating == "dislike"))).scalar() or 0
    total_unanswered = (await db.execute(select(func.count(UnansweredQuery.id)))).scalar() or 0
    total_documents = (await db.execute(select(func.count(Document.id)))).scalar() or 0
    active_documents = (await db.execute(select(func.count(Document.id)).where(Document.status == "Active"))).scalar() or 0

    today = date.today()
    queries_today = (await db.execute(
        select(func.count(ChatHistory.id)).where(
            cast(ChatHistory.timestamp, Date) == today
        )
    )).scalar() or 0

    avg_rt_result = await db.execute(select(func.avg(ChatHistory.response_time)))
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
