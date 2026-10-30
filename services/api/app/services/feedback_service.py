"""บันทึกความพึงพอใจ — กดซ้ำกับคำตอบเดิมให้อัปเดตแถวเดิม ไม่สร้างแถวซ้ำ"""
import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Feedback
from app.schemas.schemas import FeedbackSubmit


async def upsert_feedback(db: AsyncSession, body: FeedbackSubmit) -> None:
    """มี feedback ที่ query+answer ตรงกันอยู่แล้ว (ผู้ใช้เปลี่ยนใจกดใหม่) → อัปเดตแถวเดิม"""
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
