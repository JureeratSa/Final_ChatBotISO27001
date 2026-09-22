"""
TUH Chatbot AI — History Service
แยกจาก app/routers/admin_history.py (ย้ายมาจาก Backend/app/routers/admin.py เดิม
logic เหมือนทุกตัวอักษร ไม่ได้แก้ไข)
"""
import json

from app.models.models import ChatHistory
from app.schemas.schemas import HistoryResponse


def history_row_to_response(h: ChatHistory) -> HistoryResponse:
    return HistoryResponse(
        id=h.id,
        query=h.query,
        answer=h.answer,
        response_time=h.response_time,
        chunk_ids=[int(x) for x in (h.chunk_ids or "").split(",") if x.strip().isdigit()],
        api_model=h.api_model,
        referenced_docs=json.loads(h.referenced_docs or "[]"),
        timestamp=h.timestamp.strftime("%Y-%m-%d %H:%M:%S") if h.timestamp else ""
    )
