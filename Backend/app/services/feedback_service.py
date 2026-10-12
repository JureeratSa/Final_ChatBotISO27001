"""
TUH Chatbot AI — Feedback Service
แยกจาก app/routers/admin_feedback.py — เก็บ business rule ของการ upsert feedback ไว้ที่เดียว
(เดิมอยู่ใน Backend/app/routers/admin.py)
"""
import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Feedback
from app.schemas.schemas import FeedbackSubmit


async def upsert_feedback(db: AsyncSession, body: FeedbackSubmit) -> None:
    """ถ้ามี Feedback ที่ query+answer ตรงกันเป๊ะอยู่แล้ว อัปเดตแถวเดิม (กันข้อมูลซ้ำตอนผู้ใช้
    เปลี่ยนใจกด like/dislike ซ้ำสำหรับคำตอบเดิม) ไม่งั้นสร้างแถวใหม่"""
    if body.query and body.answer:
        result = await db.execute(
            select(Feedback).where(
                Feedback.query == body.query,
                Feedback.answer == body.answer
            )
        )
        existing = result.scalars().first()
        if existing:
            existing.rating = body.rating
            if body.stars is not None:
                existing.stars = body.stars
            if body.comment is not None:
                existing.comment = body.comment
            await db.commit()
            return

    entry = Feedback(
        id=f"fb-{int(time.time() * 1000)}",
        rating=body.rating,
        stars=body.stars,
        comment=body.comment,
        query=body.query,
        answer=body.answer,
        history_id=body.history_id
    )
    db.add(entry)
    await db.commit()
