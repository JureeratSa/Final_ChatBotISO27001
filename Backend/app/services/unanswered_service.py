"""
TUH Chatbot AI — Unanswered Queries Service
แยกจาก app/routers/admin_unanswered.py (ย้ายมาจาก Backend/app/routers/admin.py เดิม
logic เหมือนทุกตัวอักษร ไม่ได้แก้ไข)
"""
import json
import time
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import UnansweredQuery, User
from app.schemas.schemas import UnansweredSubmit, UnansweredUpdate


def _clear_resolution(item: UnansweredQuery) -> None:
    item.resolution_type = None
    item.ignore_reason = None
    item.note = None
    item.resolved_by_id = None
    item.resolved_at = None


async def record_unanswered_query(db: AsyncSession, body: UnansweredSubmit) -> None:
    """จับคู่คำถามซ้ำแบบไม่สนตัวพิมพ์ใหญ่เล็ก (ilike) เพิ่ม count แทนสร้างแถวใหม่"""
    result = await db.execute(
        select(UnansweredQuery).where(UnansweredQuery.query.ilike(body.query.strip()))
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.count += 1
        # ถูกถามซ้ำแล้วบอทยังตอบไม่ได้ทั้งที่แอดมินปิดว่า "แก้ไขแล้ว" = วิธีแก้ยังไม่ได้ผล
        # เปิดรายการกลับเป็น Pending ให้แอดมินเห็นอีกครั้ง (Ignored ไม่เปิดคืน เพราะตั้งใจไม่แก้)
        if existing.status == "Resolved":
            existing.status = "Pending"
            _clear_resolution(existing)
    else:
        db.add(UnansweredQuery(
            id=f"unans-{int(time.time() * 1000)}",
            query=body.query.strip(),
            count=1,
            status="Pending"
        ))
    await db.commit()


def apply_unanswered_update(item: UnansweredQuery, body: UnansweredUpdate, user: User) -> None:
    """เปลี่ยนสถานะรายการ + บันทึกว่าปิดด้วยวิธีไหน/เพราะอะไร (ตรวจความถูกต้องของ field แล้วใน schema)"""
    item.status = body.status
    if body.status == "Pending":
        _clear_resolution(item)
        return
    item.resolution_type = body.resolution_type
    item.ignore_reason = body.ignore_reason
    item.note = (body.note or "").strip() or None
    item.resolved_by_id = user.id
    item.resolved_at = datetime.now(timezone.utc)


async def analyze_query(query: str) -> dict:
    """
    ใช้ AI วิเคราะห์คำถามที่ตอบไม่ได้ ก่อนแอดมินเขียนคำตอบ FAQ ด้วยมือ
    คืนค่า: is_valid_query (เป็นคำถามจริงหรือขยะ/ทักทาย) + suggested_keywords (คำค้นหาแนะนำ)
    ถ้าไม่มี LLM API key หรือเรียกไม่สำเร็จ ให้ fallback เป็นค่าที่ไม่ทำให้ UI พัง แทนการโยน error
    """
    import logging
    from app.services.rag_service import make_http_post, contains_profanity, is_chit_chat

    logger = logging.getLogger(__name__)

    query = (query or "").strip()
    if not query:
        return {"is_valid_query": False, "suggested_keywords": []}

    if contains_profanity(query) or is_chit_chat(query):
        return {"is_valid_query": False, "suggested_keywords": []}

    api_key = settings.LLM_API_KEY
    if not api_key:
        # ไม่มี LLM key — คืนค่ากลางๆ ให้แอดมินเขียนคำตอบเองได้ตามปกติ ไม่ error
        return {"is_valid_query": True, "suggested_keywords": []}

    try:
        prompt = (
            "คุณคือผู้ช่วยวิเคราะห์คำถามสำหรับระบบ FAQ ของโรงพยาบาล "
            "ตอบกลับเป็น JSON เท่านั้น ไม่มีคำอธิบายอื่น รูปแบบ: "
            '{"is_valid_query": true/false, "suggested_keywords": ["คำ1", "คำ2", ...]}\n'
            "is_valid_query = false ถ้าข้อความเป็นคำทักทาย/ขยะ/ไม่ใช่คำถามเกี่ยวกับสวัสดิการหรือ ISO ของโรงพยาบาล\n"
            "suggested_keywords = คำสำคัญ 3-5 คำที่ควรใช้แต่งประโยคคำถาม FAQ ให้ค้นหาเจอง่ายขึ้น (ถ้า is_valid_query เป็น false ให้เป็น list ว่าง)\n\n"
            f"ข้อความที่ต้องวิเคราะห์: {query}"
        )
        payload_llm = {
            "model": settings.DEFAULT_LLM_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 300,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "TUH Chatbot v2",
        }
        loop = __import__("asyncio").get_event_loop()
        res_data = await loop.run_in_executor(
            None, make_http_post, "https://openrouter.ai/api/v1/chat/completions", payload_llm, headers, 20
        )
        content = res_data.get("choices", [{}])[0].get("message", {}).get("content", "")
        match = __import__("re").search(r'\{.*\}', content, __import__("re").DOTALL)
        parsed = json.loads(match.group(0)) if match else {}
        return {
            "is_valid_query": bool(parsed.get("is_valid_query", True)),
            "suggested_keywords": list(parsed.get("suggested_keywords", []) or [])[:5],
        }
    except Exception as e:
        logger.error("[Analyze Query Error] %s", e)
        return {"is_valid_query": True, "suggested_keywords": []}
