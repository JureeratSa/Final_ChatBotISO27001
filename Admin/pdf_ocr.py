"""
TUH Chatbot AI — ดึงข้อความจาก PDF ทีละหน้า พร้อม OCR หน้าที่เป็นภาพสแกน
ใช้ร่วมกันทั้งตอนอัปโหลดเอกสาร (Backend/app/routers/admin_documents.py) ตอน rebuild ดัชนี
(Admin/rebuild_db.py) และตอนไฮไลท์อ้างอิง (Backend/app/services/pdf_highlight.py)
ตามแนวทางในเอกสาร "สรุป-OCR-TUH-Chatbot":

1. ดึงข้อความด้วย get_text() ของ PyMuPDF ทีละหน้า
2. หน้าที่แทบไม่มีข้อความ (น้อยกว่า MIN_TEXT_CHARS ตัว) ถือเป็นหน้าสแกน → ส่งภาพหน้านั้นให้
   Typhoon OCR 1.5 บน GDCC (รูปแบบ OpenAI /chat/completions) อ่านเป็นข้อความ
3. Typhoon ไม่บอกตำแหน่งคำ จึงใช้ Tesseract (ภาษาไทย) หาตำแหน่งแต่ละบรรทัดบนหน้าสแกนเพิ่ม
   เพื่อให้ไฮไลท์อ้างอิงได้ (จับคู่บรรทัดกับข้อความ chunk ด้วย rapidfuzz ตอนไฮไลท์)
4. ผลทั้งหมดเก็บเป็น cache ข้างไฟล์ PDF (<ชื่อไฟล์>.ocr.json) ผูกกับขนาดและเวลาแก้ไขของไฟล์
   อัปโหลดครั้งเดียว OCR ครั้งเดียว rebuild/ไฮไลท์รอบต่อๆ ไปไม่ต้องเรียกซ้ำ

หน้า PDF ที่มีข้อความอยู่แล้วได้ผลเหมือนเดิมทุกตัวอักษร — OCR ทำงานเฉพาะหน้าสแกนเท่านั้น
ค่าตั้งอ่านจาก env หรือ Backend/.env:
  TYPHOON_OCR_URL / TYPHOON_OCR_API_KEY / TYPHOON_OCR_MODEL — ไม่ตั้ง = หน้าสแกนไม่มีข้อความ
  TESSERACT_CMD — path ของ tesseract.exe (ไม่ตั้ง = หาใน PATH) ไม่มี = หน้าสแกนไม่มีไฮไลท์
ส่วนไหนใช้ไม่ได้หรือเรียกไม่สำเร็จ จะข้ามไปเงียบๆ พร้อม log (ไม่ทำให้อัปโหลด/rebuild ล้ม)
"""
import base64
import html
import json
import logging
import os
import re
import shutil
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Iterable, List, Optional

import fitz

logger = logging.getLogger(__name__)

# หน้าที่มีข้อความน้อยกว่านี้ถือเป็นหน้าสแกน (บางหน้าสแกนมีแค่เลขหน้า/ตราประทับเป็นข้อความ)
MIN_TEXT_CHARS = 20
OCR_DPI = 150            # ทดสอบกับเอกสารจริงแล้วอ่านภาษาไทยได้ครบ ภาพ ~550KB ต่อหน้า
LINES_DPI = 200          # ความละเอียดที่ให้ Tesseract หาตำแหน่งบรรทัด (~1.5 วินาทีต่อหน้า)
OCR_WORKERS = 4          # จำนวนหน้าที่ทำพร้อมกัน (Typhoon ~2.7 วินาทีต่อหน้า)
OCR_TIMEOUT = 180
CACHE_VERSION = 1

# prompt มาตรฐานของ Typhoon OCR 1.5 (โมเดลถูกฝึกมากับ prompt นี้)
OCR_PROMPT = """Extract all text from the image.

Instructions:
- Only return the clean Markdown.
- Do not include any explanation or extra text.
- You must include all information on the page.

Formatting Rules:
- Tables: Render tables using <table>...</table> in clean HTML format.
- Equations: Render equations using LaTeX syntax with inline ($...$) and block ($$...$$).
- Images/Charts/Diagrams: Wrap any clearly defined visual areas (e.g., charts, diagrams, pictures) in:

<figure>
Describe the image's main elements (people, objects, text), note any contextual clues (place, event, culture), mention visible text and its meaning, provide deeper analysis when relevant (especially for financial charts, graphs, or documents), comment on style or architecture if relevant, then give a concise overall summary. Describe in Thai.
</figure>

- Page Numbers: Wrap page numbers in <page_number>...</page_number> (e.g., <page_number>14</page_number>).
- Checkboxes: Use ☐ for unchecked and ☑ for checked boxes."""


def _env_values(keys) -> Dict[str, Optional[str]]:
    """อ่านค่าจาก env ก่อน ถ้าไม่มีอ่านจาก Backend/.env (แบบเดียวกับ emb.resolve_chroma_dir)"""
    vals = {k: os.getenv(k) for k in keys}
    if not all(vals.values()):
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Backend", ".env")
        if os.path.exists(env_file):
            try:
                from dotenv import dotenv_values
                file_vals = dotenv_values(env_file)
                vals = {k: vals[k] or file_vals.get(k) for k in keys}
            except ImportError:
                pass
    return vals


def _ocr_config() -> Optional[Dict[str, str]]:
    cfg = _env_values(("TYPHOON_OCR_URL", "TYPHOON_OCR_API_KEY", "TYPHOON_OCR_MODEL"))
    return cfg if all(cfg.values()) else None


def _tesseract_cmd() -> Optional[str]:
    """path ของ tesseract ที่มีภาษาไทย หรือ None ถ้าไม่ได้ติดตั้ง/ไม่มี pytesseract"""
    try:
        import pytesseract  # noqa: F401
        import rapidfuzz  # noqa: F401
    except ImportError:
        return None
    cmd = _env_values(("TESSERACT_CMD",))["TESSERACT_CMD"] or shutil.which("tesseract")
    return cmd if cmd and os.path.exists(cmd) else None


def fix_sara_am(text: str) -> str:
    """รวม "ํ า" ที่ PyMuPDF แยกออกจากกันกลับเป็น "ำ" (ใช้กับข้อความที่ดึงจาก PDF เท่านั้น ไม่ใช้กับผล OCR)"""
    return re.sub(r'([ก-ฮ][่้๊๋]?)\s+า', r'\1ำ', text)


def _html_table_to_pipes(table_html: str) -> str:
    """แปลง <table> จาก OCR เป็นแถว "| a | b |" เพื่อให้ parse_blocks ใน rebuild_db มองเป็นตาราง"""
    rows = []
    for row_html in re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, flags=re.S | re.I):
        cells = re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>', row_html, flags=re.S | re.I)
        cells = [html.unescape(re.sub(r'<[^>]+>', ' ', c)).replace('|', '/').split() for c in cells]
        rows.append("| " + " | ".join(" ".join(c) for c in cells) + " |")
    return "\n".join(rows)


def clean_ocr_markdown(text: str) -> str:
    """ทำผล OCR ให้เป็นข้อความล้วนสำหรับ chunk:
    - ตัดเลขหน้า (<page_number>) เพราะไม่ใช่เนื้อหา
    - ตัดคำบรรยายภาพ (<figure>) ที่โมเดลแต่งขึ้นเอง เพื่อไม่ให้บอทตอบจากสิ่งที่ไม่ได้เขียนในเอกสาร
    - แปลงตาราง HTML เป็นแถวแบบ | และลบ tag ที่เหลือ"""
    text = re.sub(r'<page_number>.*?</page_number>', '', text, flags=re.S | re.I)
    text = re.sub(r'<figure>.*?</figure>', '', text, flags=re.S | re.I)
    text = re.sub(r'<table[^>]*>.*?</table>', lambda m: "\n" + _html_table_to_pipes(m.group(0)) + "\n",
                  text, flags=re.S | re.I)
    text = re.sub(r'</?(?:br|p|div|span|b|i|u|strong|em)[^>]*>', '\n', text, flags=re.I)
    text = html.unescape(text)
    return re.sub(r'\n{3,}', '\n\n', text).strip()


def ocr_page_image(png_bytes: bytes, cfg: Dict[str, str]) -> str:
    """ส่งภาพ 1 หน้าให้ Typhoon OCR แล้วคืนข้อความที่ทำความสะอาดแล้ว"""
    import httpx
    body = {
        "model": cfg["TYPHOON_OCR_MODEL"],
        "temperature": 0.1,
        "top_p": 0.6,
        "max_tokens": 8000,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": OCR_PROMPT},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(png_bytes).decode()}},
        ]}],
    }
    resp = httpx.post(
        cfg["TYPHOON_OCR_URL"].rstrip("/") + "/chat/completions",
        json=body,
        headers={"Authorization": f"Bearer {cfg['TYPHOON_OCR_API_KEY']}"},
        timeout=OCR_TIMEOUT,
    )
    resp.raise_for_status()
    return clean_ocr_markdown(resp.json()["choices"][0]["message"]["content"] or "")


def ocr_page_lines(png_bytes: bytes, dpi: int, cmd: str) -> List[Dict]:
    """หาตำแหน่งแต่ละบรรทัดบนภาพหน้าสแกนด้วย Tesseract (tha+eng)
    คืน [{"t": ข้อความบรรทัด, "r": [x0, y0, x1, y1] เป็นหน่วย point ของหน้า PDF}]"""
    import io
    import pytesseract
    from PIL import Image

    pytesseract.pytesseract.tesseract_cmd = cmd
    data = pytesseract.image_to_data(Image.open(io.BytesIO(png_bytes)), lang="tha+eng",
                                     output_type=pytesseract.Output.DICT)
    scale = 72.0 / dpi
    lines: Dict[tuple, Dict] = {}
    for i, word in enumerate(data["text"]):
        if not word.strip():
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        x0, y0 = data["left"][i], data["top"][i]
        x1, y1 = x0 + data["width"][i], y0 + data["height"][i]
        line = lines.setdefault(key, {"t": "", "r": [x0, y0, x1, y1]})
        line["t"] += word
        r = line["r"]
        line["r"] = [min(r[0], x0), min(r[1], y0), max(r[2], x1), max(r[3], y1)]
    return [{"t": l["t"], "r": [round(v * scale, 1) for v in l["r"]]} for l in lines.values()]


def _cache_path(pdf_path: str) -> str:
    return pdf_path + ".ocr.json"


def _stamp(pdf_path: str) -> Dict:
    st = os.stat(pdf_path)
    return {"v": CACHE_VERSION, "size": st.st_size, "mtime": int(st.st_mtime)}


def _load_cache(pdf_path: str, stamp: Dict) -> Dict:
    try:
        with open(_cache_path(pdf_path), "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("stamp") == stamp:
            return {"pages": data.get("pages", {}), "lines": data.get("lines", {})}
    except (OSError, ValueError):
        pass
    return {"pages": {}, "lines": {}}


def _save_cache(pdf_path: str, stamp: Dict, cache: Dict) -> None:
    try:
        with open(_cache_path(pdf_path), "w", encoding="utf-8") as f:
            json.dump({"stamp": stamp, **cache}, f, ensure_ascii=False, indent=1)
    except OSError as e:
        logger.warning("บันทึก OCR cache ไม่สำเร็จ %s: %s", pdf_path, e)


def load_page_lines(pdf_path: str) -> Dict[int, List[Dict]]:
    """ตำแหน่งบรรทัดของหน้าสแกนจาก cache (ใช้ตอนไฮไลท์) — {} ถ้าไม่มีหรือ cache ไม่ตรงกับไฟล์"""
    try:
        lines = _load_cache(pdf_path, _stamp(pdf_path))["lines"]
    except OSError:
        return {}
    return {int(p): v for p, v in lines.items()}


def extract_pages(pdf_path: str, skip_pages: Iterable[int] = ()) -> List[Dict]:
    """คืนข้อความทุกหน้า [{"page": เลขหน้าเริ่ม 1, "text": str, "is_scanned": bool}]
    skip_pages: หน้าที่ไม่ต้อง OCR (เช่นหน้าที่แอดมินละเว้น) — ยังคืนรายการของหน้านั้นแต่ไม่เสียเวลา OCR"""
    skip = {int(p) for p in skip_pages}
    stamp = _stamp(pdf_path)

    results: List[Dict] = []
    scanned: List[int] = []
    with fitz.open(pdf_path) as doc:
        for i, page in enumerate(doc, start=1):
            text = fix_sara_am(page.get_text())
            is_scanned = len(text.strip()) < MIN_TEXT_CHARS
            results.append({"page": i, "text": text, "is_scanned": is_scanned})
            if is_scanned and i not in skip:
                scanned.append(i)

        if not scanned:
            return results

        cache = _load_cache(pdf_path, stamp)
        name = os.path.basename(pdf_path)
        text_todo = [p for p in scanned if str(p) not in cache["pages"]]
        lines_todo = [p for p in scanned if str(p) not in cache["lines"]]
        cfg = _ocr_config() if text_todo else None
        if text_todo and not cfg:
            logger.warning("พบหน้าสแกน %d หน้าใน %s แต่ยังไม่ได้ตั้งค่า TYPHOON_OCR_* — ข้ามการ OCR", len(text_todo), name)
            text_todo = []
        tess = _tesseract_cmd() if lines_todo else None
        if lines_todo and not tess:
            logger.warning("ไม่พบ Tesseract/pytesseract — หน้าสแกนใน %s จะไม่มีไฮไลท์อ้างอิง", name)
            lines_todo = []
        text_imgs = {p: doc[p - 1].get_pixmap(dpi=OCR_DPI).tobytes("png") for p in text_todo}
        line_imgs = {p: doc[p - 1].get_pixmap(dpi=LINES_DPI).tobytes("png") for p in lines_todo}

    jobs = [("pages", p) for p in text_todo] + [("lines", p) for p in lines_todo]
    if jobs:
        def _run(job):
            kind, p = job
            try:
                if kind == "pages":
                    return kind, p, ocr_page_image(text_imgs[p], cfg)
                return kind, p, ocr_page_lines(line_imgs[p], LINES_DPI, tess)
            except Exception as e:  # หน้าไหนทำไม่สำเร็จ ข้ามไป แล้วลองใหม่รอบหน้า (ไม่ลง cache)
                logger.error("OCR (%s) หน้า %d ของ %s ไม่สำเร็จ: %s", kind, p, name, e)
                return kind, p, None

        with ThreadPoolExecutor(max_workers=OCR_WORKERS) as pool:
            for kind, p, value in pool.map(_run, jobs):
                if value is not None:
                    cache[kind][str(p)] = value
        _save_cache(pdf_path, stamp, cache)

    for r in results:
        if r["is_scanned"] and str(r["page"]) in cache["pages"]:
            r["text"] = cache["pages"][str(r["page"])]
    return results


def _norm(s: str) -> str:
    """ตัดช่องว่างและเครื่องหมาย markdown ทิ้งก่อนเทียบ (Tesseract กับ Typhoon เว้นวรรคไม่เหมือนกัน)"""
    return re.sub(r'[\s\*\#\|\-•·]+', '', s)


MIN_MATCH_CHARS = 8      # บรรทัดสั้นกว่านี้ (เช่น "กางเกง") ไปตรงกับหลายที่ในหน้า ไม่ไฮไลท์
MATCH_SCORE = 85         # คะแนน rapidfuzz.partial_ratio ขั้นต่ำที่ถือว่าบรรทัดนั้นอยู่ใน chunk


def match_lines(chunk_text: str, lines: List[Dict]) -> List[List[float]]:
    """คืนกรอบของบรรทัด (จาก Tesseract) ที่เนื้อหาอยู่ใน chunk — เทียบทิศ "บรรทัดอยู่ใน chunk"
    เพราะ Typhoon มักรวมหลายบรรทัดของหน้ากระดาษเป็นย่อหน้าเดียว
    เอกสารมักมีบรรทัดซ้ำในหลายหัวข้อ (เช่น "สวมหมวกพยาบาลสีขาว") จึงเลือกเฉพาะชุดบรรทัดที่ตำแหน่งใน chunk
    เรียงตามลำดับบนหน้ากระดาษยาวที่สุด (longest non-decreasing subsequence) — บรรทัดซ้ำนอกช่วงจะหลุดไป"""
    from rapidfuzz import fuzz
    target = _norm(chunk_text)
    hits = []  # (ตำแหน่งในหน้า, ตำแหน่งที่เจอใน chunk, กรอบ)
    for line in sorted(lines, key=lambda l: (l["r"][1], l["r"][0])):
        t = _norm(line["t"])
        if len(t) < MIN_MATCH_CHARS:
            continue
        m = fuzz.partial_ratio_alignment(t, target)
        if m and m.score >= MATCH_SCORE:
            hits.append((m.dest_start, line["r"]))
    if not hits:
        return []
    # longest non-decreasing subsequence ของตำแหน่งใน chunk (จำนวนบรรทัดต่อหน้ามีไม่มาก O(n^2) พอ)
    best = [1] * len(hits)
    prev = [-1] * len(hits)
    for i in range(len(hits)):
        for j in range(i):
            if hits[j][0] <= hits[i][0] and best[j] + 1 > best[i]:
                best[i], prev[i] = best[j] + 1, j
    i = max(range(len(hits)), key=lambda k: best[k])
    keep = []
    while i != -1:
        keep.append(hits[i][1])
        i = prev[i]
    return keep[::-1]
