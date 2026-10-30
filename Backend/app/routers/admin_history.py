"""
TUH Chatbot AI — Admin Router: History
แยกออกมาจาก Backend/app/routers/admin.py
history_row_to_response() ย้ายไปที่ app/services/history_service.py
"""
import json
import logging
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.config import settings
from app.routers.auth import get_current_user
from app.models.models import User, ChatHistory
from app.schemas.schemas import HistoryResponse
from app.services.history_service import history_row_to_response
from app.services.department_scope import department_filenames, history_scope_filter, scope_department

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"])

HISTORY_MAX_LIMIT = 5000


@router.get("/history", response_model=List[HistoryResponse])
async def get_history(
    limit: int = 100,
    department: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """แอดมินแผนกเห็นเฉพาะคำตอบที่อิงเอกสารของแผนกตัวเอง (ดู department_scope.history_department_filter)
    limit สูงสุด HISTORY_MAX_LIMIT (AdminWeb ขอ 5000) — เดิมไม่มีเพดาน ขอทั้งตารางในครั้งเดียวได้"""
    limit = max(1, min(limit, HISTORY_MAX_LIMIT))
    query = select(ChatHistory).order_by(ChatHistory.timestamp.desc()).limit(limit)
    scope = await history_scope_filter(db, current_user, department)
    if scope is not None:
        query = query.where(scope)
    result = await db.execute(query)
    items = result.scalars().all()
    return [history_row_to_response(h) for h in items]


@router.get("/history/chunks-map")
async def get_history_chunks_map(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """ดึงแผนผัง Chunk ID -> {source, page, content} เพื่อให้หน้าบ้านคลิกลิงก์ไปยัง PDF หน้าคู่มือของ Chunk ได้
    แอดมินแผนกได้เฉพาะ chunk ของเอกสารแผนกตัวเอง — เดิมได้เนื้อหาทุกเอกสารทุกแผนก (security audit L11)"""
    chunks_path = Path(settings.ADMIN_DIR).parent / "sample_chunks.json"
    if not chunks_path.exists():
        return {}
    dept = scope_department(current_user)
    allowed = await department_filenames(db, dept) if dept is not None else None
    try:
        with open(chunks_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            str(item["chunk_id"]): {
                "source": item["metadata"].get("source", ""),
                "page": item["metadata"].get("page", 1),
                "content": item.get("content", "")
            }
            for item in data
            if "chunk_id" in item and "metadata" in item
            and (allowed is None or item["metadata"].get("source") in allowed)
        }
    except Exception as e:
        logger.error("[Chunks Map Error] %s", e)
        return {}
