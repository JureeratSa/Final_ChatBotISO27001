"""
Endpoint ของหน้าแชท (UserWeb)

  POST /api/search          ถามคำถาม → คำตอบ + เอกสารอ้างอิง + ลิงก์แบบฟอร์ม
  GET  /api/chat/settings   ข้อความต้อนรับ + ปุ่มคำถามด่วน
"""
import json

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rate_limit import rate_limit_dependency
from app.models.models import SystemSettings
from app.schemas.schemas import ChatRequest
from app.services.chat_service import answer_question

router = APIRouter(tags=["chat"])


@router.post("/api/search", dependencies=[Depends(rate_limit_dependency)])
async def search(body: ChatRequest, background: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    query = body.query.strip()
    if not query:
        return {"answer": "กรุณาพิมพ์คำถาม", "results": []}
    return await answer_question(db, query, body.history, background)


@router.get("/api/chat/settings")
async def chat_settings(db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(SystemSettings).where(SystemSettings.id == "config"))).scalar_one_or_none()
    if not row:
        return {"welcome_message": None, "predefined_faqs": [], "chat_greeting": None}
    return {
        "welcome_message": row.welcome_message,
        "chat_greeting": row.chat_greeting,
        "predefined_faqs": json.loads(row.predefined_faqs or "[]"),
    }
