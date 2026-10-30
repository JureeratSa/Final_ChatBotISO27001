"""
สร้างดัชนีค้นหาใหม่ทั้งคลังจาก PDF ที่สถานะ Active

ขั้นตอน (ต่อเอกสาร):
  1. ดึงข้อความทีละหน้า (หน้าสแกนใช้ OCR — rag/ocr.py) ข้ามหน้าที่แอดมินตั้งให้ละเว้น
  2. แบ่งเป็น chunk ~800 ตัวอักษร (ซ้อนกัน 200) — ตารางเก็บเป็น chunk เดียวพร้อมคำอธิบาย
  3. แปลงทุก chunk เป็นเวกเตอร์ด้วย bge-m3
  ผลของแต่ละเอกสารเก็บเป็น cache ใน uploads/cache — ไฟล์ไม่เปลี่ยนก็ไม่ต้องทำ embedding ใหม่
แล้วรวมทุกเอกสาร: บันทึกลง ChromaDB + สร้าง BM25 (index_db/bm25.pkl) + สำเนา chunk (sample_chunks.json)
"""
import json
import logging
import os
import pickle
import re
import time

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pythainlp.tokenize import sent_tokenize

from app.core.config import settings
from app.rag.ocr import extract_pages
from app.rag.retriever import COLLECTION_NAME, EMBEDDING_MODEL, tokenize

logger = logging.getLogger(__name__)

CHUNK_SIZE = 800
CHUNK_OVERLAP = 200
EMBED_BATCH = 16                 # encode ทีละชุด เพื่อรายงานความคืบหน้าได้
# ส่วนหนึ่งของชื่อไฟล์และเนื้อ cache — เปลี่ยนค่านี้ = cache เดิมทั้งหมดใช้ไม่ได้ ต้อง embedding ใหม่
CACHE_TECH = "local_chroma"


# ─── แบ่งข้อความเป็น chunk ─────────────────────────────────────────────────────

def parse_blocks(page_text):
    """แยกข้อความของหน้าเป็นบล็อก text / table (บรรทัดที่ขึ้นต้นด้วย | คือแถวของตาราง)
    จำหัวข้อล่าสุด (บรรทัด # ...) ไว้กับทุกบล็อก"""
    lines = page_text.split('\n')
    blocks = []
    current_lines = []
    in_table = False
    block_start = 0
    heading = ""

    for line_idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('#') and not re.match(r'^#\s+Page\s+\d+', stripped):
            heading = stripped

        if stripped.startswith('|'):
            if not in_table:
                if current_lines:
                    blocks.append({'type': 'text', 'lines': current_lines, 'start_line': block_start, 'heading': heading})
                    current_lines = []
                in_table = True
                block_start = line_idx
            current_lines.append('|'.join(cell.strip() for cell in line.split('|')))
        else:
            if in_table:
                if current_lines:
                    blocks.append({'type': 'table', 'lines': current_lines, 'start_line': block_start, 'heading': heading})
                    current_lines = []
                in_table = False
                block_start = line_idx
            current_lines.append(line)
    if current_lines:
        blocks.append({'type': 'table' if in_table else 'text', 'lines': current_lines,
                       'start_line': block_start, 'heading': heading})

    for block in blocks:
        block['content'] = '\n'.join(block['lines'])
    return blocks


def preprocess_thai_text(text):
    """จัดประโยคภาษาไทยในแต่ละย่อหน้าใหม่ (คั่นประโยคด้วยช่องว่างเดียว)"""
    if not text.strip():
        return text
    paragraphs = [p for p in text.split("\n\n") if p.strip()]
    return "\n\n".join(" ".join(sent_tokenize(p, engine="whitespace")) for p in paragraphs)


def describe_table(table_markdown, heading, page_num):
    """ประโยคสั้นๆ อธิบายตาราง (ช่วยให้ค้นเจอตารางจากชื่อหัวข้อ/ชื่อคอลัมน์)"""
    topic = f"เรื่อง '{heading}'" if heading else "ระเบียบสวัสดิการ"
    columns = ""
    for line in table_markdown.split('\n'):
        if '|' in line and not all(c in '|- ' for c in line.strip()):
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if cells:
                columns = " ประกอบด้วยข้อมูลคอลัมน์: " + ", ".join(cells)
                break
    return f"ตารางแสดงข้อมูลรายละเอียด{topic} (หน้า {page_num}){columns}"


def chunk_document_text(full_text, filename, start_chunk_id=1):
    """แบ่งข้อความทั้งเอกสาร (มีบรรทัด "# Page n" คั่นแต่ละหน้า) เป็น chunk — chunk ไม่ข้ามหน้า"""
    pages = re.split(r'(# Page \d+\n)', full_text)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", " "],  # ตัดตามย่อหน้า/บรรทัด/ช่องว่าง ไม่ตัดกลางคำ
        add_start_index=True,
    )
    chunks = []
    chunk_id = start_chunk_id

    def add(content, page, kind, **extra_meta):
        nonlocal chunk_id
        chunks.append({"chunk_id": chunk_id, "content": content,
                       "metadata": {"source": filename, "page": page, "type": kind, **extra_meta}})
        chunk_id += 1

    # ข้อความก่อน "# Page 1" (ถ้ามี) นับเป็นหน้า 1
    if pages[0].strip():
        for doc in splitter.create_documents([pages[0].strip()]):
            add(doc.page_content.strip(), 1, "text")

    page_num = 1
    for idx in range(1, len(pages), 2):
        match = re.search(r'# Page (\d+)', pages[idx])
        page_num = int(match.group(1)) if match else page_num
        page_text = pages[idx + 1] if idx + 1 < len(pages) else ""
        if not page_text.strip():
            continue

        for block in parse_blocks(page_text):
            if block['type'] == 'table':
                table = block['content']
                if block['heading']:
                    table = f"หัวข้ออ้างอิง: {block['heading']}\n{block['content']}"
                description = describe_table(block['content'], block['heading'], page_num)
                add(f"{description}\n\n{table}", page_num, "table", raw_table=table)
            elif block['content'].strip():
                for doc in splitter.create_documents([preprocess_thai_text(block['content'])]):
                    text = doc.page_content.strip()
                    if block['heading'] and block['heading'] not in text:
                        text = f"หมวดหมู่: {block['heading']}\n{text}"
                    add(text, page_num, "text")

    return chunks, chunk_id


# ─── สร้างดัชนี ─────────────────────────────────────────────────────────────────

def _cache_file(cache_dir, pdf):
    safe_name = re.sub(r'[^\w฀-๿\.\-]', '_', pdf)
    return os.path.join(cache_dir, f"{safe_name}_{CACHE_TECH}.json")


def _load_cache(path, file_size, file_mtime, exclude_pages):
    """cache ใช้ได้เมื่อไฟล์ PDF และหน้าที่ละเว้นไม่เปลี่ยนจากตอนสร้าง"""
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        logger.warning("อ่าน cache %s ไม่ได้: %s", path, e)
        return None
    same = (data.get("file_size") == file_size and data.get("file_mtime") == file_mtime
            and data.get("exclude_pages") == exclude_pages and data.get("embedding_tech") == CACHE_TECH)
    return data if same else None


def _document_text(pdf_path, exclude_pages):
    """ข้อความทั้งเอกสาร (คั่นหน้าด้วย "# Page n") + เลขหน้าที่ได้ข้อความจาก OCR"""
    pages = extract_pages(pdf_path, skip_pages=exclude_pages)
    scanned = {p["page"] for p in pages if p["is_scanned"]}
    text = "\n\n".join(f"# Page {i}\n{p['text']}" for i, p in enumerate(pages, start=1) if i not in exclude_pages)
    return text, scanned


def rebuild(documents, progress=None):
    """
    สร้างดัชนีใหม่ทั้งคลัง
    documents: [{"filename", "status", "exclude_pages": [int]}] จากฐานข้อมูล — ใช้เฉพาะ status Active
    progress:  callback(percent 0–100, ข้อความขั้นตอน) สำหรับแสดงในหน้าแอดมิน (ไม่บังคับ)
    คืน {filename: {"chunking_duration", "embedding_duration"}} ให้ผู้เรียกบันทึกลงฐานข้อมูล
    """
    started = time.perf_counter()

    def report(percent, stage):
        if progress:
            try:
                progress(percent, stage)
            except Exception:
                pass  # การรายงานความคืบหน้าห้ามทำให้ rebuild ล้ม

    uploads_dir = settings.UPLOADS_DIR
    cache_dir = os.path.join(uploads_dir, "cache")
    os.makedirs(cache_dir, exist_ok=True)

    active = {d["filename"]: d for d in documents if d.get("status") == "Active"}
    todo = [f for f in os.listdir(uploads_dir) if f.lower().endswith(".pdf") and f in active]
    logger.info("rebuild: %d เอกสาร Active", len(todo))

    per_document = []        # [{"chunks", "embeddings"}] ต่อเอกสาร
    durations = {}
    model = None
    done = 0

    # ความคืบหน้า: 0–80% ไล่ทีละเอกสาร, 80–90% บันทึก ChromaDB, 90–100% สร้าง BM25
    def doc_progress(fraction, stage):
        report(80 * (done + fraction) / max(1, len(todo)), stage)

    report(0, "กำลังเตรียมเอกสาร")
    for pdf in todo:
        pdf_path = os.path.join(uploads_dir, pdf)
        stat = os.stat(pdf_path)
        exclude_pages = sorted(int(p) for p in (active[pdf].get("exclude_pages") or []))
        cache_path = _cache_file(cache_dir, pdf)
        cached = _load_cache(cache_path, stat.st_size, int(stat.st_mtime), exclude_pages)

        if cached:
            chunks, embeddings = cached["chunks"], cached["embeddings"]
            chunking_duration = cached.get("chunking_duration", 0.0)
            embedding_duration = cached.get("embedding_duration", 0.0)
        else:
            doc_progress(0, f"กำลังสกัดข้อความ: {pdf}")
            t0 = time.perf_counter()
            text, scanned_pages = _document_text(pdf_path, exclude_pages)
            chunks, _ = chunk_document_text(text, pdf)
            for c in chunks:
                if c["metadata"]["page"] in scanned_pages:
                    c["metadata"]["is_scanned"] = True   # หน้าสแกนไฮไลท์ด้วยตำแหน่งจาก OCR (rag/highlight.py)
            chunking_duration = time.perf_counter() - t0
            if not chunks:
                logger.warning("ไม่มีข้อความใน %s", pdf)
                done += 1
                continue

            if model is None:
                from sentence_transformers import SentenceTransformer
                model = SentenceTransformer(EMBEDDING_MODEL)
            t0 = time.perf_counter()
            texts = [c["content"] for c in chunks]
            embeddings = []
            for start in range(0, len(texts), EMBED_BATCH):
                doc_progress(start / len(texts), f"กำลังทำ embedding: {pdf}")
                batch = model.encode(texts[start:start + EMBED_BATCH], show_progress_bar=False,
                                     convert_to_numpy=True, normalize_embeddings=True)
                embeddings.extend(batch.tolist())
            embedding_duration = time.perf_counter() - t0

            try:
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump({"filename": pdf, "file_size": stat.st_size, "file_mtime": int(stat.st_mtime),
                               "exclude_pages": exclude_pages, "embedding_tech": CACHE_TECH,
                               "chunks": chunks, "embeddings": embeddings,
                               "chunking_duration": chunking_duration, "embedding_duration": embedding_duration},
                              f, ensure_ascii=False, indent=2)
            except OSError as e:
                logger.warning("บันทึก cache %s ไม่สำเร็จ: %s", cache_path, e)

        per_document.append({"chunks": chunks, "embeddings": embeddings})
        durations[pdf] = {"chunking_duration": round(chunking_duration, 4),
                          "embedding_duration": round(embedding_duration, 4)}
        done += 1
        doc_progress(0, f"ทำ embedding เสร็จ: {pdf}")

    # รวมทุกเอกสารแล้วเรียง chunk_id ใหม่ 1..N
    all_chunks, all_embeddings = [], []
    for doc in per_document:
        for chunk, embedding in zip(doc["chunks"], doc["embeddings"]):
            all_chunks.append({**chunk, "chunk_id": len(all_chunks) + 1})
            all_embeddings.append(embedding)

    if not all_chunks:
        logger.warning("rebuild: ไม่มี chunk ให้สร้างดัชนี")
        return durations

    report(80, "กำลังบันทึกฐานข้อมูลเวกเตอร์ (ChromaDB)")
    import chromadb
    os.makedirs(settings.CHROMA_DIR, exist_ok=True)
    client = chromadb.PersistentClient(path=settings.CHROMA_DIR)
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass  # ยังไม่เคยมี collection
    client.create_collection(COLLECTION_NAME).add(
        ids=[str(c["chunk_id"]) for c in all_chunks],
        embeddings=all_embeddings,
        metadatas=[c["metadata"] for c in all_chunks],
        documents=[c["content"] for c in all_chunks],
    )

    report(90, "กำลังสร้างดัชนีคำสำคัญ (BM25)")
    with open(settings.CHUNKS_FILE, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)
    from rank_bm25 import BM25Okapi
    os.makedirs(settings.INDEX_DB_DIR, exist_ok=True)
    with open(os.path.join(settings.INDEX_DB_DIR, "bm25.pkl"), "wb") as f:
        pickle.dump({"bm25_index": BM25Okapi([tokenize(c["content"]) for c in all_chunks]),
                     "chunks": all_chunks}, f)

    report(100, "บันทึกดัชนีเสร็จ")
    logger.info("rebuild เสร็จ: %d chunk ใน %.1f วินาที", len(all_chunks), time.perf_counter() - started)
    return durations
