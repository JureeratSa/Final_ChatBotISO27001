"""
ขั้นตอนอนุมัติเอกสาร — แอดมินกดอนุมัติทีละขั้น และตรวจ/แก้ผลของแต่ละขั้นได้ก่อนไปขั้นถัดไป

  Step_Raw_Text      ข้อความดิบจาก PDF            → <ไฟล์>.raw.txt   (สร้างตอนอัปโหลด)
  Step_Clean_Text    แปลงเลขไทย ตัดหน้าที่ละเว้น    → <ไฟล์>.cleaned.md
  Step_Chunk_Preview ตัวอย่างการแบ่ง chunk          → <ไฟล์>.chunks.json
  Active             บอทใช้ตอบได้ (rebuild ดัชนีเบื้องหลัง)
"""
import json
import re
from pathlib import Path
from typing import List, Optional

from fastapi import HTTPException

from app.core.config import settings
from app.core.security import safe_path
from app.models.models import Document, User
from app.rag.text_cleaning import replace_thai_numbers
from app.schemas.schemas import DocumentResponse
from app.services.audit_service import add_audit_detail
from app.services.department_scope import check_department
from app.utils.timeutil import thai_str

PAGE_MARKER = re.compile(r'(# Page \d+\n)')
# ไฟล์ประกอบของแต่ละเอกสารใน uploads/ (ลบตามเมื่อลบเอกสาร)
WORK_FILE_SUFFIXES = [".raw.txt", ".cleaned.md", ".chunks.json", ".ocr.json"]


def uploads_dir() -> Path:
    return Path(settings.UPLOADS_DIR)


def parse_exclude_pages(pages_str: Optional[str]) -> List[int]:
    """"3, 5,7" → [3, 5, 7]"""
    return [int(x.strip()) for x in (pages_str or "").split(",") if x.strip().isdigit()]


def doc_to_response(doc: Document) -> DocumentResponse:
    return DocumentResponse(
        filename=doc.filename,
        display_name=doc.display_name,
        status=doc.status,
        pages=doc.pages,
        size=doc.size,
        exclude_pages=parse_exclude_pages(doc.exclude_pages),
        chunking_duration=doc.chunking_duration,
        embedding_duration=doc.embedding_duration,
        upload_date=thai_str(doc.upload_date) or "",
        uploaded_by=doc.uploaded_by,
        department=doc.department,
    )


def check_doc_ownership(doc: Document, current_user: User) -> None:
    """เอกสารเป็นของ "แผนก" — แอดมินแผนกอื่นแก้ไม่ได้ (บันทึกลง audit log ว่าทำกับเอกสารไหนด้วย)"""
    add_audit_detail(document=doc.filename, document_name=doc.display_name, department=doc.department)
    check_department(doc.department, current_user, "คุณไม่มีสิทธิ์แก้ไขหรือดำเนินการกับเอกสารของแผนกอื่น")


def _split_pages(text: str):
    """แยกข้อความตาม "# Page N" → (ข้อความก่อนหน้าแรก, [(เลขหน้า, marker, เนื้อหา), ...])"""
    parts = PAGE_MARKER.split(text)
    pages = []
    for i in range(1, len(parts), 2):
        page_num = int(re.search(r'\d+', parts[i]).group())
        pages.append((page_num, parts[i], parts[i + 1] if i + 1 < len(parts) else ""))
    return parts[0], pages


def _read_work_file(filename: str, suffix: str, missing_detail: str) -> str:
    path = safe_path(uploads_dir(), f"{filename}{suffix}")
    if not path.exists():
        raise HTTPException(status_code=404, detail=missing_detail)
    return path.read_text(encoding="utf-8")


def _clean_text_step(filename: str, exclude_pages: List[int]) -> None:
    raw_text = _read_work_file(filename, ".raw.txt", "ไม่พบไฟล์ข้อความดิบสำหรับการคลีนคำ")
    text = replace_thai_numbers(raw_text)
    text = re.sub(r'([ก-ฮ][่้๊๋]?)\s+า', r'\1ำ', text)   # สระอำที่ PDF แยกเป็น "ํ า"

    header, pages = _split_pages(text)
    kept = [header] if header.strip() else []
    kept += [marker + content for page_num, marker, content in pages if page_num not in exclude_pages]
    safe_path(uploads_dir(), f"{filename}.cleaned.md").write_text("".join(kept), encoding="utf-8")


def _chunk_preview_step(filename: str) -> None:
    from langchain_text_splitters import RecursiveCharacterTextSplitter   # โหลดช้า — import ตอนใช้

    full_text = _read_work_file(filename, ".cleaned.md", "ไม่พบไฟล์ข้อความที่เคลียร์แล้วสำหรับแบ่ง Chunk")
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=400,
                                              separators=["\n\n", "\n", " "], add_start_index=True)
    header, pages = _split_pages(full_text)
    sections = [(1, header.strip())] if header.strip() else []
    sections += [(page_num, content) for page_num, _, content in pages if content.strip()]

    chunks = []
    for page_num, content in sections:
        for piece in splitter.create_documents([content]):
            chunks.append({
                "chunk_id": len(chunks) + 1,
                "content": piece.page_content.strip(),
                "metadata": {"source": filename, "page": page_num, "type": "text"},
            })
    safe_path(uploads_dir(), f"{filename}.chunks.json").write_text(
        json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")


def run_approval_pipeline(filename: str, current_status: str, exclude_pages: List[int]) -> str:
    """ทำขั้นถัดไปของเอกสาร แล้วคืนสถานะใหม่ (การสั่ง rebuild ตอนเข้า Active อยู่ที่ router)"""
    if current_status == "Step_Raw_Text":
        _clean_text_step(filename, exclude_pages)
        return "Step_Clean_Text"
    if current_status == "Step_Clean_Text":
        _chunk_preview_step(filename)
        return "Step_Chunk_Preview"
    if current_status == "Step_Chunk_Preview":
        return "Active"
    return current_status
