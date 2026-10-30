"""
TUH Chatbot AI — History Service
แยกจาก app/routers/admin_history.py (เดิมอยู่ใน Backend/app/routers/admin.py)
"""
import json

from app.models.models import ChatHistory
from app.schemas.schemas import HistoryResponse
from app.utils.timeutil import thai_str  # เวลาในฐานข้อมูลเป็น UTC — แสดงเป็นเวลาไทย


def history_row_to_response(h: ChatHistory) -> HistoryResponse:
    return HistoryResponse(
        id=h.id,
        query=h.query,
        answer=h.answer,
        response_time=h.response_time,
        chunk_ids=[int(x) for x in (h.chunk_ids or "").split(",") if x.strip().isdigit()],
        api_model=h.api_model,
        referenced_docs=json.loads(h.referenced_docs or "[]"),
        cited_docs=json.loads(h.cited_docs) if h.cited_docs is not None else None,
        timestamp=thai_str(h.timestamp) or ""
    )
