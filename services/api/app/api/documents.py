"""
จัดการเอกสาร PDF ที่บอทใช้ตอบ (หน้า "จัดการเอกสาร" ของ AdminWeb) — /api/admin/documents*

แอดมินแผนกจัดการได้เฉพาะเอกสารของแผนกตัวเอง ทุก endpoint ที่ระบุไฟล์จึงผ่าน _get_owned_document
"""
import json
import logging
from typing import Any, List, Optional, Union
from urllib.parse import unquote

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.security import safe_filename, safe_path
from app.core.uploads import read_request_body, require_pdf
from app.models.models import Document, User
from app.rag.ocr import extract_pages
from app.schemas.schemas import DocumentResponse
from app.services.audit_service import add_audit_detail
from app.services.department_scope import UNASSIGNED, owner_department_for, require_super_admin, scope_department
from app.services.document_service import (
    WORK_FILE_SUFFIXES, check_doc_ownership, doc_to_response, parse_exclude_pages, run_approval_pipeline,
    uploads_dir,
)
from app.services.rebuild_service import delete_from_search_index, get_index_status, mark_pending, rebuild_in_background

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["documents"])


class FilenameRequest(BaseModel):
    filename: str


class ToggleDocumentRequest(FilenameRequest):
    active: bool


class UpdateDetailsRequest(FilenameRequest):
    display_name: str


class UpdateDepartmentRequest(FilenameRequest):
    department: Optional[str] = None      # None/"" = ยังไม่ระบุแผนก


class ApproveRequest(FilenameRequest):
    current_status: str


class UpdateContentRequest(FilenameRequest):
    type: str                             # raw | cleaned | chunks
    content: Union[str, List[Any]]


async def _get_document(db: AsyncSession, filename: str) -> Document:
    doc = (await db.execute(select(Document).where(Document.filename == safe_filename(filename)))).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="ไม่พบเอกสารนี้")
    return doc


async def _get_owned_document(db: AsyncSession, filename: str, user: User) -> Document:
    doc = await _get_document(db, filename)
    check_doc_ownership(doc, user)
    return doc


def _reindex_later(background: BackgroundTasks, filename: str) -> None:
    """เอกสารเปลี่ยนสถานะ → mark ว่ารอเข้าดัชนี แล้วสั่ง rebuild เบื้องหลัง"""
    mark_pending(filename)
    background.add_task(rebuild_in_background)


@router.get("/documents", response_model=List[DocumentResponse])
async def list_documents(department: Optional[str] = None,
                         current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """SuperAdmin เห็นทุกแผนก (กรองด้วย ?department= ได้, __unassigned__ = ยังไม่ระบุแผนก)"""
    query = select(Document).order_by(Document.upload_date.desc())
    dept = scope_department(current_user, department)
    if dept == UNASSIGNED:
        query = query.where(Document.department.is_(None))
    elif dept is not None:
        query = query.where(Document.department == dept)
    return [doc_to_response(d) for d in (await db.execute(query)).scalars().all()]


@router.get("/documents/index_status")
async def documents_index_status(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """ความคืบหน้า rebuild + เอกสารที่เข้าดัชนีแล้วจริง (สถานะ Active ยังไม่พอ เพราะ embedding รันเบื้องหลัง)"""
    status_data = get_index_status()
    query = select(Document.filename)
    dept = scope_department(current_user, None)
    if dept is not None:
        query = query.where(Document.department == dept)
    visible = set((await db.execute(query)).scalars().all())
    status_data["pending"] = [f for f in status_data["pending"] if f in visible]
    status_data["indexed"] = [f for f in status_data["indexed"] if f in visible]
    return status_data


@router.post("/documents/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(request: Request,
                          current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """body = ไฟล์ PDF ดิบ, ชื่อไฟล์/ชื่อแสดงผล/หน้าที่ละเว้น ส่งมาใน header X-File-Name, X-Display-Name, X-Exclude-Pages"""
    filename = safe_filename(unquote(request.headers.get("x-file-name", "")))   # ตัด path ทิ้ง กัน ../
    display_name = unquote(request.headers.get("x-display-name", "")) or filename.replace(".pdf", "").replace("_", " ")
    exclude_pages = request.headers.get("x-exclude-pages", "")
    content = await read_request_body(request, settings.MAX_DOCUMENT_UPLOAD_MB * 1024 * 1024)

    add_audit_detail(document=filename, document_name=display_name, size_bytes=len(content),
                     exclude_pages=exclude_pages or None)
    require_pdf(content, filename)

    # ชื่อไฟล์ห้ามซ้ำทั้งระบบ — อัปโหลดทับเอกสารของแผนกอื่นไม่ได้ (เช็คก่อนเขียนไฟล์)
    existing = (await db.execute(select(Document).where(Document.filename == filename))).scalar_one_or_none()
    if existing:
        check_doc_ownership(existing, current_user)

    file_path = uploads_dir() / filename
    file_path.write_bytes(content)

    # ดึงข้อความทุกหน้า (หน้าสแกนจะ OCR — ช้าหลายวินาทีต่อหน้า จึงรันใน thread แยก)
    pages = None
    try:
        page_list = await run_in_threadpool(extract_pages, str(file_path), parse_exclude_pages(exclude_pages))
        pages = len(page_list)
        raw_text = "\n\n".join(f"# Page {p['page']}\n{p['text']}" for p in page_list)
    except Exception as e:
        logger.error("[Upload] ดึงข้อความจาก %s ไม่สำเร็จ: %s", filename, e)
        raw_text = "(ไม่สามารถถอดข้อความภาษาไทยได้)"
    (uploads_dir() / f"{filename}.raw.txt").write_text(raw_text, encoding="utf-8")

    uploader = current_user.display_name or current_user.username
    doc = existing or Document(filename=filename, department=owner_department_for(current_user))
    doc.display_name = display_name
    doc.status = "Step_Raw_Text"
    doc.pages = pages
    doc.size = len(content)
    doc.exclude_pages = exclude_pages
    doc.uploaded_by = uploader
    doc.uploaded_by_id = current_user.id
    if not existing:
        db.add(doc)

    add_audit_detail(department=doc.department, replaced_existing=bool(existing) or None)
    await db.commit()
    await db.refresh(doc)
    return doc_to_response(doc)


@router.post("/documents/toggle")
async def toggle_document(payload: ToggleDocumentRequest, background: BackgroundTasks,
                          current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    doc = await _get_owned_document(db, payload.filename, current_user)
    new_status = "Active" if payload.active else "Inactive"
    add_audit_detail(from_status=doc.status, to_status=new_status)
    doc.status = new_status
    await db.commit()
    _reindex_later(background, doc.filename)
    return {"success": True}


@router.post("/documents/delete")
async def delete_document(payload: FilenameRequest, background: BackgroundTasks,
                          current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    doc = await _get_owned_document(db, payload.filename, current_user)
    for suffix in [""] + WORK_FILE_SUFFIXES:
        path = safe_path(uploads_dir(), f"{doc.filename}{suffix}")
        if path.exists():
            path.unlink()
    await db.delete(doc)
    await db.commit()
    background.add_task(delete_from_search_index, doc.filename)
    return {"success": True}


@router.post("/documents/update_details")
async def update_document_details(payload: UpdateDetailsRequest,
                                  current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    doc = await _get_owned_document(db, payload.filename, current_user)
    doc.display_name = payload.display_name.strip() or doc.filename
    add_audit_detail(new_display_name=doc.display_name)
    await db.commit()
    return {"success": True}


@router.post("/documents/update_department")
async def update_document_department(payload: UpdateDepartmentRequest,
                                     current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """ย้ายเอกสารไปแผนกอื่น (SuperAdmin เท่านั้น) — ประวัติคำตอบที่อิงเอกสารนี้ย้ายตามไปเอง"""
    require_super_admin(current_user, "เฉพาะ SuperAdmin เท่านั้นที่ย้ายแผนกของเอกสารได้")
    doc = await _get_document(db, payload.filename)
    new_department = (payload.department or "").strip() or None
    add_audit_detail(document=doc.filename, document_name=doc.display_name,
                     from_department=doc.department or "ยังไม่ระบุ", to_department=new_department or "ยังไม่ระบุ")
    doc.department = new_department
    await db.commit()
    return {"success": True, "department": doc.department}


@router.post("/documents/approve")
async def approve_document(payload: ApproveRequest, background: BackgroundTasks,
                           current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """ทำขั้นถัดไปของการอนุมัติ (ดูลำดับขั้นใน services/document_service.py)"""
    doc = await _get_owned_document(db, payload.filename, current_user)
    new_status = run_approval_pipeline(doc.filename, payload.current_status, parse_exclude_pages(doc.exclude_pages))
    add_audit_detail(from_status=payload.current_status, to_status=new_status)
    if payload.current_status == "Step_Chunk_Preview":     # ขั้นสุดท้าย → เข้าดัชนี
        _reindex_later(background, doc.filename)
    doc.status = new_status
    await db.commit()
    return {"success": True, "new_status": new_status}


@router.get("/documents/file")
async def get_document_file(filename: str, download: bool = False,
                            current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """ไฟล์ PDF สำหรับแอดมิน (ทุกสถานะ รวมฉบับร่าง) — คนทั่วไปใช้ /api/documents/serve ซึ่งเปิดได้เฉพาะ Active"""
    doc = await _get_owned_document(db, filename, current_user)
    file_path = safe_path(uploads_dir(), doc.filename)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="ไม่พบไฟล์ PDF นี้")
    return FileResponse(str(file_path), media_type="application/pdf", filename=doc.filename,
                        content_disposition_type="attachment" if download else "inline")


async def _read_owned_work_file(db, filename: str, user: User, suffix: str, missing_detail: str) -> str:
    doc = await _get_owned_document(db, filename, user)
    path = safe_path(uploads_dir(), f"{doc.filename}{suffix}")
    if not path.exists():
        raise HTTPException(status_code=404, detail=missing_detail)
    return path.read_text(encoding="utf-8")


@router.get("/documents/view_raw")
async def view_raw_document(filename: str, current_user: User = Depends(get_current_user),
                            db: AsyncSession = Depends(get_db)):
    content = await _read_owned_work_file(db, filename, current_user, ".raw.txt", "ไม่พบไฟล์ข้อความดิบ")
    return {"filename": filename, "content": content}


@router.get("/documents/view_cleaned")
async def view_cleaned_document(filename: str, current_user: User = Depends(get_current_user),
                                db: AsyncSession = Depends(get_db)):
    content = await _read_owned_work_file(db, filename, current_user, ".cleaned.md", "ไม่พบไฟล์ข้อความที่เคลียร์แล้ว")
    return {"filename": filename, "content": content}


@router.get("/documents/view_chunks")
async def view_chunks_document(filename: str, current_user: User = Depends(get_current_user),
                               db: AsyncSession = Depends(get_db)):
    content = await _read_owned_work_file(db, filename, current_user, ".chunks.json", "ไม่พบไฟล์พรีวิวแบ่ง Chunk")
    try:
        return {"filename": filename, "chunks": json.loads(content)}
    except ValueError:
        logger.exception("[View Chunks] อ่าน chunks ของ %s ไม่สำเร็จ", filename)
        raise HTTPException(status_code=500, detail="ไม่สามารถโหลดไฟล์ Chunks ได้")


@router.post("/documents/update_content")
async def update_content_document(payload: UpdateContentRequest,
                                  current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """บันทึกผลที่แอดมินแก้ในขั้นตรวจข้อความ/แบ่ง chunk"""
    doc = await _get_owned_document(db, payload.filename, current_user)
    add_audit_detail(content_type=payload.type)
    targets = {
        "raw": (".raw.txt", str, "Content สำหรับข้อความดิบต้องเป็น string"),
        "cleaned": (".cleaned.md", str, "Content สำหรับข้อความเคลียร์ต้องเป็น string"),
        "chunks": (".chunks.json", list, "Content สำหรับ Chunk ต้องเป็น list"),
    }
    if payload.type not in targets:
        raise HTTPException(status_code=400, detail=f"ประเภทเนื้อหาไม่ถูกต้อง: {payload.type}")
    suffix, expected_type, type_error = targets[payload.type]
    if not isinstance(payload.content, expected_type):
        raise HTTPException(status_code=400, detail=type_error)

    text = payload.content if expected_type is str else json.dumps(payload.content, ensure_ascii=False, indent=2)
    safe_path(uploads_dir(), f"{doc.filename}{suffix}").write_text(text, encoding="utf-8")
    return {"success": True}
