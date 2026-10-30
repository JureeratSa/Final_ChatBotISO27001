"""
TUH Chatbot AI — ไฮไลท์ส่วนที่ใช้ตอบลงใน PDF ก่อนส่งให้เบราว์เซอร์
ทำหน้าที่: เมื่อผู้ใช้กดแหล่งอ้างอิง ลิงก์จะมี ?hl=<chunk_id,...> ต่อท้าย (ดู build_citations)
endpoint /api/documents/serve จะเรียก highlight_pdf() เพื่อวาดไฮไลท์สีฟ้าอ่อนทับข้อความของ chunk
เหล่านั้นในสำเนา PDF ที่อยู่ในหน่วยความจำ — ไฟล์ต้นฉบับบนดิสก์ไม่ถูกแก้
ข้อความ chunk มาจาก BM25 index ของ HybridRetriever (ข้อความเดียวกับที่ส่งให้ LLM) และถูกสกัดจาก PDF
ด้วย PyMuPDF ตั้งแต่ตอนสร้างดัชนี จึงค้นเจอในหน้า PDF ได้ตรงแทบทุกบรรทัด
"""
import re
from typing import Dict, List

import fitz  # PyMuPDF

from app.services.rag_service import get_retriever

HIGHLIGHT_RGB = (0.68, 0.85, 1.0)  # ฟ้าอ่อน
MAX_CHUNKS = 10                     # กันลิงก์ที่ใส่ chunk มาเยอะผิดปกติ
MIN_LINE_LEN = 6                    # บรรทัดสั้นกว่านี้ (เช่น "3.5") ไปตรงกับที่อื่นในหน้าได้ง่าย ข้ามไป


def parse_chunk_ids(hl: str) -> List[int]:
    """แปลง "125,80" → [125, 80] (ไม่ซ้ำ ไม่เกิน MAX_CHUNKS) — ค่าที่ไม่ใช่ตัวเลขถูกทิ้ง"""
    ids: List[int] = []
    for part in re.findall(r"\d+", hl or ""):
        n = int(part)
        if n not in ids:
            ids.append(n)
    return ids[:MAX_CHUNKS]


def find_chunks(filename: str, chunk_ids: List[int]) -> List[Dict]:
    """คืนเฉพาะ chunk ที่มีเลขตรงและเป็นของเอกสาร filename จริง (กันการขอข้อความของเอกสารอื่น)"""
    retriever = get_retriever()
    chunks = getattr(retriever, "bm25_chunks", None) or []
    wanted = set(chunk_ids)
    return [
        c for c in chunks
        if c.get("chunk_id") in wanted and (c.get("metadata") or {}).get("source") == filename
    ]


def _pdf_ocr():
    """โมดูล Admin/pdf_ocr.py (OCR cache + จับคู่บรรทัดหน้าสแกน)"""
    import sys
    from pathlib import Path
    from app.core.config import settings
    admin_parent = str(Path(settings.ADMIN_DIR).parent)
    if admin_parent not in sys.path:
        sys.path.insert(0, admin_parent)
    from Admin import pdf_ocr
    return pdf_ocr


def _load_scanned_lines(pdf_path: str) -> Dict[int, List[Dict]]:
    try:
        return _pdf_ocr().load_page_lines(pdf_path)
    except Exception:
        return {}


def match_scanned_lines(chunk_text: str, lines: List[Dict]) -> List[List[float]]:
    if not lines:
        return []
    try:
        return _pdf_ocr().match_lines(chunk_text, lines)
    except ImportError:  # ไม่มี rapidfuzz — ไม่ไฮไลท์ แต่ยังเปิด PDF ได้ตามปกติ
        return []


def highlight_pdf(pdf_path: str, chunks: List[Dict]) -> bytes:
    """เปิด PDF แล้ววาด highlight annotation ทับทุกบรรทัดของแต่ละ chunk คืนเป็น bytes
    chunk หนึ่งอาจยาวข้ามไปหน้าถัดไป จึงไล่หาจากหน้าที่ระบุใน metadata ต่อไปอีก 1 หน้า"""
    doc = fitz.open(pdf_path)
    # เก็บ Page object ไว้ตลอด — doc[n] สร้าง object ใหม่ทุกครั้ง ถ้าไม่ถือไว้ annotation จะหลุดจากหน้า
    # ก่อน update() ("annotation not bound to any page")
    page_objs: Dict[int, "fitz.Page"] = {}
    scanned_lines = None  # ตำแหน่งบรรทัดของหน้าสแกน (โหลดจาก OCR cache เมื่อต้องใช้ครั้งแรก)
    try:
        for chunk in chunks:
            meta = chunk.get("metadata") or {}
            try:
                start = int(meta.get("page") or 1) - 1
            except (TypeError, ValueError):
                start = 0
            pages = [p for p in (start, start + 1) if 0 <= p < doc.page_count]

            if meta.get("is_scanned"):
                # หน้าสแกนไม่มีชั้นข้อความให้ search_for — ใช้กรอบบรรทัดจาก Tesseract ที่จับคู่กับเนื้อหา chunk
                if scanned_lines is None:
                    scanned_lines = _load_scanned_lines(pdf_path)
                for pno in pages:
                    rects = match_scanned_lines(chunk.get("content") or "", scanned_lines.get(pno + 1, []))
                    if rects:
                        page = page_objs.setdefault(pno, doc[pno])
                        # กรอบจาก Tesseract อยู่ในพิกัดภาพที่เรนเดอร์แล้ว (หมุนตาม /Rotate) แต่ annotation ใช้พิกัด
                        # หน้าก่อนหมุน — หน้าที่สแกนแนวนอนแล้วตั้ง rotation 90/270 ไว้ ถ้าไม่แปลงจะไฮไลท์เป็นแถบแนวตั้ง
                        # แปลงเป็น quad (ไม่ใช่ Rect) เพื่อให้ทิศของบรรทัดหมุนตามด้วย ไม่งั้นไฮไลท์ออกมาเป็นวงรี
                        to_page = page.derotation_matrix
                        for r in rects:
                            annot = page.add_highlight_annot(fitz.Rect(r).quad * to_page)
                            annot.set_colors(stroke=HIGHLIGHT_RGB)
                            annot.update()
                continue

            for line in (l.strip() for l in (chunk.get("content") or "").split("\n")):
                if len(line) < MIN_LINE_LEN:
                    continue
                for pno in pages:
                    page = page_objs.setdefault(pno, doc[pno])
                    rects = page.search_for(line)
                    if rects:
                        annot = page.add_highlight_annot(rects)
                        annot.set_colors(stroke=HIGHLIGHT_RGB)
                        annot.update()
                        break
        return doc.tobytes()
    finally:
        doc.close()
