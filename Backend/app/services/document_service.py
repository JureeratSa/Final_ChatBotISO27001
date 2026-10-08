"""
TUH Chatbot AI — Documents Service
แยกจาก app/routers/admin_documents.py (เดิมอยู่ใน Backend/app/routers/admin.py) —
run_approval_pipeline() ที่ดึงเนื้อหาของ
approve_document ส่วน clean→chunk ออกมาเป็นฟังก์ชันแยก — การ trigger rebuild background
task (ตอนเข้าสถานะ Active) ยังอยู่ที่ router เพราะต้องใช้ BackgroundTasks ของ FastAPI)
"""
import json
from pathlib import Path
from typing import List, Optional

from fastapi import HTTPException

from app.core.config import settings
from app.core.security import safe_path
from app.models.models import Document, User
from app.schemas.schemas import DocumentResponse

UPLOADS_DIR = Path(settings.UPLOADS_DIR)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


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
        upload_date=doc.upload_date.strftime("%Y-%m-%d %H:%M:%S") if doc.upload_date else "",
        uploaded_by=doc.uploaded_by
    )


def _check_doc_ownership(doc: Document, current_user: User):
    if current_user.role == "System Administrator":
        return
    if doc.uploaded_by not in [current_user.username, current_user.display_name]:
        raise HTTPException(
            status_code=403,
            detail="คุณไม่มีสิทธิ์แก้ไขหรือดำเนินการกับเอกสารที่ผู้อื่นเป็นผู้อัปโหลด"
        )


def run_approval_pipeline(filename: str, current_status: str, exclude_pages: List[int]) -> str:
    """ประมวลผล 1 ขั้นของ pipeline อนุมัติเอกสาร (raw text -> clean -> chunk preview -> active)
    คืนค่า status ใหม่ที่ควรบันทึกลง DB — การ trigger rebuild background task (เมื่อเข้าสถานะ
    Active) เป็นหน้าที่ของ router เพราะต้องใช้ BackgroundTasks ของ FastAPI
    """
    new_status = current_status

    if current_status == "Step_Raw_Text":
        # Step 2: Clean the raw text
        raw_text_path = safe_path(UPLOADS_DIR, f"{filename}.raw.txt")
        if not raw_text_path.exists():
            raise HTTPException(status_code=404, detail="ไม่พบไฟล์ข้อความดิบสำหรับการคลีนคำ")

        with open(str(raw_text_path), "r", encoding="utf-8") as f:
            raw_text = f.read()

        # Import clean functions
        import sys
        import re
        admin_parent = str(Path(settings.ADMIN_DIR).parent)
        if admin_parent not in sys.path:
            sys.path.insert(0, admin_parent)

        from Admin.cleanData import replace_thai_numbers
        cleaned_text = replace_thai_numbers(raw_text)
        cleaned_text = re.sub(r'([ก-ฮ][่้๊๋]?)\s+า', r'\1ำ', cleaned_text)

        # Filter out excluded pages
        pages_blocks = re.split(r'(# Page \d+\n)', cleaned_text)
        reconstructed_blocks = []
        current_page_num = 1

        if pages_blocks[0].strip():
            reconstructed_blocks.append(pages_blocks[0])

        for idx in range(1, len(pages_blocks), 2):
            marker = pages_blocks[idx]
            content = pages_blocks[idx+1] if idx+1 < len(pages_blocks) else ""

            page_match = re.search(r'# Page (\d+)', marker)
            p_num = int(page_match.group(1)) if page_match else current_page_num

            if p_num not in exclude_pages:
                reconstructed_blocks.append(marker + content)
            current_page_num = p_num + 1

        cleaned_filtered_text = "".join(reconstructed_blocks)

        cleaned_path = safe_path(UPLOADS_DIR, f"{filename}.cleaned.md")
        with open(str(cleaned_path), "w", encoding="utf-8") as f:
            f.write(cleaned_filtered_text)

        new_status = "Step_Clean_Text"

    elif current_status == "Step_Clean_Text":
        # Step 3: Split cleaned text into chunks
        cleaned_path = safe_path(UPLOADS_DIR, f"{filename}.cleaned.md")
        if not cleaned_path.exists():
            raise HTTPException(status_code=404, detail="ไม่พบไฟล์ข้อความที่เคลียร์แล้วสำหรับแบ่ง Chunk")

        with open(str(cleaned_path), "r", encoding="utf-8") as f:
            full_text = f.read()

        from langchain_text_splitters import RecursiveCharacterTextSplitter
        import re

        pages_raw = re.split(r'(# Page \d+\n)', full_text)
        chunks = []
        chunk_id = 1
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=400,
            separators=["\n\n", "\n", " "],
            add_start_index=True
        )

        current_page_num = 1
        header_content = pages_raw[0].strip()
        if header_content:
            docs_split = splitter.create_documents([header_content])
            for doc_chunk in docs_split:
                chunks.append({
                    "chunk_id": chunk_id,
                    "content": doc_chunk.page_content.strip(),
                    "metadata": {
                        "source": filename,
                        "page": 1,
                        "type": "text"
                    }
                })
                chunk_id += 1

        for idx in range(1, len(pages_raw), 2):
            marker = pages_raw[idx]
            page_content = pages_raw[idx+1] if idx+1 < len(pages_raw) else ""

            page_match = re.search(r'# Page (\d+)', marker)
            page_num = int(page_match.group(1)) if page_match else current_page_num
            current_page_num = page_num

            if page_content.strip():
                docs_split = splitter.create_documents([page_content])
                for doc_chunk in docs_split:
                    chunks.append({
                        "chunk_id": chunk_id,
                        "content": doc_chunk.page_content.strip(),
                        "metadata": {
                            "source": filename,
                            "page": page_num,
                            "type": "text"
                        }
                    })
                    chunk_id += 1

        chunks_path = safe_path(UPLOADS_DIR, f"{filename}.chunks.json")
        with open(str(chunks_path), "w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)

        new_status = "Step_Chunk_Preview"

    elif current_status == "Step_Chunk_Preview":
        # Step 4: Go live / Active and Rebuild Vector
        new_status = "Active"

    return new_status
