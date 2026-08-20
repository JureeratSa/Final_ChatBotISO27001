"""
TUH Chatbot AI — Chat Router (RAG Core)
Endpoints: POST /api/chat, GET /api/chat/settings
คง Pipeline เดิม: FAISS + BM25 + Weighted RRF + OpenRouter (Gemini/Ollama)
"""
import os
import re
import sys
import time
import json
import uuid
from typing import List, Optional
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.config import settings
from app.schemas.schemas import ChatRequest, ChatResponse, CitationInfo, FormLink
from app.models.models import SystemSettings, ChatHistory, UnansweredQuery, Form, Document
from app.services.rag_service import get_retriever, query_rag

from app.core.security import safe_path

router = APIRouter(prefix="/api/chat", tags=["chat"])

UPLOADS_DIR = Path(settings.UPLOADS_DIR)


# ─── Chat Endpoint ────────────────────────────────────────────────────────────

@router.post("", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Main Chat Endpoint — ประมวลผลคำถามผ่าน RAG Pipeline
    Flow: Custom FAQs → HybridRetriever (FAISS+BM25) → Weighted RRF → OpenRouter/Ollama
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

    # ─── 2. ตรวจสอบ Custom FAQs ก่อน ──────────────────────────────────────
    custom_faqs = config.get("custom_faqs", [])
    for faq in custom_faqs:
        faq_q = faq.get("question", "").strip().lower()
        if faq_q and faq_q in query.lower():
            elapsed = time.time() - start_time
            history_id = f"history-{int(time.time() * 1000)}"
            background_tasks.add_task(
                save_history, db, history_id, query, faq["answer"], [], elapsed, "custom_faq", []
            )
            return ChatResponse(
                answer=faq["answer"],
                used_rag=False,
                response_time=round(elapsed, 3),
                model="custom_faq",
                history_id=history_id
            )

    # ─── 3. RAG Pipeline ────────────────────────────────────────────────────
    rag_results = []
    try:
        retriever = get_retriever()
        if retriever:
            top_k = config.get("top_k", 3)
            rag_results = retriever.query(query, top_k=top_k)
    except Exception as e:
        print(f"[RAG Error] {e}")

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

    elapsed = time.time() - start_time

    # ─── 6. สร้าง Citations ────────────────────────────────────────────────
    citations: List[CitationInfo] = []
    form_links_out: List[FormLink] = []

    if used_rag and rag_results:
        # โหลด display_name mapping จาก DB
        docs_result = await db.execute(select(Document))
        docs = docs_result.scalars().all()
        filename_to_display = {d.filename: d.display_name for d in docs if d.display_name}

        grouped: dict = {}
        for res in rag_results:
            source = res["metadata"].get("source", "เอกสาร")
            page = res["metadata"].get("page")
            if source not in grouped:
                grouped[source] = set()
            if page:
                try:
                    grouped[source].add(int(page))
                except ValueError:
                    pass

        for source, pages in grouped.items():
            display = filename_to_display.get(source, source.replace(".pdf", "").replace("_", " "))
            pdf_url = f"/api/documents/serve/{quote(source)}#page={min(pages)}" if pages else f"/api/documents/serve/{quote(source)}"
            citations.append(CitationInfo(
                source=source,
                pages=sorted(pages),
                display_name=display,
                url=pdf_url
            ))

    # ─── 7. Form Links ─────────────────────────────────────────────────────
    for form in forms_list:
        if form.name and form.name in answer:
            form_links_out.append(FormLink(name=form.name, download_link=form.download_link))

    # ─── 8. ตรวจว่าเป็น unanswered query หรือไม่ ──────────────────────────
    is_unanswered = any(k in answer for k in ["ไม่พบข้อมูล", "ไม่มีข้อมูล", "ขออภัย", "ไม่สามารถตอบได้"])
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
        print(f"[History Save Error] {e}")


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
        print(f"[Unanswered Save Error] {e}")
