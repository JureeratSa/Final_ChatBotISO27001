"""
TUH Chatbot AI — Public / Compatibility Router
Endpoint สาธารณะที่ไม่ได้ผูกกับ resource ใดโดยเฉพาะ (health check, ดาวน์โหลดไฟล์) รวมถึง
endpoint compatibility ของ frontend รุ่นเดิมที่ยังใช้งานอยู่จริง (/api/search, /api/ip,
/api/announcements/active) — ย้ายออกจาก main.py เพื่อไม่ให้ entry point ของแอปพันกับ
business logic (เดิม main.py มี route handler ปนอยู่กับ FastAPI app setup ยาวเกือบ 300 บรรทัด)
"""
import asyncio
import datetime
import json
import logging
import socket
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.core.config import settings
from app.core.rate_limit import rate_limit_dependency
from app.core.security import safe_path
from app.models.models import Announcement, Form, SystemSettings
from app.schemas.schemas import ChatRequest

logger = logging.getLogger(__name__)
router = APIRouter(tags=["public"])


def is_announcement_active(start_date: Optional[str], end_date: Optional[str], now: datetime.datetime) -> bool:
    """คำนวณว่าประกาศ (เก็บ start_date/end_date เป็น string) กำลัง active ณ เวลา now หรือไม่
    รองรับ 2 รูปแบบ: วันที่ล้วน "YYYY-MM-DD" (เติม T00:00/T23:59 อัตโนมัติ) หรือวันที่+เวลา
    "YYYY-MM-DDTHH:MM" — เทียบแบบ string ตรงๆ ได้เพราะ format ISO เรียงตามตัวอักษรตรงกับลำดับเวลา
    แยกออกมาจาก compatibility_active_announcements() เพื่อ unit test ได้โดยไม่ต้องมี DB จริง
    (ดู UT-14 ใน web_testing/unit/test_ut_announcement.py) — พฤติกรรมเดิมทุกกรณี ไม่ได้แก้ logic
    """
    start = start_date or ""
    end = end_date or ""

    if len(start) == 10:
        start += "T00:00"
    if len(end) == 10:
        end += "T23:59"

    now_str = now.strftime("%Y-%m-%dT%H:%M")
    now_date_str = now.strftime("%Y-%m-%d")

    if len(now_str) == 16 and len(start) == 16 and len(end) == 16:
        return start <= now_str <= end
    return start <= now_date_str <= end

# ค่าคงที่ระดับ module (ไม่ใช่ property เรียกสดทุกครั้ง) เพื่อให้เทส monkeypatch แทนที่ตอนรัน
# ทดสอบได้ตรงๆ เหมือน UPLOADS_DIR ใน routers/chat.py และ routers/admin.py
UPLOADS_DIR = Path(settings.UPLOADS_DIR)


# ─── Health Check ─────────────────────────────────────────────────────────────

@router.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


# ─── File Downloads ───────────────────────────────────────────────────────────

@router.get("/api/forms/download/{filename}")
async def download_form_file(filename: str):
    try:
        forms_dir = UPLOADS_DIR / "forms"
        form_path = safe_path(forms_dir, filename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not form_path.exists():
        raise HTTPException(status_code=404, detail="ไม่พบไฟล์แบบฟอร์มนี้")
    return FileResponse(
        path=str(form_path),
        filename=filename.split("_", 1)[-1],
        media_type="application/pdf"
    )


@router.get("/api/documents/serve/{filename}")
async def main_serve_pdf(filename: str):
    try:
        file_path = safe_path(UPLOADS_DIR, filename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="ไม่พบไฟล์ PDF นี้")
    return FileResponse(str(file_path), media_type="application/pdf")


@router.get("/api/documents/download/{filename}")
async def main_download_pdf(filename: str):
    """ดาวน์โหลดไฟล์ PDF ต้นฉบับ — เรียกจากลิงก์ดาวน์โหลดในตารางเอกสารของ AdminWeb
    (ต่างจาก /api/documents/serve/ ที่เปิดดูแบบ inline ในเบราว์เซอร์)"""
    try:
        file_path = safe_path(UPLOADS_DIR, filename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="ไม่พบไฟล์ PDF นี้")
    return FileResponse(
        str(file_path),
        media_type="application/pdf",
        filename=file_path.name,
    )


# ─── Legacy Compatibility Endpoints (ยังใช้งานจริงโดย UserWeb) ─────────────────

@router.post("/api/search", dependencies=[Depends(rate_limit_dependency)])
async def compatibility_search(
    request: Request,
    body: ChatRequest,
    background_tasks: BackgroundTasks
):
    # import AsyncSessionLocal สดทุกครั้งที่เรียก (ไม่ผูกไว้ตอน module import) เพราะ endpoint นี้
    # ไม่ได้ใช้ Depends(get_db) — ต้อง import ทีหลังเพื่อให้ค่าที่ถูก monkeypatch ใน pytest
    # fixture (session_maker) มีผลจริงตอนเทส ไม่งั้นเทสจะหลุดไปต่อ DB จริงตาม .env
    from app.core.database import AsyncSessionLocal
    from app.services.rag_service import (
        get_retriever, query_rag, contains_profanity, is_chit_chat,
        build_citations, is_unanswered_response, has_reliable_context, find_matching_faq,
        split_used_sources,
    )
    from app.routers.chat import save_history, save_unanswered

    start_time = time.time()
    query = body.query.strip()
    if not query:
        return {"answer": "กรุณาพิมพ์คำถาม", "results": []}

    async with AsyncSessionLocal() as db:
        # Load settings
        result = await db.execute(select(SystemSettings).where(SystemSettings.id == "config"))
        config_row = result.scalar_one_or_none()
        config = {}
        custom_faqs = []
        predefined_faqs = []
        if config_row:
            config = {
                "model_name": config_row.model_name,
                "temperature": config_row.temperature,
                "max_tokens": config_row.max_tokens,
                "top_k": config_row.top_k,
                "system_prompt": config_row.system_prompt
            }
            try:
                custom_faqs = json.loads(config_row.custom_faqs or "[]")
            except Exception:
                pass
            try:
                predefined_faqs = json.loads(config_row.predefined_faqs or "[]")
            except Exception:
                pass

        # Check FAQs — find_matching_faq() เช็ค custom_faqs ก่อนแล้วค่อย predefined_faqs
        # (ปุ่มคำถามด่วนหน้าแรก/ห้องแชท) เหมือน chat.py ใช้ฟังก์ชันร่วมกันแทนเขียน loop ซ้ำ
        faq_match = find_matching_faq(query, custom_faqs, predefined_faqs)
        if faq_match:
            faq_a, _faq_source = faq_match
            return {"answer": faq_a, "results": []}

        # Query retriever — ข้ามถ้าเป็นคำทักทาย/หยาบคาย เพราะ query_rag() ทิ้งผลนี้อยู่แล้ว
        # ยกไปรันใน thread pool เพราะ retriever.query() เป็น sync/CPU-bound ไม่งั้นบล็อก event loop
        rag_results = []
        if not contains_profanity(query) and not is_chit_chat(query):
            try:
                retriever = get_retriever()
                if retriever:
                    top_k = config.get("top_k", 3)
                    loop = asyncio.get_event_loop()
                    rag_results = await loop.run_in_executor(None, lambda: retriever.query(query, top_k=top_k))
            except Exception as e:
                logger.error("[Compatibility Search RAG Error] %s", e)

        # Load Forms
        forms_result = await db.execute(select(Form))
        forms_list = forms_result.scalars().all()

        # Query RAG
        answer, used_rag, model_used = await query_rag(
            query=query,
            results=rag_results,
            config=config,
            history=body.history,
            forms=forms_list
        )
        # ตัด tag [SOURCES: ...] ออก และเก็บเฉพาะชิ้นที่ LLM ใช้จริงไว้ทำ citation (เหมือน chat.py)
        answer, cited_results = split_used_sources(answer, rag_results)

        elapsed = time.time() - start_time

        # Unanswered check — เช็ค model_used ก่อนเสมือน chat.py (ดูคอมเมนต์ที่นั่นสำหรับเหตุผล)
        is_unanswered = is_unanswered_response(answer, model_used)
        if is_unanswered:
            background_tasks.add_task(save_unanswered, db, query)

        # Citations — ใช้ has_reliable_context() เหมือน chat.py แทนเช็คแค่ rag_results ไม่ว่าง
        # (ดูเหตุผลเต็มใน rag_service.has_reliable_context — retriever คืน top_k เสมอไม่ว่า
        # คำถามจะเกี่ยวกับเอกสารจริงหรือไม่ เช็คแค่ไม่ว่างเดิมจึงเกือบไม่มีความหมาย)
        citations = []
        if has_reliable_context(rag_results, used_rag) and not is_unanswered and cited_results:
            citations = await build_citations(db, cited_results)

        # Log history in background
        history_id = f"history-{int(time.time() * 1000)}"
        chunk_ids = [res.get("chunk_id", res.get("id", 0)) if isinstance(res, dict) else 0 for res in rag_results]
        referenced_docs = list(set(res["metadata"].get("source", "") for res in rag_results if isinstance(res, dict) and "metadata" in res))

        background_tasks.add_task(
            save_history, db, history_id, query, answer, chunk_ids, elapsed, model_used, referenced_docs
        )

        return {
            "answer": answer,
            "results": rag_results,
            "citations": citations,
        }


@router.get("/api/announcements/active")
async def compatibility_active_announcements():
    from app.core.database import AsyncSessionLocal  # ดูคอมเมนต์ compatibility_search ด้านบน

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Announcement).order_by(Announcement.pinned.desc(), Announcement.created_at.desc())
        )
        announcements = result.scalars().all()

        now = datetime.datetime.now()
        active_list = []

        for a in announcements:
            if is_announcement_active(a.start_date, a.end_date, now):
                active_list.append({
                    "id": a.id,
                    "title": a.title,
                    "content": a.content,
                    "start_date": a.start_date,
                    "end_date": a.end_date,
                    "pinned": a.pinned
                })

        return active_list


@router.get("/api/ip")
async def compatibility_ip(request: Request):
    client_ip = request.headers.get("x-forwarded-for")
    if client_ip:
        client_ip = client_ip.split(",")[0].strip()
    else:
        client_ip = request.headers.get("x-real-ip", request.client.host if request.client else "127.0.0.1")

    if client_ip in ("127.0.0.1", "localhost", "::1"):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 1))
            client_ip = s.getsockname()[0]
        except Exception:
            pass
        finally:
            s.close()

    return {"ip": client_ip}
