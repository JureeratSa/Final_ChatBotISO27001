"""
ขั้นตอนตอบคำถาม 1 ข้อ (เรียกจาก POST /api/search)

  1. คำถามตรงกับ FAQ ที่แอดมินตั้งคำตอบไว้ → ตอบเลย
  2. ค้นเอกสาร (HybridRetriever) — ข้ามถ้าเป็นคำหยาบ/คำทักทาย
  3. ให้ LLM ตอบจาก chunk ที่ค้นเจอ
  4. เลือกเอกสารอ้างอิง + ลิงก์แบบฟอร์มที่แนบไปกับคำตอบ
  5. บันทึกประวัติ (และคำถามที่ตอบไม่ได้) หลังส่งคำตอบไปแล้ว
"""
import asyncio
import json
import logging
import time
from typing import List

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.models import ChatHistory, Form, SystemSettings
from app.rag.answer import (
    build_citations, cites_sources_explicitly, condense_question, contains_profanity, find_matching_faq,
    get_retriever, has_reliable_context, is_chit_chat, is_unanswered_response, query_rag, split_used_sources,
)
from app.services.department_scope import answer_documents
from app.services.taught_keywords_service import expand_retrieval_query
from app.services.unanswered_service import record_unanswered_query

logger = logging.getLogger(__name__)


def _load_json_list(raw) -> list:
    try:
        return json.loads(raw or "[]")
    except ValueError:
        return []


async def load_chat_config(db: AsyncSession) -> dict:
    row = (await db.execute(select(SystemSettings).where(SystemSettings.id == "config"))).scalar_one_or_none()
    if not row:
        return {}
    return {
        "temperature": row.temperature,
        "max_tokens": row.max_tokens,
        "top_k": row.top_k,
        "system_prompt": row.system_prompt,
        "custom_faqs": _load_json_list(row.custom_faqs),
        "predefined_faqs": _load_json_list(row.predefined_faqs),
    }


async def search_documents(db: AsyncSession, query: str, history: List, top_k: int) -> List[dict]:
    retriever = get_retriever()
    if not retriever:
        return []
    try:
        # คำถามที่ใช้ "ค้น" อาจต่างจากคำถามที่ส่งให้ LLM:
        # เติมหัวข้อจากประวัติแชท ("มีแนะนำมั้ย" → "มีคำแนะนำการตั้งรหัสผ่านมั้ย")
        # และเติมคำค้นที่แอดมินสอนไว้ให้คำถามที่คล้ายกัน
        search_query = await condense_question(query, history)
        search_query = await expand_retrieval_query(db, retriever, search_query)
        # retriever.query ใช้ CPU ล้วน — รันใน thread แยก ไม่ให้ request อื่นต้องรอ
        return await asyncio.to_thread(retriever.query, search_query, top_k)
    except Exception as e:
        logger.error("[RAG] ค้นเอกสารไม่สำเร็จ: %s", e)
        return []


async def answer_question(db: AsyncSession, query: str, history: List, background: BackgroundTasks) -> dict:
    """คืน {"answer", "citations", "form_links"} ตามที่ UserWeb ใช้"""
    start = time.time()
    config = await load_chat_config(db)

    faq = find_matching_faq(query, config.get("custom_faqs", []), config.get("predefined_faqs", []))
    if faq:
        return {"answer": faq[0], "results": []}

    rag_results = []
    if not contains_profanity(query) and not is_chit_chat(query):
        rag_results = await search_documents(db, query, history, config.get("top_k", 3))

    forms = (await db.execute(select(Form))).scalars().all()
    answer, used_rag, model_used = await query_rag(query, rag_results, config, history, forms)

    # LLM บอกเลข chunk ที่ใช้ตอบจริงมาใน [SOURCES: ...] — แนบเฉพาะเอกสารพวกนั้น
    explicit_sources = cites_sources_explicitly(answer, rag_results)
    answer, cited_results = split_used_sources(answer, rag_results)
    unanswered = is_unanswered_response(answer, model_used)

    # คำตอบที่ตอบได้บางส่วนนับเป็น "ตอบไม่ได้" (แอดมินจะเห็นว่าเอกสารขาดอะไร)
    # แต่ถ้า LLM ระบุแหล่งอ้างอิงมาเอง ก็ยังแนบเอกสารให้ส่วนที่ตอบได้
    citations = []
    if has_reliable_context(rag_results, used_rag) and cited_results and (not unanswered or explicit_sources):
        citations = await build_citations(db, cited_results)

    form_links = [{"name": f.name, "download_link": f.download_link}
                  for f in forms if f.name and f.download_link and f.name in answer]

    # เอกสารที่คำตอบนี้อิง — ใช้แยกประวัติ/คำถามที่ตอบไม่ได้ให้แอดมินแต่ละแผนก
    answer_docs = answer_documents(rag_results, cited_results if citations else [])
    if unanswered:
        background.add_task(save_unanswered, query, answer_docs)
    background.add_task(save_history, query, answer, rag_results, time.time() - start, model_used, answer_docs)

    return {"answer": answer, "citations": citations, "form_links": form_links}


# ─── งานเบื้องหลัง (รันหลังส่งคำตอบให้ผู้ใช้แล้ว ใช้ session ใหม่ของตัวเอง) ───────

async def save_history(query: str, answer: str, rag_results: List[dict], elapsed: float,
                       model_name: str, answer_docs: List[str]) -> None:
    try:
        async with AsyncSessionLocal() as session:
            session.add(ChatHistory(
                id=f"history-{int(time.time() * 1000)}",
                query=query,
                answer=answer,
                response_time=round(elapsed, 4),
                chunk_ids=",".join(str(r.get("chunk_id", 0)) for r in rag_results),
                api_model=model_name,
                referenced_docs=json.dumps(list({r["metadata"].get("source", "") for r in rag_results}),
                                           ensure_ascii=False),
                cited_docs=json.dumps(answer_docs or [], ensure_ascii=False),
            ))
            await session.commit()
    except Exception as e:
        logger.error("[History] บันทึกไม่สำเร็จ: %s", e)


async def save_unanswered(query: str, answer_docs: List[str]) -> None:
    try:
        async with AsyncSessionLocal() as session:
            await record_unanswered_query(session, query, answer_docs)
    except Exception as e:
        logger.error("[Unanswered] บันทึกไม่สำเร็จ: %s", e)
