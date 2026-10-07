"""
TUH Chatbot AI — Chat Router (RAG Core)
Endpoints: POST /api/chat, GET /api/chat/settings
คง Pipeline เดิม: ChromaDB + BM25 + Weighted RRF + OpenRouter (Gemini/Ollama)
"""
import os
import re
import sys
import time
import json
import uuid
import asyncio
import logging
from typing import List, Optional
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.config import settings
from app.schemas.schemas import ChatRequest, ChatResponse, CitationInfo, FormLink
from app.models.models import SystemSettings, ChatHistory, UnansweredQuery, Form
from app.services.rag_service import (
    get_retriever, query_rag, contains_profanity, is_chit_chat,
    build_citations, is_unanswered_response, has_reliable_context, find_matching_faq,
    split_used_sources,
)

from app.core.security import safe_path
from app.core.rate_limit import rate_limit_dependency

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])

UPLOADS_DIR = Path(settings.UPLOADS_DIR)


# ─── Chat Endpoint ────────────────────────────────────────────────────────────

@router.post("", response_model=ChatResponse, dependencies=[Depends(rate_limit_dependency)])
async def chat(
    body: ChatRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Main Chat Endpoint — ประมวลผลคำถามผ่าน RAG Pipeline
    Flow: Custom FAQs / Predefined FAQs (เฉพาะข้อที่ตั้งคำตอบตายตัวไว้) → HybridRetriever
    (ChromaDB+BM25) → Weighted RRF → OpenRouter/Ollama
    """
    start_time = time.time()
    query = body.query.strip()

    if not query:
        raise HTTPException(status_code=400, detail="กรุณาพิมพ์คำถาม")

    # ─── 1. โหลด Settings จาก DB ───────────────────────────────────────────
    result = await db.execute(select(SystemSettings).where(SystemSettings.id == "config"))
    config_row = result.scalar_one_or_none()
    config = {}
    if config_row:
        config = {
            "model_name": config_row.model_name,
            "temperature": config_row.temperature,
            "max_tokens": config_row.max_tokens,
            "top_k": config_row.top_k,
            "system_prompt": config_row.system_prompt,
            "welcome_message": config_row.welcome_message,
            "custom_faqs": json.loads(config_row.custom_faqs or "[]"),
            "predefined_faqs": json.loads(config_row.predefined_faqs or "[]"),
            "gemini_api_key": settings.LLM_API_KEY,
        }

    # ─── 2. ตรวจสอบ Custom FAQs / Predefined FAQs ก่อน ────────────────────
    # predefined_faqs (ปุ่มคำถามด่วนหน้าแรก/ห้องแชท) เดิมโหลดมาเก็บใน config เฉยๆ ไม่เคยถูกเช็ค
    # ตรงนี้เลย ทำให้ "คำตอบตายตัว" ที่แอดมินตั้งไว้ในหน้าคู่มือตอบกลับ (FAQs) ไม่มีผลกับคำตอบจริง —
    # find_matching_faq() เช็คทั้งสองลิสต์ (custom_faqs ก่อนตามลำดับเดิม) และคืน source label
    # ที่ตรงกับลิสต์ที่จับคู่เจอจริง แทนการ hardcode "custom_faq" เสมอ
    custom_faqs = config.get("custom_faqs", [])
    predefined_faqs = config.get("predefined_faqs", [])
    faq_match = find_matching_faq(query, custom_faqs, predefined_faqs)
    if faq_match:
        faq_a, faq_source = faq_match
        elapsed = time.time() - start_time
        history_id = f"history-{int(time.time() * 1000)}"
        background_tasks.add_task(
            save_history, db, history_id, query, faq_a, [], elapsed, faq_source, []
        )
        return ChatResponse(
            answer=faq_a,
            used_rag=False,
            response_time=round(elapsed, 3),
            model=faq_source,
            history_id=history_id
        )

    # ─── 3. RAG Pipeline ────────────────────────────────────────────────────
    # ข้าม retriever ไปเลยถ้าเป็นคำทักทาย/หยาบคาย เพราะ query_rag() ทิ้งผล rag_results
    # ทันทีอยู่แล้วสำหรับ 2 เคสนี้ (ดู contains_profanity/is_chit_chat ใน rag_service.py)
    # เดิมคำนวณ retriever.query() ไปก่อนโดยไม่จำเป็น เสียเวลาฟรีทุกครั้งที่มีคนทักทาย/พิมพ์หยาบคาย
    #
    # retriever.query() เป็น sync/CPU-bound ล้วน (BM25 + pythainlp tokenize + Chroma search)
    # ถ้าเรียกตรงๆ ใน async def จะบล็อก event loop ทั้งตัวจนกว่าจะเสร็จ ทำให้ request อื่นรอคิว
    # หมดไม่ว่าจะมี concurrent connection กี่ตัว (วัดได้จริงจาก load test — throughput ไม่ขยับ
    # ตาม concurrency เลย) จึงต้องยกไปรันใน thread pool เหมือนที่ query_rag() ทำกับ LLM HTTP call
    rag_results = []
    if not contains_profanity(query) and not is_chit_chat(query):
        try:
            retriever = get_retriever()
            if retriever:
                top_k = config.get("top_k", 3)
                loop = asyncio.get_event_loop()
                rag_results = await loop.run_in_executor(None, lambda: retriever.query(query, top_k=top_k))
        except Exception as e:
            logger.error("[RAG Error] %s", e)

    # ─── 4. โหลด Forms สำหรับ embed ลิงก์ ────────────────────────────────
    forms_result = await db.execute(select(Form))
    forms_list = forms_result.scalars().all()

    # ─── 5. AI Generation ──────────────────────────────────────────────────
    answer, used_rag, model_used = await query_rag(
        query=query,
        results=rag_results,
        config=config,
        history=body.history,
        forms=forms_list
    )
    # ตัด tag [SOURCES: ...] ออกจากคำตอบ และเก็บเฉพาะชิ้นที่ LLM ใช้จริงไว้ทำ citation
    answer, cited_results = split_used_sources(answer, rag_results)

    elapsed = time.time() - start_time

    # ─── 6. ตรวจว่าเป็น unanswered query หรือไม่ ──────────────────────────
    # เดิมเดาจาก keyword ในคำตอบ ("ขออภัย", "ไม่สามารถตอบได้") อย่างเดียว ซึ่งชนกับข้อความ
    # ปฏิเสธคำหยาบคาย ("ขออภัยครับ ไม่สามารถตอบคำถามที่ใช้ภาษาไม่สุภาพได้...") ทำให้ทุกคำถาม
    # ที่โดนกรองคำหยาบ/เป็นคำทักทาย ถูกบันทึกลง unanswered log ผิดๆ ไปด้วย ทั้งที่ระบบทำงาน
    # ถูกต้องแล้ว (ไม่ใช่กรณี "หาคำตอบไม่เจอ") — กันด้วยการเช็ค model_used ก่อน
    is_unanswered = is_unanswered_response(answer, model_used)

    # ─── 7. สร้าง Citations ────────────────────────────────────────────────
    # ใช้ has_reliable_context() แทนเช็คแค่ "rag_results ไม่ว่าง" เพราะ retriever คืน top_k
    # เสมอไม่ว่าคำถามจะเกี่ยวกับเอกสารจริงหรือไม่ — เชื่อ used_rag ก่อน ถ้า LLM ลืมใส่ tag ค่อย
    # fallback ไปเช็ค dense similarity score (ดูเหตุผลเต็มใน rag_service.has_reliable_context)
    citations: List[CitationInfo] = []
    form_links_out: List[FormLink] = []

    if has_reliable_context(rag_results, used_rag) and not is_unanswered and cited_results:
        citation_dicts = await build_citations(db, cited_results)
        citations = [CitationInfo(**c) for c in citation_dicts]

    # ─── 8. Form Links ─────────────────────────────────────────────────────
    for form in forms_list:
        if form.name and form.name in answer:
            form_links_out.append(FormLink(name=form.name, download_link=form.download_link))

    if is_unanswered:
        background_tasks.add_task(save_unanswered, db, query)

    # ─── 9. บันทึกประวัติ ──────────────────────────────────────────────────
    history_id = f"history-{int(time.time() * 1000)}"
    chunk_ids = [res.get("chunk_id", res.get("id", 0)) for res in rag_results]
    referenced_docs = list(set(res["metadata"].get("source", "") for res in rag_results))
    background_tasks.add_task(
        save_history, db, history_id, query, answer, chunk_ids, elapsed, model_used, referenced_docs
    )

    return ChatResponse(
        answer=answer,
        citations=citations,
        form_links=form_links_out,
        used_rag=used_rag,
        response_time=round(elapsed, 3),
        model=model_used,
        history_id=history_id
    )


# ─── Serve PDF ────────────────────────────────────────────────────────────────

@router.get("/settings")
async def get_public_settings(db: AsyncSession = Depends(get_db)):
    """ดึงการตั้งค่าสาธารณะ (welcome message, predefined FAQs) สำหรับ User"""
    result = await db.execute(select(SystemSettings).where(SystemSettings.id == "config"))
    config_row = result.scalar_one_or_none()
    if not config_row:
        return {"welcome_message": None, "predefined_faqs": [], "chat_greeting": None}

    return {
        "welcome_message": config_row.welcome_message,
        "chat_greeting": config_row.chat_greeting,
        "predefined_faqs": json.loads(config_row.predefined_faqs or "[]"),
    }


@router.get("/documents/serve/{filename}")
async def serve_pdf(filename: str):
    """Serve PDF ไฟล์ให้ User เปิดดูใน browser"""
    try:
        file_path = safe_path(UPLOADS_DIR, filename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="ไม่พบไฟล์ PDF นี้")
    return FileResponse(str(file_path), media_type="application/pdf")


# ─── Background Tasks ─────────────────────────────────────────────────────────

async def save_history(db, history_id, query, answer, chunk_ids, elapsed, model_name, referenced_docs):
    """บันทึกประวัติการสนทนา (Background Task)"""
    try:
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            entry = ChatHistory(
                id=history_id,
                query=query,
                answer=answer,
                response_time=round(elapsed, 4),
                chunk_ids=",".join(map(str, chunk_ids)),
                api_model=model_name,
                referenced_docs=json.dumps(referenced_docs, ensure_ascii=False)
            )
            session.add(entry)
            await session.commit()
    except Exception as e:
        logger.error("[History Save Error] %s", e)


async def save_unanswered(db, query):
    """บันทึกคำถามที่ตอบไม่ได้ (Background Task)"""
    try:
        from sqlalchemy import update as sql_update, func
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(UnansweredQuery).where(
                    UnansweredQuery.query.ilike(query.strip())
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                existing.count += 1
            else:
                session.add(UnansweredQuery(
                    id=f"unans-{int(time.time() * 1000)}",
                    query=query.strip(),
                    count=1,
                    status="Pending"
                ))
            await session.commit()
    except Exception as e:
        logger.error("[Unanswered Save Error] %s", e)
