"""
TUH Chatbot AI — Admin Routers (Documents, Settings, Feedback, Unanswered, Stats, Rebuild, Forms, Announcements, History)
"""
import os
import json
import time
import uuid
import shutil
import threading
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, status, Request
from pydantic import BaseModel
from app.core.security import verify_password, create_access_token
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete

from app.core.database import get_db
from app.core.config import settings
from app.routers.auth import get_current_user
from app.models.models import (
    User, Document, SystemSettings, Feedback, UnansweredQuery,
    ChatHistory, Form as FormModel, Announcement
)
from app.schemas.schemas import (
    DocumentResponse, DocumentUpdate,
    SettingsResponse, SettingsUpdate, FAQ,
    FeedbackResponse, FeedbackSubmit,
    UnansweredResponse, UnansweredUpdate, UnansweredSubmit,
    StatsResponse, RebuildStatus,
    FormResponse, FormCreate,
    AnnouncementResponse, AnnouncementCreate, AnnouncementUpdate,
    HistoryResponse
)

UPLOADS_DIR = Path(settings.UPLOADS_DIR)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/api/admin", tags=["admin"])


class LegacyLoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def legacy_admin_login(
    payload: LegacyLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.username == payload.username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
        
    if not user.is_active:
        raise HTTPException(status_code=400, detail="บัญชีนี้ถูกระงับการใช้งาน")
        
    # Generate JWT token
    token = create_access_token(data={"sub": user.username})
    
    return {
        "success": True,
        "token": token,
        "username": user.username,
        "role": user.role,
        "name": user.display_name
    }

# ─── Rebuild State ────────────────────────────────────────────────────────────
_rebuild_status = {"status": "idle", "message": "ยังไม่ได้ประมวลผล", "duration": None}


# ═══════════════════════════════════════════════════════════════════════════════
# DOCUMENTS
# ═══════════════════════════════════════════════════════════════════════════════

def _parse_exclude_pages(pages_str: Optional[str]) -> List[int]:
    if not pages_str:
        return []
    result = []
    for x in pages_str.split(","):
        x = x.strip()
        if x.isdigit():
            result.append(int(x))
    return result


def _doc_to_response(doc: Document) -> DocumentResponse:
    return DocumentResponse(
        filename=doc.filename,
        display_name=doc.display_name,
        status=doc.status,
        pages=doc.pages,
        size=doc.size,
        exclude_pages=_parse_exclude_pages(doc.exclude_pages),
        chunking_duration=doc.chunking_duration,
        embedding_duration=doc.embedding_duration,
        upload_date=doc.upload_date.strftime("%Y-%m-%d %H:%M:%S") if doc.upload_date else ""
    )


@router.get("/documents", response_model=List[DocumentResponse])
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Document).order_by(Document.upload_date.desc()))
    docs = result.scalars().all()
    return [_doc_to_response(d) for d in docs]


@router.post("/documents/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from urllib.parse import unquote
    content_type = request.headers.get("content-type", "")
    
    if "application/pdf" in content_type:
        # Legacy adminSPO upload (raw binary PDF in request body)
        filename = request.headers.get("x-file-name", "")
        filename = unquote(filename)
        exclude_pages = request.headers.get("x-exclude-pages", "")
        display_name = request.headers.get("x-display-name", "")
        if display_name:
            display_name = unquote(display_name)
        else:
            display_name = filename.replace(".pdf", "").replace("_", " ")
            
        file_content = await request.body()
        file_size = len(file_content)
    else:
        # Standard multipart upload (new v2 frontend)
        if not file:
            raise HTTPException(status_code=400, detail="ไม่พบไฟล์ที่อัปโหลด")
        filename = file.filename
        exclude_pages = ""  # multipart doesn't send page exclusions during file upload
        display_name = filename.replace(".pdf", "").replace("_", " ")
        file_content = await file.read()
        file_size = len(file_content)

    if not filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="รองรับเฉพาะไฟล์ PDF เท่านั้น")

    file_path = UPLOADS_DIR / filename
    with open(str(file_path), "wb") as f:
        f.write(file_content)

    # Count PDF pages
    pages = None
    try:
        import fitz
        doc_pdf = fitz.open(str(file_path))
        pages = len(doc_pdf)
        doc_pdf.close()
    except Exception:
        pass

    # Check if already exists
    existing_result = await db.execute(select(Document).where(Document.filename == filename))
    existing = existing_result.scalar_one_or_none()

    if existing:
        existing.status = "Processing"
        existing.size = file_size
        existing.pages = pages
        existing.exclude_pages = exclude_pages
        existing.display_name = display_name
        doc_entry = existing
    else:
        doc_entry = Document(
            filename=filename,
            display_name=display_name,
            status="Processing",
            pages=pages,
            size=file_size,
            exclude_pages=exclude_pages
        )
        db.add(doc_entry)

    await db.commit()
    await db.refresh(doc_entry)

    # Trigger rebuild in background
    background_tasks.add_task(_trigger_rebuild_background)

    return _doc_to_response(doc_entry)


@router.put("/documents/{filename}", response_model=DocumentResponse)
async def update_document(
    filename: str,
    body: DocumentUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Document).where(Document.filename == filename))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="ไม่พบเอกสารนี้")

    if body.status is not None:
        doc.status = body.status
    if body.exclude_pages is not None:
        doc.exclude_pages = ",".join(map(str, body.exclude_pages))
    if body.display_name is not None:
        doc.display_name = body.display_name

    await db.commit()
    await db.refresh(doc)

    if body.status is not None or body.exclude_pages is not None:
        background_tasks.add_task(_trigger_rebuild_background)

    return _doc_to_response(doc)


@router.delete("/documents/{filename}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    filename: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Document).where(Document.filename == filename))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="ไม่พบเอกสารนี้")

    file_path = UPLOADS_DIR / filename
    if file_path.exists():
        file_path.unlink()

    await db.delete(doc)
    await db.commit()

    background_tasks.add_task(_trigger_rebuild_background)


# ═══════════════════════════════════════════════════════════════════════════════
# SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/settings", response_model=SettingsResponse)
async def get_settings(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    # Determine if request is authenticated as admin
    is_admin = False
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        try:
            from app.core.security import verify_access_token
            payload = verify_access_token(token)
            username = payload.get("sub")
            if username:
                result = await db.execute(select(User).where(User.username == username, User.is_active == True))
                user = result.scalar_one_or_none()
                if user:
                    is_admin = True
        except Exception:
            pass

    result = await db.execute(select(SystemSettings).where(SystemSettings.id == "config"))
    cfg = result.scalar_one_or_none()
    if not cfg:
        # Return defaults
        return SettingsResponse(
            model_name="google/gemini-2.5-flash",
            temperature=0.4,
            max_tokens=1000,
            top_k=3,
            embedding_tech="bge-m3"
        )
        
    gemini_key = ""
    if cfg.gemini_api_key:
        gemini_key = cfg.gemini_api_key if is_admin else "***masked***"
        
    return SettingsResponse(
        model_name=cfg.model_name,
        temperature=cfg.temperature,
        max_tokens=cfg.max_tokens,
        top_k=cfg.top_k,
        embedding_tech=cfg.embedding_tech,
        system_prompt=cfg.system_prompt,
        welcome_message=cfg.welcome_message,
        chat_greeting=cfg.chat_greeting,
        custom_faqs=json.loads(cfg.custom_faqs or "[]"),
        predefined_faqs=json.loads(cfg.predefined_faqs or "[]"),
        last_build_duration=cfg.last_build_duration,
        gemini_api_key=gemini_key
    )


@router.put("/settings", response_model=SettingsResponse)
async def update_settings(
    body: SettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(SystemSettings).where(SystemSettings.id == "config"))
    cfg = result.scalar_one_or_none()

    if not cfg:
        cfg = SystemSettings(id="config")
        db.add(cfg)

    if body.model_name is not None:
        cfg.model_name = body.model_name
    if body.temperature is not None:
        cfg.temperature = body.temperature
    if body.max_tokens is not None:
        cfg.max_tokens = body.max_tokens
    if body.top_k is not None:
        cfg.top_k = body.top_k
    if body.system_prompt is not None:
        cfg.system_prompt = body.system_prompt
    if body.welcome_message is not None:
        cfg.welcome_message = body.welcome_message
    if body.chat_greeting is not None:
        cfg.chat_greeting = body.chat_greeting
    if body.custom_faqs is not None:
        cfg.custom_faqs = json.dumps([f.model_dump() for f in body.custom_faqs], ensure_ascii=False)
    if body.predefined_faqs is not None:
        cfg.predefined_faqs = json.dumps([f.model_dump() for f in body.predefined_faqs], ensure_ascii=False)
    if body.gemini_api_key is not None:
        # Store API key in environment (not DB for security)
        os.environ["OPENROUTER_API_KEY"] = body.gemini_api_key

    await db.commit()
    await db.refresh(cfg)

    return SettingsResponse(
        model_name=cfg.model_name,
        temperature=cfg.temperature,
        max_tokens=cfg.max_tokens,
        top_k=cfg.top_k,
        embedding_tech=cfg.embedding_tech,
        system_prompt=cfg.system_prompt,
        welcome_message=cfg.welcome_message,
        chat_greeting=cfg.chat_greeting,
        custom_faqs=json.loads(cfg.custom_faqs or "[]"),
        predefined_faqs=json.loads(cfg.predefined_faqs or "[]"),
        last_build_duration=cfg.last_build_duration
    )


# ═══════════════════════════════════════════════════════════════════════════════
# FEEDBACK
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/feedback", response_model=List[FeedbackResponse])
async def get_feedback(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Feedback).order_by(Feedback.timestamp.desc()))
    items = result.scalars().all()
    return [FeedbackResponse(
        id=f.id, rating=f.rating, comment=f.comment, query=f.query, answer=f.answer,
        timestamp=f.timestamp.strftime("%Y-%m-%d %H:%M:%S") if f.timestamp else "",
        history_id=f.history_id
    ) for f in items]


@router.post("/feedback/submit", status_code=status.HTTP_201_CREATED)
async def submit_feedback(body: FeedbackSubmit, db: AsyncSession = Depends(get_db)):
    """User submits feedback (ไม่ต้องการ auth)"""
    entry = Feedback(
        id=f"fb-{int(time.time() * 1000)}",
        rating=body.rating,
        comment=body.comment,
        query=body.query,
        answer=body.answer,
        history_id=body.history_id
    )
    db.add(entry)
    await db.commit()
    return {"success": True}


@router.delete("/feedback/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feedback(
    feedback_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Feedback).where(Feedback.id == feedback_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="ไม่พบ Feedback นี้")
    await db.delete(item)
    await db.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# UNANSWERED QUERIES
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/unanswered", response_model=List[UnansweredResponse])
async def get_unanswered(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(UnansweredQuery).order_by(UnansweredQuery.count.desc()))
    items = result.scalars().all()
    return [UnansweredResponse(
        id=u.id, query=u.query, count=u.count, status=u.status,
        timestamp=u.timestamp.strftime("%Y-%m-%d %H:%M:%S") if u.timestamp else ""
    ) for u in items]


@router.post("/unanswered/submit", status_code=status.HTTP_201_CREATED)
async def submit_unanswered(body: UnansweredSubmit, db: AsyncSession = Depends(get_db)):
    """User-facing endpoint: บันทึกคำถามที่ระบบตอบไม่ได้"""
    result = await db.execute(
        select(UnansweredQuery).where(UnansweredQuery.query.ilike(body.query.strip()))
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.count += 1
    else:
        db.add(UnansweredQuery(
            id=f"unans-{int(time.time() * 1000)}",
            query=body.query.strip(),
            count=1,
            status="Pending"
        ))
    await db.commit()
    return {"success": True}


@router.put("/unanswered/{query_id}", response_model=UnansweredResponse)
async def update_unanswered(
    query_id: str,
    body: UnansweredUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(UnansweredQuery).where(UnansweredQuery.id == query_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="ไม่พบรายการนี้")
    item.status = body.status
    await db.commit()
    await db.refresh(item)
    return UnansweredResponse(
        id=item.id, query=item.query, count=item.count, status=item.status,
        timestamp=item.timestamp.strftime("%Y-%m-%d %H:%M:%S") if item.timestamp else ""
    )


@router.delete("/unanswered/{query_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_unanswered(
    query_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(UnansweredQuery).where(UnansweredQuery.id == query_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="ไม่พบรายการนี้")
    await db.delete(item)
    await db.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# STATS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from datetime import datetime, date

    total_queries = (await db.execute(select(func.count(ChatHistory.id)))).scalar() or 0
    total_likes = (await db.execute(select(func.count(Feedback.id)).where(Feedback.rating == "like"))).scalar() or 0
    total_dislikes = (await db.execute(select(func.count(Feedback.id)).where(Feedback.rating == "dislike"))).scalar() or 0
    total_unanswered = (await db.execute(select(func.count(UnansweredQuery.id)))).scalar() or 0
    total_documents = (await db.execute(select(func.count(Document.id)))).scalar() or 0
    active_documents = (await db.execute(select(func.count(Document.id)).where(Document.status == "Active"))).scalar() or 0

    today = date.today()
    from sqlalchemy import cast, Date
    queries_today = (await db.execute(
        select(func.count(ChatHistory.id)).where(
            cast(ChatHistory.timestamp, Date) == today
        )
    )).scalar() or 0

    avg_rt_result = await db.execute(select(func.avg(ChatHistory.response_time)))
    avg_rt = avg_rt_result.scalar() or 0.0

    return StatsResponse(
        total_queries=total_queries,
        total_likes=total_likes,
        total_dislikes=total_dislikes,
        total_unanswered=total_unanswered,
        total_documents=total_documents,
        active_documents=active_documents,
        queries_today=queries_today,
        avg_response_time=round(float(avg_rt), 3)
    )


# ═══════════════════════════════════════════════════════════════════════════════
# REBUILD
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/rebuild", response_model=RebuildStatus)
async def trigger_rebuild(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Trigger การ Rebuild Vector Index ใน Background"""
    global _rebuild_status
    if _rebuild_status["status"] == "processing":
        return RebuildStatus(status="processing", message="กำลังประมวลผลอยู่แล้ว กรุณารอสักครู่")

    _rebuild_status = {"status": "processing", "message": "กำลังเริ่มประมวลผล...", "duration": None}
    background_tasks.add_task(_trigger_rebuild_background)
    return RebuildStatus(status="processing", message="เริ่มประมวลผล Background Task แล้ว")


@router.get("/rebuild/status", response_model=RebuildStatus)
async def get_rebuild_status(current_user: User = Depends(get_current_user)):
    return RebuildStatus(**_rebuild_status)


def _trigger_rebuild_background():
    """Background thread สำหรับ Rebuild Index"""
    global _rebuild_status
    start = time.time()
    try:
        import sys
        admin_parent = str(Path(settings.ADMIN_DIR).parent)
        if admin_parent not in sys.path:
            sys.path.insert(0, admin_parent)

        from Admin.rebuild_db import rebuild
        _rebuild_status["message"] = "กำลัง rebuild index..."
        rebuild()

        from app.services.rag_service import reload_retriever
        reload_retriever()

        duration = round(time.time() - start, 2)
        _rebuild_status = {"status": "success", "message": f"Rebuild สำเร็จใน {duration} วินาที", "duration": duration}
    except Exception as e:
        _rebuild_status = {"status": "error", "message": f"เกิดข้อผิดพลาด: {e}", "duration": None}


# ═══════════════════════════════════════════════════════════════════════════════
# FORMS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/forms", response_model=List[FormResponse])
async def get_forms(db: AsyncSession = Depends(get_db)):
    """Public endpoint — ดึงรายการแบบฟอร์ม"""
    result = await db.execute(select(FormModel))
    return result.scalars().all()


@router.post("/forms", response_model=FormResponse, status_code=status.HTTP_201_CREATED)
async def create_form(
    body: FormCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    new_form = FormModel(
        id=str(uuid.uuid4()),
        name=body.name,
        filename=body.filename,
        page=body.page,
        download_link=body.download_link
    )
    db.add(new_form)
    await db.commit()
    await db.refresh(new_form)
    return new_form


@router.delete("/forms/{form_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_form(
    form_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(FormModel).where(FormModel.id == form_id))
    form = result.scalar_one_or_none()
    if not form:
        raise HTTPException(status_code=404, detail="ไม่พบแบบฟอร์มนี้")
    await db.delete(form)
    await db.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# ANNOUNCEMENTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/announcements", response_model=List[AnnouncementResponse])
async def get_announcements(db: AsyncSession = Depends(get_db)):
    """Public endpoint — ดึงประกาศทั้งหมด"""
    result = await db.execute(
        select(Announcement).order_by(Announcement.pinned.desc(), Announcement.created_at.desc())
    )
    return result.scalars().all()


@router.post("/announcements", response_model=AnnouncementResponse, status_code=status.HTTP_201_CREATED)
async def create_announcement(
    body: AnnouncementCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    ann = Announcement(**body.model_dump())
    db.add(ann)
    await db.commit()
    await db.refresh(ann)
    return ann


@router.put("/announcements/{ann_id}", response_model=AnnouncementResponse)
async def update_announcement(
    ann_id: int,
    body: AnnouncementUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Announcement).where(Announcement.id == ann_id))
    ann = result.scalar_one_or_none()
    if not ann:
        raise HTTPException(status_code=404, detail="ไม่พบประกาศนี้")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(ann, field, value)
    await db.commit()
    await db.refresh(ann)
    return ann


@router.delete("/announcements/{ann_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_announcement(
    ann_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Announcement).where(Announcement.id == ann_id))
    ann = result.scalar_one_or_none()
    if not ann:
        raise HTTPException(status_code=404, detail="ไม่พบประกาศนี้")
    await db.delete(ann)
    await db.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# HISTORY
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/history", response_model=List[HistoryResponse])
async def get_history(
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(ChatHistory).order_by(ChatHistory.timestamp.desc()).limit(limit)
    )
    items = result.scalars().all()
    return [HistoryResponse(
        id=h.id,
        query=h.query,
        answer=h.answer,
        response_time=h.response_time,
        chunk_ids=[int(x) for x in (h.chunk_ids or "").split(",") if x.strip().isdigit()],
        api_model=h.api_model,
        referenced_docs=json.loads(h.referenced_docs or "[]"),
        timestamp=h.timestamp.strftime("%Y-%m-%d %H:%M:%S") if h.timestamp else ""
    ) for h in items]


# ─── Form Upload & Page Extraction (Legacy Compatibility) ─────────────────────

def _parse_pages(page_str: str, total_pages: int) -> List[int]:
    """Parse page specification like '1,3,5' or '2-5' or '1-3,7' into sorted 0-indexed page list."""
    pages = set()
    parts = page_str.replace(' ', '').split(',')
    for part in parts:
        if not part:
            continue
        if '-' in part:
            bounds = part.split('-', 1)
            try:
                start = int(bounds[0]) - 1
                end = int(bounds[1]) - 1
            except ValueError:
                continue
            for p in range(start, end + 1):
                if 0 <= p < total_pages:
                    pages.add(p)
        else:
            try:
                p = int(part) - 1
                if 0 <= p < total_pages:
                    pages.add(p)
            except ValueError:
                continue
    return sorted(pages)


@router.post("/forms/upload")
async def upload_form_compatibility(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from urllib.parse import unquote, quote
    
    form_name = unquote(request.headers.get("x-form-name", "").strip())
    filename = unquote(request.headers.get("x-file-name", "form.pdf").strip())
    page = unquote(request.headers.get("x-form-page", "").strip())
    
    if not form_name or not filename:
        raise HTTPException(status_code=400, detail="กรุณากรอกชื่อและเลือกไฟล์แบบฟอร์มให้ครบถ้วน")
        
    post_data = await request.body()
    
    forms_dir = Path(settings.UPLOADS_DIR) / "forms"
    forms_dir.mkdir(parents=True, exist_ok=True)
    
    ts = int(time.time())
    temp_filepath = forms_dir / f"_temp_{ts}_{filename}"
    
    with open(str(temp_filepath), "wb") as f:
        f.write(post_data)
        
    final_filename = f"{ts}_{filename}"
    final_filepath = forms_dir / final_filename
    
    if page:
        try:
            import fitz
            src_doc = fitz.open(str(temp_filepath))
            total = len(src_doc)
            page_indices = _parse_pages(page, total)
            
            if not page_indices:
                src_doc.close()
                if temp_filepath.exists():
                    temp_filepath.unlink()
                raise HTTPException(
                    status_code=400, 
                    detail=f"หน้าที่ระบุ ({page}) ไม่อยู่ในไฟล์ PDF (มีทั้งหมด {total} หน้า)"
                )
                
            new_doc = fitz.open()
            for pi in page_indices:
                new_doc.insert_pdf(src_doc, from_page=pi, to_page=pi)
            new_doc.save(str(final_filepath))
            new_doc.close()
            src_doc.close()
            
            if temp_filepath.exists():
                temp_filepath.unlink()
        except HTTPException:
            raise
        except Exception as e:
            # Fallback
            if temp_filepath.exists():
                temp_filepath.rename(final_filepath)
    else:
        if temp_filepath.exists():
            temp_filepath.rename(final_filepath)
            
    # Save/Update in DB
    result = await db.execute(select(FormModel).where(func.lower(FormModel.name) == func.lower(form_name)))
    existing_form = result.scalar_one_or_none()
    
    host_header = request.headers.get("host", "localhost:8000")
    download_link = f"http://{host_header}/api/forms/download/{quote(final_filename)}"
    
    if existing_form:
        # Delete old file
        if existing_form.filename:
            old_filepath = forms_dir / existing_form.filename
            if old_filepath.exists():
                try:
                    old_filepath.unlink()
                except Exception:
                    pass
        existing_form.filename = final_filename
        existing_form.page = page
        existing_form.download_link = download_link
        message = "อัปเดตแบบฟอร์มเดิมและอัปโหลดไฟล์ใหม่สำเร็จ"
    else:
        new_form = FormModel(
            id=f"form-{int(time.time() * 1000)}",
            name=form_name,
            filename=final_filename,
            page=page,
            download_link=download_link
        )
        db.add(new_form)
        message = "บันทึกและอัปโหลดแบบฟอร์มสำเร็จ"
        
    await db.commit()
    
    return {"success": True, "message": message}
