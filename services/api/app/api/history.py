"""
ประวัติการสนทนา (หน้า "ประวัติ" ของ AdminWeb) — /api/admin/history*
แอดมินแผนกเห็นเฉพาะคำตอบที่อิงเอกสารของแผนกตัวเอง
"""
import json
import logging
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.models import ChatHistory, User
from app.schemas.schemas import HistoryResponse
from app.services.department_scope import department_filenames, history_scope_filter, scope_department
from app.services.history_service import history_row_to_response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["history"])

HISTORY_MAX_LIMIT = 5000


@router.get("/history", response_model=List[HistoryResponse])
async def get_history(
    limit: int = 100,
    department: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """ใหม่ไปเก่า สูงสุด HISTORY_MAX_LIMIT แถว (AdminWeb ขอ 5000)"""
    limit = max(1, min(limit, HISTORY_MAX_LIMIT))
    query = select(ChatHistory).order_by(ChatHistory.timestamp.desc()).limit(limit)
    scope = await history_scope_filter(db, current_user, department)
    if scope is not None:
        query = query.where(scope)
    return [history_row_to_response(h) for h in (await db.execute(query)).scalars().all()]


@router.get("/history/chunks-map")
async def get_history_chunks_map(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """chunk_id → {source, page, content} ให้หน้าประวัติแสดงว่าคำตอบอิง chunk ไหน (เฉพาะเอกสารในแผนกตัวเอง)"""
    chunks_path = Path(settings.CHUNKS_FILE)
    if not chunks_path.exists():
        return {}
    dept = scope_department(current_user)
    allowed = await department_filenames(db, dept) if dept is not None else None
    try:
        data = json.loads(chunks_path.read_text(encoding="utf-8"))
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
