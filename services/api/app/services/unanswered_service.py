"""คำถามที่บอทตอบไม่ได้ — บันทึก, เปลี่ยนสถานะ, ให้ AI ช่วยแนะนำคำค้น"""
import json
import logging
import re
import time
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import UnansweredQuery, User
from app.rag.answer import call_llm, contains_profanity, get_retriever, is_chit_chat, llm_is_configured
from app.schemas.schemas import UnansweredUpdate
from app.services.department_scope import guess_department

logger = logging.getLogger(__name__)


def _clear_resolution(item: UnansweredQuery) -> None:
    # ไม่ล้าง search_keywords — เก็บไว้ให้แอดมินแก้ต่อตอนสอนใหม่
    item.resolution_type = None
    item.ignore_reason = None
    item.note = None
    item.resolved_by_id = None
    item.resolved_at = None


async def record_unanswered_query(db: AsyncSession, query: str, answer_docs=None) -> None:
    """คำถามซ้ำ (ไม่สนตัวพิมพ์) → เพิ่ม count แทนสร้างแถวใหม่
    answer_docs = เอกสารที่ค้นเจอใกล้เคียงที่สุด ใช้เดาว่าคำถามนี้เป็นของแผนกไหน"""
    query = query.strip()
    department = await guess_department(db, answer_docs or [])
    existing = (await db.execute(
        select(UnansweredQuery).where(UnansweredQuery.query.ilike(query))
    )).scalar_one_or_none()

    if existing:
        existing.count += 1
        if not existing.department and department:
            existing.department = department
        # แอดมินปิดว่า "แก้ไขแล้ว" แต่ยังตอบไม่ได้ = วิธีแก้ไม่ได้ผล → เปิดกลับเป็น Pending
        # (Ignored ไม่เปิดคืน เพราะตั้งใจไม่แก้)
        if existing.status == "Resolved":
            existing.status = "Pending"
            _clear_resolution(existing)
    else:
        db.add(UnansweredQuery(id=f"unans-{int(time.time() * 1000)}", query=query,
                               count=1, status="Pending", department=department))
    await db.commit()


def apply_unanswered_update(item: UnansweredQuery, body: UnansweredUpdate, user: User) -> None:
    """เปลี่ยนสถานะ + บันทึกว่าปิดด้วยวิธีไหน (ตรวจความถูกต้องของ field แล้วใน schema)"""
    item.status = body.status
    if body.status == "Pending":
        _clear_resolution(item)
        return
    item.resolution_type = body.resolution_type
    item.ignore_reason = body.ignore_reason
    item.note = (body.note or "").strip() or None
    if body.search_keywords:
        item.search_keywords = json.dumps(body.search_keywords, ensure_ascii=False)
    item.resolved_by_id = user.id
    item.resolved_at = datetime.now(timezone.utc)


def _document_titles() -> list:
    """ชื่อเรื่องของเอกสารในดัชนี (จากบรรทัด "เรื่อง : ...") — ไม่เจอใช้ชื่อไฟล์แทน"""
    titles = {}
    for c in (getattr(get_retriever(), "bm25_chunks", None) or []):
        source = (c.get("metadata") or {}).get("source")
        if not source or titles.get(source):
            continue
        m = re.search(r"เรื่อง\s*:\s*(.+?)\s{2,}", c.get("content", ""))
        titles[source] = m.group(1).strip() if m else None
    return [t or src.rsplit(".", 1)[0] for src, t in titles.items()]


async def analyze_query(query: str) -> dict:
    """ให้ AI ดูว่าเป็นคำถามจริงไหม + เสนอคำค้น "ภาษาเอกสาร" 3-5 คำ
    (ผู้ใช้พิมพ์ "โน้ตบุ๊ก" แต่เอกสารเขียน "คอมพิวเตอร์แบบพกพา" — คำแบบเอกสารเท่านั้นที่ช่วยให้ค้นเจอ)
    เรียก AI ไม่ได้ → คืนค่ากลางๆ ให้แอดมินกรอกเองได้"""
    query = (query or "").strip()
    if not query or contains_profanity(query) or is_chit_chat(query):
        return {"is_valid_query": False, "suggested_keywords": []}
    if not llm_is_configured():
        return {"is_valid_query": True, "suggested_keywords": []}

    titles = _document_titles()
    docs_block = ("\nเอกสารที่มีในระบบ:\n" + "\n".join(f"- {t}" for t in titles) + "\n") if titles else ""
    prompt = (
        "คุณช่วยแอดมินแชทบอทโรงพยาบาลวิเคราะห์คำถามที่บอทตอบไม่ได้ "
        "ตอบกลับเป็น JSON เท่านั้น ไม่มีคำอธิบายอื่น รูปแบบ: "
        '{"is_valid_query": true/false, "suggested_keywords": ["คำ1", "คำ2", ...]}\n'
        "is_valid_query = false ถ้าข้อความเป็นคำทักทาย/ขยะ/ไม่ใช่คำถามเกี่ยวกับงานหรือนโยบายของโรงพยาบาล\n"
        "suggested_keywords = คำค้น 3-5 คำ/วลี ที่ช่วยให้ระบบค้นเอกสารเจอคำตอบ — ผู้ใช้มักพิมพ์ภาษาพูด "
        "แต่เอกสารใช้ภาษาทางการ ให้เสนอคำแบบที่น่าจะเขียนอยู่ในเอกสาร (เช่น ผู้ใช้พิมพ์ 'โน้ตบุ๊ก' "
        "เอกสารเขียน 'คอมพิวเตอร์แบบพกพา') โดยอิงชื่อเอกสารด้านล่าง "
        "(ถ้า is_valid_query เป็น false ให้เป็น list ว่าง)\n"
        f"{docs_block}\n"
        f"ข้อความที่ต้องวิเคราะห์: {query}"
    )
    try:
        content = await call_llm([{"role": "user", "content": prompt}], temperature=0.1, max_tokens=300, timeout=20)
        match = re.search(r'\{.*\}', content, re.DOTALL)
        parsed = json.loads(match.group(0)) if match else {}
        return {
            "is_valid_query": bool(parsed.get("is_valid_query", True)),
            "suggested_keywords": list(parsed.get("suggested_keywords", []) or [])[:5],
        }
    except Exception as e:
        logger.error("[Analyze Query] %s", e)
        return {"is_valid_query": True, "suggested_keywords": []}
