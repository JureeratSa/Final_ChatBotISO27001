"""แบบฟอร์มดาวน์โหลด — ตัดเฉพาะหน้าที่ต้องการออกจาก PDF ที่อัปโหลด"""
from pathlib import Path
from typing import List

import fitz  # PyMuPDF


def parse_pages(page_str: str, total_pages: int) -> List[int]:
    """"1,3,5" / "2-5" / "1-3,7" → เลขหน้าแบบเริ่มที่ 0 เรียงจากน้อยไปมาก (ข้ามหน้าที่ไม่มีอยู่จริง)"""
    pages = set()
    for part in page_str.replace(" ", "").split(","):
        try:
            if "-" in part:
                start, end = part.split("-", 1)
                candidates = range(int(start) - 1, int(end))
            elif part:
                candidates = [int(part) - 1]
            else:
                continue
        except ValueError:
            continue
        pages.update(p for p in candidates if 0 <= p < total_pages)
    return sorted(pages)


def extract_pdf_pages(src: Path, dest: Path, page_spec: str) -> bool:
    """บันทึกเฉพาะหน้าตาม page_spec จาก src ลง dest — คืน False ถ้าไม่มีหน้าที่ระบุอยู่ในไฟล์เลย"""
    with fitz.open(str(src)) as src_doc:
        indices = parse_pages(page_spec, len(src_doc))
        if not indices:
            return False
        with fitz.open() as new_doc:
            for i in indices:
                new_doc.insert_pdf(src_doc, from_page=i, to_page=i)
            new_doc.save(str(dest))
    return True


def page_count(path: Path) -> int:
    with fitz.open(str(path)) as doc:
        return len(doc)
