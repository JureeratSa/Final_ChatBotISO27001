"""
TUH Chatbot AI — Admin Router: Documents
แยกออกมาจาก Backend/app/routers/admin.py — Endpoint/logic เหมือนเดิมทุกตัวอักษร
Business logic ย้ายไปที่ app/services/document_service.py (ownership check, response
mapping, exclude-pages parsing, approval pipeline) และ app/services/rebuild_service.py
(_trigger_rebuild_background, _delete_from_search_index)

หมายเหตุ: test_documents_ownership.py monkeypatch `_trigger_rebuild_background` /
`_delete_from_search_index` โดยแพตช์ที่โมดูลนี้ (admin_documents) ไม่ใช่ที่
rebuild_service — ดู comment ใน rebuild_service.py
"""
import json
import logging
from pathlib import Path
from typing import Any, List, Optional, Union

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.config import settings
from app.core.security import safe_filename, safe_path
from app.routers.auth import get_current_user
from app.models.models import User, Document
from app.schemas.schemas import DocumentResponse, DocumentUpdate
from app.services.document_service import (
    _check_doc_ownership, _doc_to_response, _parse_exclude_pages, run_approval_pipeline
)
from app.services.rebuild_service import _delete_from_search_index, _trigger_rebuild_background

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"])

UPLOADS_DIR = Path(settings.UPLOADS_DIR)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


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

    # ตัด path component ทิ้งก่อนเช็คนามสกุล/ต่อ path ป้องกัน Path Traversal (CWE-22)
    # เดิมเอา filename จาก header x-file-name ไปต่อ path ตรงๆ ส่ง "../../x.pdf" เขียนไฟล์
    # นอก UPLOADS_DIR ได้เลย
    filename = safe_filename(filename)
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="รองรับเฉพาะไฟล์ PDF เท่านั้น")

    file_path = UPLOADS_DIR / filename
    with open(str(file_path), "wb") as f:
        f.write(file_content)

    # Count PDF pages and extract raw text for Step 1
    pages = None
    raw_text_blocks = []
    try:
        import fitz
        import re
        doc_pdf = fitz.open(str(file_path))
        pages = len(doc_pdf)
        for i, page in enumerate(doc_pdf):
            page_text = page.get_text()
            # Clean Thai spacing and split sara-am characters
            cleaned_page_text = re.sub(r'([ก-ฮ][่้๊๋]?)\s+า', r'\1ำ', page_text)
            raw_text_blocks.append(f"# Page {i+1}\n{cleaned_page_text}")
        doc_pdf.close()
    except Exception as parse_err:
        logger.error("Error parsing raw text on upload: %s", parse_err)
        raw_text_blocks = ["(ไม่สามารถถอดข้อความภาษาไทยได้)"]

    raw_text = "\n\n".join(raw_text_blocks)
    raw_text_path = UPLOADS_DIR / f"{filename}.raw.txt"
    with open(str(raw_text_path), "w", encoding="utf-8") as f:
        f.write(raw_text)

    # Check if already exists
    existing_result = await db.execute(select(Document).where(Document.filename == filename))
    existing = existing_result.scalar_one_or_none()

    if existing:
        existing.status = "Step_Raw_Text"
        existing.size = file_size
        existing.pages = pages
        existing.exclude_pages = exclude_pages
        existing.display_name = display_name
        existing.uploaded_by = current_user.display_name or current_user.username
        existing.uploaded_by_id = current_user.id
        doc_entry = existing
    else:
        doc_entry = Document(
            filename=filename,
            display_name=display_name,
            status="Step_Raw_Text",
            pages=pages,
            size=file_size,
            exclude_pages=exclude_pages,
            uploaded_by=current_user.display_name or current_user.username,
            uploaded_by_id=current_user.id
        )
        db.add(doc_entry)

    await db.commit()
    await db.refresh(doc_entry)

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
    _check_doc_ownership(doc, current_user)

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
    _check_doc_ownership(doc, current_user)

    file_path = safe_path(UPLOADS_DIR, filename)
    if file_path.exists():
        file_path.unlink()

    # Delete associated workflow files
    for ext in [".raw.txt", ".cleaned.md", ".chunks.json"]:
        assoc_file = safe_path(UPLOADS_DIR, f"{filename}{ext}")
        if assoc_file.exists():
            assoc_file.unlink()

    await db.delete(doc)
    await db.commit()

    background_tasks.add_task(_delete_from_search_index, filename)


class ToggleDocumentRequest(BaseModel):
    filename: str
    active: bool


class DeleteDocumentRequest(BaseModel):
    filename: str


class UpdateExcludeRequest(BaseModel):
    filename: str
    exclude_pages: List[int]


@router.post("/documents/toggle")
async def toggle_document(
    payload: ToggleDocumentRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    filename = payload.filename
    active = payload.active

    result = await db.execute(select(Document).where(Document.filename == filename))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="ไม่พบเอกสารนี้")
    _check_doc_ownership(doc, current_user)

    doc.status = "Active" if active else "Inactive"
    await db.commit()
    await db.refresh(doc)

    background_tasks.add_task(_trigger_rebuild_background)
    return {"success": True}


@router.post("/documents/delete")
async def delete_document_post(
    payload: DeleteDocumentRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    filename = payload.filename

    result = await db.execute(select(Document).where(Document.filename == filename))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="ไม่พบเอกสารนี้")
    _check_doc_ownership(doc, current_user)

    file_path = safe_path(UPLOADS_DIR, filename)
    if file_path.exists():
        file_path.unlink()

    # Delete associated workflow files
    for ext in [".raw.txt", ".cleaned.md", ".chunks.json"]:
        assoc_file = safe_path(UPLOADS_DIR, f"{filename}{ext}")
        if assoc_file.exists():
            assoc_file.unlink()

    await db.delete(doc)
    await db.commit()

    background_tasks.add_task(_delete_from_search_index, filename)
    return {"success": True}


@router.post("/documents/update_exclude")
async def update_exclude_pages(
    payload: UpdateExcludeRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    filename = payload.filename
    exclude_pages = payload.exclude_pages

    result = await db.execute(select(Document).where(Document.filename == filename))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="ไม่พบเอกสารนี้")
    _check_doc_ownership(doc, current_user)

    doc.exclude_pages = ",".join(map(str, exclude_pages))
    await db.commit()
    await db.refresh(doc)

    background_tasks.add_task(_trigger_rebuild_background)
    return {"success": True}


class UpdateDocDetailsRequest(BaseModel):
    filename: str
    display_name: str


@router.post("/documents/update_details")
async def update_document_details(
    payload: UpdateDocDetailsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """แก้ไขชื่อแสดงผล (display_name) ของเอกสาร — เรียกจากหน้าต่างแก้ไขรายละเอียดเอกสารใน AdminWeb"""
    result = await db.execute(select(Document).where(Document.filename == payload.filename))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="ไม่พบเอกสารนี้")
    _check_doc_ownership(doc, current_user)

    doc.display_name = payload.display_name.strip() or doc.filename
    await db.commit()
    await db.refresh(doc)
    return {"success": True}


class ApproveRequest(BaseModel):
    filename: str
    current_status: str


class UpdateContentRequest(BaseModel):
    filename: str
    type: str
    content: Union[str, List[Any]]


@router.post("/documents/approve")
async def approve_document(
    payload: ApproveRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    filename = payload.filename
    current_status = payload.current_status

    result = await db.execute(select(Document).where(Document.filename == filename))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="ไม่พบเอกสารนี้ในระบบ")
    _check_doc_ownership(doc, current_user)

    exclude_pages = _parse_exclude_pages(doc.exclude_pages)
    new_status = run_approval_pipeline(filename, current_status, exclude_pages)

    if current_status == "Step_Chunk_Preview":
        background_tasks.add_task(_trigger_rebuild_background)

    doc.status = new_status
    await db.commit()
    await db.refresh(doc)

    return {"success": True, "new_status": new_status}


@router.get("/documents/view_raw")
async def view_raw_document(
    filename: str,
    current_user: User = Depends(get_current_user)
):
    filepath = safe_path(UPLOADS_DIR, f"{safe_filename(filename)}.raw.txt")
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="ไม่พบไฟล์ข้อความดิบ")

    with open(str(filepath), "r", encoding="utf-8") as f:
        content = f.read()
    return {"filename": filename, "content": content}


@router.get("/documents/view_cleaned")
async def view_cleaned_document(
    filename: str,
    current_user: User = Depends(get_current_user)
):
    filepath = safe_path(UPLOADS_DIR, f"{safe_filename(filename)}.cleaned.md")
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="ไม่พบไฟล์ข้อความที่เคลียร์แล้ว")

    with open(str(filepath), "r", encoding="utf-8") as f:
        content = f.read()
    return {"filename": filename, "content": content}


@router.get("/documents/view_chunks")
async def view_chunks_document(
    filename: str,
    current_user: User = Depends(get_current_user)
):
    filepath = safe_path(UPLOADS_DIR, f"{safe_filename(filename)}.chunks.json")
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="ไม่พบไฟล์พรีวิวแบ่ง Chunk")

    try:
        with open(str(filepath), "r", encoding="utf-8") as f:
            chunks = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ไม่สามารถโหลดไฟล์ Chunks ได้: {e}")
    return {"filename": filename, "chunks": chunks}


@router.post("/documents/update_content")
async def update_content_document(
    payload: UpdateContentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    filename = payload.filename
    content_type = payload.type
    content = payload.content

    result = await db.execute(select(Document).where(Document.filename == filename))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="ไม่พบเอกสารนี้")
    _check_doc_ownership(doc, current_user)

    safe_name = safe_filename(filename)
    if content_type == "raw":
        if not isinstance(content, str):
            raise HTTPException(status_code=400, detail="Content สำหรับข้อความดิบต้องเป็น string")
        filepath = safe_path(UPLOADS_DIR, f"{safe_name}.raw.txt")
        with open(str(filepath), "w", encoding="utf-8") as f:
            f.write(content)
    elif content_type == "cleaned":
        if not isinstance(content, str):
            raise HTTPException(status_code=400, detail="Content สำหรับข้อความเคลียร์ต้องเป็น string")
        filepath = safe_path(UPLOADS_DIR, f"{safe_name}.cleaned.md")
        with open(str(filepath), "w", encoding="utf-8") as f:
            f.write(content)
    elif content_type == "chunks":
        if not isinstance(content, list):
            raise HTTPException(status_code=400, detail="Content สำหรับ Chunk ต้องเป็น list")
        filepath = safe_path(UPLOADS_DIR, f"{safe_name}.chunks.json")
        with open(str(filepath), "w", encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False, indent=2)
    else:
        raise HTTPException(status_code=400, detail=f"ประเภทเนื้อหาไม่ถูกต้อง: {content_type}")

    return {"success": True}
