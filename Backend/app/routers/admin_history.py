"""
TUH Chatbot AI — Admin Router: History
แยกออกมาจาก Backend/app/routers/admin.py — Endpoint/logic เหมือนเดิมทุกตัวอักษร
history_row_to_response() ย้ายไปที่ app/services/history_service.py
"""
import json
import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.config import settings
from app.routers.auth import get_current_user
from app.models.models import User, ChatHistory
from app.schemas.schemas import HistoryResponse
from app.services.history_service import history_row_to_response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/history", response_model=List[HistoryResponse])
async def get_history(
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(ChatHistory).order_by(ChatHistory.timestamp.desc()).limit(limit)
    )
    items = result.scalars().all()
    return [history_row_to_response(h) for h in items]


@router.get("/history/chunks-map")
async def get_history_chunks_map(current_user: User = Depends(get_current_user)):
    """ดึงแผนผัง Chunk ID -> {source, page, content} เพื่อให้หน้าบ้านคลิกลิงก์ไปยัง PDF หน้าคู่มือของ Chunk ได้"""
    chunks_path = Path(settings.ADMIN_DIR).parent / "sample_chunks.json"
    if not chunks_path.exists():
        return {}
    try:
        with open(chunks_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            str(item["chunk_id"]): {
                "source": item["metadata"].get("source", ""),
                "page": item["metadata"].get("page", 1),
                "content": item.get("content", "")
            }
            for item in data if "chunk_id" in item and "metadata" in item
        }
    except Exception as e:
        logger.error("[Chunks Map Error] %s", e)
        return {}
