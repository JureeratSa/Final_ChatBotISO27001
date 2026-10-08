"""
TUH Chatbot AI — Chunk Hint Service
"สอนบอทผ่านเอกสาร": แอดมินผูกคำถามตัวอย่างกับ chunk ที่มีคำตอบอยู่แล้วแต่บอทค้นไม่เจอ
แทนการเพิ่ม Custom FAQ (คำตอบยังมาจาก PDF จริงพร้อม citation เดิม)

ที่เก็บจริงของ hint คือตาราง chunk_hints ใน TiDB — ดัชนีค้นหา (bm25.pkl + ChromaDB) เป็นแค่
ผลลัพธ์ที่ derive มา ต้อง sync ใหม่ทุกครั้งที่ hint เปลี่ยน หรือดัชนีถูกสร้าง/แก้ใหม่
(rebuild ทั้งคลัง, ลบเอกสาร) ผ่าน sync_hints_to_index()
"""
import json
import logging
import re
import sys
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select

from app.core.config import settings
from app.models.models import ChunkHint

logger = logging.getLogger(__name__)

# การเขียนดัชนี (bm25.pkl / ChromaDB) ต้องทำทีละงาน — hint หลายอันอาจถูกบันทึกพร้อมกัน
_index_write_lock = threading.Lock()


def _admin_module():
    admin_parent = str(Path(settings.ADMIN_DIR).parent)
    if admin_parent not in sys.path:
        sys.path.insert(0, admin_parent)
    from Admin import emb
    return emb


def hints_map(rows) -> Dict[Tuple[str, str], List[str]]:
    return {(h.source, h.chunk_hash): json.loads(h.questions or "[]") for h in rows}


def apply_hints_sync(hints: Dict[Tuple[str, str], List[str]]) -> dict:
    """นำ hint ชุดเต็มเข้าดัชนีปัจจุบัน (CPU-bound: tokenize + encode — เรียกผ่าน executor/thread)"""
    from app.services.rag_service import get_retriever
    emb = _admin_module()
    with _index_write_lock:
        return emb.apply_chunk_hints(hints, retriever=get_retriever())


def sync_hints_to_index() -> None:
    """อ่าน hint ทั้งหมดจาก DB แบบ sync แล้วนำเข้าดัชนี — เรียกหลัง rebuild / ลบเอกสาร
    (รันใน background thread อยู่แล้ว จึงใช้ DATABASE_URL_SYNC แบบเดียวกับ _sync_update_rebuild_status)"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    sync_engine = create_engine(settings.DATABASE_URL_SYNC)
    try:
        with Session(sync_engine) as session:
            rows = session.execute(select(ChunkHint)).scalars().all()
            hints = hints_map(rows)
        if not hints:
            return
        result = apply_hints_sync(hints)
        logger.info("[Chunk Hints] นำ hint เข้าดัชนีแล้ว %s", result)
    except Exception as e:
        logger.error("[Chunk Hints] sync เข้าดัชนีไม่สำเร็จ: %s", e)
    finally:
        sync_engine.dispose()


def serialize_chunk(chunk: dict, emb, hints: Dict[Tuple[str, str], List[str]]) -> dict:
    meta = chunk.get("metadata") or {}
    key = emb.chunk_key(chunk)
    return {
        "chunk_id": chunk.get("chunk_id"),
        "source": meta.get("source"),
        "page": meta.get("page"),
        "content": chunk.get("content", ""),
        "chunk_hash": key[1],
        "hint_questions": hints.get(key, []),
    }


def find_chunk(retriever, source: str, content_hash: str) -> Optional[dict]:
    emb = _admin_module()
    for c in (retriever.bm25_chunks or []):
        if emb.chunk_key(c) == (source, content_hash):
            return c
    return None


def rank_of_chunk(results: List[dict], source: str, content_hash: str) -> Optional[int]:
    emb = _admin_module()
    for r in results:
        if emb.chunk_key(r) == (source, content_hash):
            return r.get("hybrid_rank")
    return None


def clean_questions(questions: List[str]) -> List[str]:
    seen, cleaned = set(), []
    for q in questions:
        q = re.sub(r"\s+", " ", (q or "")).strip()
        if q and q.lower() not in seen:
            seen.add(q.lower())
            cleaned.append(q)
    return cleaned


async def suggest_questions(content: str, query: str) -> List[str]:
    """ให้ LLM เสนอคำถามตัวอย่าง 3-5 ข้อที่ chunk นี้ตอบได้ (แอดมินตรวจ/แก้ก่อนบันทึกเสมอ)
    ไม่มี API key หรือเรียกไม่สำเร็จ → คืนคำถามต้นเรื่องอย่างเดียว ไม่ทำให้ UI พัง"""
    from app.services.rag_service import make_http_post

    fallback = clean_questions([query]) if query else []
    if not settings.LLM_API_KEY:
        return fallback
    prompt = (
        "คุณช่วยแอดมินระบบแชทบอทของโรงพยาบาล ให้เขียน 'คำถามตัวอย่าง' ที่ผู้ใช้น่าจะพิมพ์ถาม "
        "แล้วเนื้อหาด้านล่างตอบได้ เพื่อช่วยให้ระบบค้นหาเจอเนื้อหานี้\n"
        "กฎ: 3-5 คำถาม ภาษาไทยแบบที่คนทั่วไปพิมพ์ สั้น ใช้คำสำคัญจากทั้งคำถามต้นเรื่องและเนื้อหา "
        "ห้ามถามเรื่องที่เนื้อหาไม่ได้ตอบ ตอบกลับเป็น JSON array ของ string เท่านั้น\n\n"
        f"คำถามต้นเรื่องที่บอทตอบไม่ได้: {query}\n\nเนื้อหา:\n{content[:3000]}"
    )
    payload = {
        "model": settings.DEFAULT_LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 400,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.LLM_API_KEY}",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "TUH Chatbot v2",
    }
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(
            None, make_http_post, "https://openrouter.ai/api/v1/chat/completions", payload, headers, 20
        )
        text = res.get("choices", [{}])[0].get("message", {}).get("content", "")
        match = re.search(r"\[.*\]", text, re.DOTALL)
        parsed = json.loads(match.group(0)) if match else []
        questions = clean_questions([str(q)[:300] for q in parsed if isinstance(q, str)])[:5]
        return questions or fallback
    except Exception as e:
        logger.error("[Chunk Hint Suggest Error] %s", e)
        return fallback
