"""
TUH Chatbot AI — Taught Search Keywords (คำค้นที่แอดมินสอนจากหน้าคำถามที่บอทตอบไม่ได้)

ปัญหา: ผู้ใช้พิมพ์ภาษาพูด ("เอาโน้ตบุ๊กกลับบ้านได้ไหม") แต่เอกสารนโยบายใช้ภาษาทางการ
("คอมพิวเตอร์แบบพกพา") ระบบจึงค้นไม่เจอ แอดมินสอน "คำค้นภาษาเอกสาร" ไว้กับคำถามที่ตอบไม่ได้
→ เมื่อมีคำถามใหม่ที่ "คล้าย" คำถามนั้น (cosine similarity ของ bge-m3 ≥ SIMILARITY_THRESHOLD)
ระบบเติมคำค้นต่อท้ายข้อความที่ใช้ค้นเอกสาร — ไม่แก้ดัชนี ไม่แก้ HybridRetriever ไม่แก้คำถามที่ส่งให้ LLM

ผลทดลองบนดัชนีจริง (2026-10-08): สอน "เอาโน้ตบุ๊กของโรงพยาบาลกลับบ้านได้ไหม" ด้วยคำที่ AI เสนอ
→ ประโยคใกล้เคียง 5 แบบ (similarity 0.73–1.00) ขึ้นจากนอก 10 อันดับเป็นอันดับ 1–2 ส่วนคำถาม
ชุดทดสอบ 80 ข้อมี similarity กับคำถามที่สอนสูงสุดแค่ 0.65 จึงไม่ถูกเติมคำเลย
"""
import asyncio
import json
import logging
import time
from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import UnansweredQuery

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.70
CACHE_TTL_SECONDS = 60

# [(id, query, keywords)] + embedding ของ query ที่สอนไว้ (คำนวณครั้งเดียวต่อ query)
_cache = {"loaded_at": 0.0, "items": []}
_vectors = {}


def invalidate_cache() -> None:
    """เรียกหลังแอดมินเปลี่ยนสถานะ/คำค้น เพื่อให้มีผลทันทีไม่ต้องรอ TTL"""
    _cache["loaded_at"] = 0.0


async def _taught_items(db: AsyncSession) -> List[Tuple[str, str, List[str]]]:
    if time.time() - _cache["loaded_at"] < CACHE_TTL_SECONDS:
        return _cache["items"]
    rows = (await db.execute(
        select(UnansweredQuery.id, UnansweredQuery.query, UnansweredQuery.search_keywords).where(
            UnansweredQuery.status == "Resolved",
            UnansweredQuery.resolution_type == "search_keywords",
        )
    )).all()
    items = []
    for row_id, query, raw in rows:
        try:
            keywords = [k for k in json.loads(raw or "[]") if isinstance(k, str) and k.strip()]
        except ValueError:
            keywords = []
        if keywords:
            items.append((row_id, query, keywords))
    _cache.update(loaded_at=time.time(), items=items)
    return items


def _best_match(model, query: str, items) -> Optional[Tuple[float, Tuple[str, str, List[str]]]]:
    """CPU-bound (encode ด้วย bge-m3) — เรียกผ่าน executor"""
    missing = [q for _, q, _ in items if q not in _vectors]
    if missing:
        for q, vec in zip(missing, model.encode(missing, convert_to_numpy=True, normalize_embeddings=True)):
            _vectors[q] = vec
    query_vec = model.encode([query], convert_to_numpy=True, normalize_embeddings=True)[0]
    scored = [(float(query_vec @ _vectors[item[1]]), item) for item in items]
    return max(scored, key=lambda x: x[0], default=None)


async def expand_retrieval_query(db: AsyncSession, retriever, query: str) -> str:
    """คืนข้อความสำหรับค้นเอกสาร: query เดิม + คำค้นที่สอนไว้ ถ้าคล้ายคำถามที่สอนไว้พอ
    ไม่มีคำที่สอนไว้ / ไม่มีโมเดล dense / เกิดข้อผิดพลาด → คืน query เดิม (ไม่ทำให้แชทพัง)"""
    try:
        model = getattr(retriever, "model", None)
        if model is None or not getattr(retriever, "dense_enabled", False):
            return query
        items = await _taught_items(db)
        if not items:
            return query
        loop = asyncio.get_event_loop()
        best = await loop.run_in_executor(None, _best_match, model, query, items)
        if not best or best[0] < SIMILARITY_THRESHOLD:
            return query
        score, (row_id, taught_query, keywords) = best
        logger.info("[Taught Keywords] '%s' ~ '%s' (%.3f) → เติม %s", query, taught_query, score, keywords)
        return f"{query} {' '.join(keywords)}"
    except Exception as e:
        logger.error("[Taught Keywords Error] %s", e)
        return query
