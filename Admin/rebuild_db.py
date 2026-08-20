import os
import re
import sys
import json
import fitz  
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pythainlp.tokenize import sent_tokenize

admin_dir = os.path.dirname(os.path.abspath(__file__)) # ปัจจุบันใช้ไฟล์พวกนี้เลย ไม่ได้ยุ่ง
root_dir = os.path.dirname(admin_dir) 
sys.path.append(root_dir)

# ฟังก์ชันย่อยสำหรับจัดการและแยกตารางออกจากข้อความธรรมดา

def parse_blocks(full_text):
    """แยก text , table ออกจากกัน (in block)"""
    lines = full_text.split('\n')
    blocks = []
    current_block_lines = []
    in_table = False
    current_block_start_line = 0
    
    current_heading = ""

    for line_idx, line in enumerate(lines):
        stripped_line = line.strip()
        
        # (hd)
        if stripped_line.startswith('#') and not re.match(r'^#\s+Page\s+\d+', stripped_line):
            current_heading = stripped_line

        # check table(T F)
        is_table_line = stripped_line.startswith('|')
        if is_table_line:
            if not in_table:
                if current_block_lines:
                    blocks.append({
                        'type': 'text',
                        'lines': current_block_lines,
                        'start_line': current_block_start_line,
                        'heading': current_heading
                    })
                    current_block_lines = []
                in_table = True
                current_block_start_line = line_idx
            cells = [cell.strip() for cell in line.split('|')]
            cleaned_line = '|'.join(cells)
            current_block_lines.append(cleaned_line)
        else:
            if in_table:
                if current_block_lines:
                    blocks.append({
                        'type': 'table',
                        'lines': current_block_lines,
                        'start_line': current_block_start_line,
                        'heading': current_heading
                    })
                    current_block_lines = []
                in_table = False
                current_block_start_line = line_idx
            current_block_lines.append(line)
    if current_block_lines:
        blocks.append({
            'type': 'table' if in_table else 'text',
            'lines': current_block_lines,
            'start_line': current_block_start_line,
            'heading': current_heading
        })

    # content
    line_offsets = []
    current_offset = 0
    for line in lines:
        line_offsets.append(current_offset)
        current_offset += len(line) + 1

    for block in blocks:
        start_line = block['start_line']
        block['start_offset'] = line_offsets[start_line]
        block['content'] = '\n'.join(block['lines'])

    return blocks

def preprocess_thai_text(text):
    """แยกและรวมประโยคภาษาไทยใหม่"""
    if not text.strip():
        return text
    paragraphs = text.split("\n\n")
    processed_paragraphs = []
    for para in paragraphs:
        if para.strip():
            sentences = sent_tokenize(para, engine="whitespace")
            processed_paragraphs.append(" ".join(sentences))
    return "\n\n".join(processed_paragraphs)

def generate_table_description(table_markdown, heading, page_num):
    """สร้างคำอธิบายสรุปหัวเรื่องตารางสั้นๆ"""
    heading_info = f"เรื่อง '{heading}'" if heading else "ระเบียบสวัสดิการ"
    lines = table_markdown.split('\n')
    columns_info = ""
    for line in lines:
        if '|' in line and not all(c in '|- ' for c in line.strip()):
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if cells:
                columns_info = " ประกอบด้วยข้อมูลคอลัมน์: " + ", ".join(cells)
                break
                
    desc = f"ตารางแสดงข้อมูลรายละเอียด{heading_info} (หน้า {page_num}){columns_info}"
    return desc

def extract_text_from_pdf(filepath):
    """แกะตัวหนังสือจากไฟล์ PDF ทีละหน้า"""
    pages_text = []
    doc = fitz.open(filepath)
    for page in doc:
        raw_text = page.get_text()
        # Clean Thai spacing and split sara-am characters
        cleaned_text = re.sub(r'([ก-ฮ][่้๊๋]?)\s+า', r'\1ำ', raw_text)
        pages_text.append(cleaned_text)
    doc.close()
    return pages_text

# Chunking

def chunk_document_text(full_text, filename, start_chunk_id=1):
    """ทำเป็นย่อย 1000 400"""
    # หน้าใหม่ chunk ใหม่
    pages_raw = re.split(r'(# Page \d+\n)', full_text)
    chunks = []
    chunk_id = start_chunk_id
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=200,
        separators=["\n\n", "\n", " "],  # เพื่อไม่ให้ตัดคำ
        add_start_index=True
    )
    
    current_page_num = 1
    
    # จัดการ Header หน้าแรกสุด
    header_content = pages_raw[0].strip()
    if header_content:
        docs = splitter.create_documents([header_content])
        for doc in docs:
            chunks.append({
                "chunk_id": chunk_id,
                "content": doc.page_content.strip(),
                "metadata": {
                    "source": filename,
                    "page": 1,
                    "type": "text"
                }
            })
            chunk_id += 1
            
    # วนลูปสลับระหว่างหน้าและเนื้อหา
    for idx in range(1, len(pages_raw), 2):
        marker = pages_raw[idx]
        page_content = pages_raw[idx+1] if idx+1 < len(pages_raw) else ""
        
        page_match = re.search(r'# Page (\d+)', marker)
        page_num = int(page_match.group(1)) if page_match else current_page_num
        current_page_num = page_num
        
        if not page_content.strip():
            continue
            
        blocks = parse_blocks(page_content)
        for block in blocks:
            if block['type'] == 'table':
                raw_table_with_heading = block['content']
                if block['heading']:
                    raw_table_with_heading = f"หัวข้ออ้างอิง: {block['heading']}\n{block['content']}"

                table_desc = generate_table_description(block['content'], block['heading'], page_num)
                
                chunks.append({
                    "chunk_id": chunk_id,
                    "content": f"{table_desc}\n\n{raw_table_with_heading}",
                    "metadata": {
                        "source": filename,
                        "page": page_num,
                        "type": "table",
                        "raw_table": raw_table_with_heading
                    }
                })
                chunk_id += 1
            else:
                if block['content'].strip():
                    preprocessed_content = preprocess_thai_text(block['content'])
                    docs = splitter.create_documents([preprocessed_content])
                    
                    for doc in docs:
                        chunk_text = doc.page_content.strip()
                        if block['heading'] and block['heading'] not in chunk_text:
                            chunk_text = f"หมวดหมู่: {block['heading']}\n{chunk_text}"

                        chunks.append({
                            "chunk_id": chunk_id,
                            "content": chunk_text,
                            "metadata": {
                                "source": filename,
                                "page": page_num,
                                "type": "text"
                            }
                        })
                        chunk_id += 1
                        
    return chunks, chunk_id

# เรียกทุก def มาใช้งาน

def rebuild():
    import time
    start_time = time.perf_counter()
    
    # 1. โหลดการตั้งค่าระบบ AI
    db_settings_path = os.path.join(root_dir, "user", "backend", "db", "db_settings.json")
    config = {}
    if os.path.exists(db_settings_path):
        try:
            with open(db_settings_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception:
            pass
            
    tech = config.get("embedding_tech", "local_faiss")
    api_key = config.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY")
    
    uploads_dir = os.path.join(root_dir, "uploads")
    cache_dir = os.path.join(uploads_dir, "cache")
    os.makedirs(cache_dir, exist_ok=True)
    
    if not os.path.exists(uploads_dir):
        print(f"Uploads directory not found: {uploads_dir}")
        return
        
    pdf_files = [f for f in os.listdir(uploads_dir) if f.lower().endswith(".pdf")]
    print(f"Found {len(pdf_files)} PDF documents on disk.")
    
    db_docs_path = os.path.join(root_dir, "user", "backend", "db", "db_documents.json")
    if os.path.exists(db_docs_path):
        with open(db_docs_path, "r", encoding="utf-8") as f:
            docs_db = json.load(f)
    else:
        docs_db = []
        
    active_filenames = {d["filename"] for d in docs_db if d.get("status", "Active") in ["Active", "Processing"]}
    if not docs_db:
        # ถ้าไม่มีข้อมูลเปิดใช้งาน ให้สแกนทำทั้งหมด
        active_filenames = set(pdf_files)
        
    combined_docs_data = []
    model = None
    
    for pdf in pdf_files:
        if pdf not in active_filenames:
            print(f"Skipping Inactive document: {pdf}")
            continue
            
        pdf_path = os.path.join(uploads_dir, pdf)
        if not os.path.exists(pdf_path):
            continue
            
        # ดึงสถิติของไฟล์
        stat_info = os.stat(pdf_path)
        file_size = stat_info.st_size
        file_mtime = int(stat_info.st_mtime)
        
        # ดึงการละเว้นหน้า
        doc_record = next((d for d in docs_db if d["filename"] == pdf), {})
        exclude_pages = doc_record.get("exclude_pages", [])
        
        # สร้างชื่อไฟล์ cache (กรองชื่อพิเศษให้ปลอดภัย)
        safe_name = re.sub(r'[^\w\u0e00-\u0e7f\.\-]', '_', pdf)
        cache_file = os.path.join(cache_dir, f"{safe_name}_{tech}.json")
        
        use_cache = False
        cached_data = None
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                if (cached_data.get("file_size") == file_size and 
                    cached_data.get("file_mtime") == file_mtime and 
                    cached_data.get("exclude_pages") == exclude_pages and
                    cached_data.get("embedding_tech") == tech):
                    use_cache = True
            except Exception as e:
                print(f"  Error reading cache file {cache_file}: {e}")
                
        if use_cache and cached_data is not None:
            print(f"-> ใช้ข้อมูลและเวกเตอร์จาก Cache: {pdf} ({len(cached_data['chunks'])} chunks)")
            combined_docs_data.append({
                "chunks": cached_data["chunks"],
                "embeddings": cached_data["embeddings"]
            })
            chunking_duration = cached_data.get("chunking_duration", 0.0)
            embedding_duration = cached_data.get("embedding_duration", 0.0)
        else:
            print(f"-> คำนวณเวกเตอร์และสกัดคำใหม่สำหรับ: {pdf}")
            
            default_filename = "ประกาศ มธ.สวัสดิการด้านสุขภาพ พ.ศ.2566.pdf"
            default_md_path = os.path.join(root_dir, "sample_cleaned.md")
            is_default_and_unchanged = (pdf == default_filename and os.path.exists(default_md_path))
            
            chunk_start = time.perf_counter()
            if is_default_and_unchanged:
                print("  Loading pre-cleaned markdown for default document...")
                with open(default_md_path, "r", encoding="utf-8") as f:
                    raw_md = f.read()
                    
                pages_blocks = re.split(r'(# Page \d+\n)', raw_md)
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
                    else:
                        print(f"    (Skipping pre-cleaned page {p_num})")
                    current_page_num = p_num + 1
                    
                full_text = "".join(reconstructed_blocks)
            else:
                pages = extract_text_from_pdf(pdf_path)
                text_blocks = []
                for i, page_text in enumerate(pages):
                    page_num = i + 1
                    if page_num in exclude_pages:
                        print(f"    (Skipping page {page_num})")
                        continue
                    text_blocks.append(f"# Page {page_num}\n{page_text}")
                full_text = "\n\n".join(text_blocks)
                
            chunks, _ = chunk_document_text(full_text, pdf, start_chunk_id=1)
            chunking_duration = time.perf_counter() - chunk_start
            
            if not chunks:
                print(f"  Warning: No chunks generated for {pdf}")
                continue
                
            texts = [c["content"] for c in chunks]
            embeddings_list = []
            
            if tech == "cloud_gemini":
                if not api_key:
                    raise ValueError("ไม่พบ Gemini API Key ในระบบหลังบ้าน กรุณากรอก API Key ในหน้าแอดมินก่อนใช้งาน Cloud Gemini")
                
                emb_start = time.perf_counter()
                batch_size = 100
                for i in range(0, len(texts), batch_size):
                    batch_texts = texts[i:i+batch_size]
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:batchEmbedContents?key={api_key}"
                    requests_payload = []
                    for t in batch_texts:
                        requests_payload.append({
                            "model": "models/text-embedding-004",
                            "content": {"parts": [{"text": t}]}
                        })
                    import urllib.request
                    req = urllib.request.Request(
                        url,
                        data=json.dumps({"requests": requests_payload}).encode("utf-8"),
                        headers={"Content-Type": "application/json"},
                        method="POST"
                    )
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        res_data = json.loads(resp.read().decode("utf-8"))
                        batch_embs = [item["values"] for item in res_data["embeddings"]]
                        embeddings_list.extend(batch_embs)
                embedding_duration = time.perf_counter() - emb_start
            else:
                # local_faiss หรือ local_chroma
                if model is None:
                    print("กำลังโหลดโมเดล BAAI/bge-m3 SentenceTransformer เข้าสู่ RAM...")
                    from sentence_transformers import SentenceTransformer
                    model = SentenceTransformer("BAAI/bge-m3")
                emb_start = time.perf_counter()
                embeddings_np = model.encode(texts, show_progress_bar=True, convert_to_numpy=True, normalize_embeddings=True)
                embeddings_list = embeddings_np.tolist()
                embedding_duration = time.perf_counter() - emb_start
                
            # บันทึกลง Cache
            cache_data = {
                "filename": pdf,
                "file_size": file_size,
                "file_mtime": file_mtime,
                "exclude_pages": exclude_pages,
                "embedding_tech": tech,
                "chunks": chunks,
                "embeddings": embeddings_list,
                "chunking_duration": chunking_duration,
                "embedding_duration": embedding_duration
            }
            try:
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(cache_data, f, ensure_ascii=False, indent=2)
                print(f"  💾 บันทึก Cache ลงไฟล์เรียบร้อย: {os.path.basename(cache_file)}")
            except Exception as e:
                print(f"  Error writing cache file: {e}")
                
            combined_docs_data.append({
                "chunks": chunks,
                "embeddings": embeddings_list
            })

        # อัปเดตข้อมูลระยะเวลาลงใน docs_db
        for d in docs_db:
            if d["filename"] == pdf:
                d["chunking_duration"] = round(chunking_duration, 4)
                d["embedding_duration"] = round(embedding_duration, 4)

    # บันทึกข้อมูลที่อัปเดตระยะเวลาลงใน db_documents.json
    try:
        with open(db_docs_path, "w", encoding="utf-8") as f:
            json.dump(docs_db, f, ensure_ascii=False, indent=2)
        print("💾 บันทึกเวลาสกัดคำและเวกเตอร์ลงใน db_documents.json เรียบร้อยแล้ว")
    except Exception as e:
        print(f"Error saving durations to db_documents.json: {e}")
            
    # รวบรวมข้อมูลทั้งหมด
    all_chunks = []
    all_embeddings_list = []
    chunk_id_counter = 1
    
    for doc in combined_docs_data:
        for chunk, embedding in zip(doc["chunks"], doc["embeddings"]):
            new_chunk = chunk.copy()
            new_chunk["chunk_id"] = chunk_id_counter
            all_chunks.append(new_chunk)
            all_embeddings_list.append(embedding)
            chunk_id_counter += 1
            
    print(f"รวมข้อมูล chunks สำเร็จ: ทั้งหมด {len(all_chunks)} chunks")
    
    # 2. จัดเก็บเวกเตอร์
    index_dir = os.path.join(root_dir, "index_db")
    os.makedirs(index_dir, exist_ok=True)
    
    if len(all_chunks) > 0:
        import numpy as np
        embeddings_np = np.array(all_embeddings_list, dtype=np.float32)
        
        if tech == "local_chroma":
            try:
                import chromadb
            except ImportError:
                print("กำลังติดตั้ง chromadb...")
                import subprocess
                subprocess.run([sys.executable, "-m", "pip", "install", "chromadb"])
                import chromadb
                
            if sys.platform.startswith('win') or os.name == 'nt':
                chroma_dir = "C:\\Users\\ITS\\tuh-chatbot-db\\chroma_db"
            else:
                chroma_dir = os.path.join(index_dir, "chroma_db")
            os.makedirs(chroma_dir, exist_ok=True)
            chroma_client = chromadb.PersistentClient(path=chroma_dir)
            try:
                chroma_client.delete_collection("tuh_collection")
            except Exception:
                pass
            collection = chroma_client.create_collection("tuh_collection")
            
            ids = [str(c["chunk_id"]) for c in all_chunks]
            texts = [c["content"] for c in all_chunks]
            metadatas = [c["metadata"] for c in all_chunks]
            
            collection.add(
                ids=ids,
                embeddings=embeddings_np.tolist(),
                metadatas=metadatas,
                documents=texts
            )
            print(f"บันทึก Chroma DB สำเร็จ (รวม {len(ids)} รายการ)")
            
        else:
            # FAISS (local_faiss หรือ cloud_gemini)
            import faiss
            faiss.normalize_L2(embeddings_np)
            dimension = embeddings_np.shape[1]
            faiss_index = faiss.IndexFlatIP(dimension)
            faiss_index.add(embeddings_np)
            
            faiss_index_path = os.path.join(index_dir, "faiss.index")
            faiss_meta_path = os.path.join(index_dir, "faiss_metadata.json")
            
            faiss.write_index(faiss_index, faiss_index_path)
            with open(faiss_meta_path, "w", encoding="utf-8") as f:
                json.dump(all_chunks, f, ensure_ascii=False, indent=2)
            print(f"บันทึก FAISS Index สำเร็จ (รวม {len(all_chunks)} รายการ)")
            
        # 3. บันทึก sample_chunks.json
        chunks_output_path = os.path.join(root_dir, "sample_chunks.json")
        with open(chunks_output_path, "w", encoding="utf-8") as f:
            json.dump(all_chunks, f, ensure_ascii=False, indent=2)
            
        # 4. บันทึก BM25
        print("กำลังสร้างดัชนีคำสำคัญ BM25 (ด้วย PyThaiNLP)...")
        from pythainlp.tokenize import word_tokenize
        from rank_bm25 import BM25Okapi
        import pickle
        
        texts = [c["content"] for c in all_chunks]
        tokenized_corpus = [word_tokenize(text, keep_whitespace=False) for text in texts]
        bm25 = BM25Okapi(tokenized_corpus)
        
        bm25_path = os.path.join(index_dir, "bm25.pkl")
        bm25_data = {
            "bm25_index": bm25,
            "chunks": all_chunks
        }
        with open(bm25_path, "wb") as f:
            pickle.dump(bm25_data, f)
        print("บันทึกดัชนี BM25 สำเร็จ")
    else:
        print("คำเตือน: ไม่มี chunks ที่จะทำการดรรชนีเวกเตอร์")
        
    # 5. คำนวณเวลาประมวลผลทั้งหมดและบันทึก
    duration = time.perf_counter() - start_time
    print(f"🎉 จัดทำดัชนี RAG เสร็จสิ้นในเวลา {duration:.4f} วินาที")
    
    # โหลด settings และบันทึก last_build_duration
    if os.path.exists(db_settings_path):
        try:
            with open(db_settings_path, "r", encoding="utf-8") as f:
                current_settings = json.load(f)
            
            # Only update and save if read succeeded
            current_settings["last_build_duration"] = duration
            try:
                with open(db_settings_path, "w", encoding="utf-8") as f:
                    json.dump(current_settings, f, ensure_ascii=False, indent=2)
                print("บันทึกเวลาการสร้างดัชนีลงใน db_settings.json เรียบร้อย")
            except Exception as e:
                print(f"ไม่สามารถบันทึกเวลาลงในไฟล์ได้: {e}")
        except Exception as e:
            print(f"ไม่สามารถเปิดอ่าน db_settings.json ได้เนื่องจากไฟล์ล็อกหรือข้อผิดพลาด: {e}")
            print("ข้ามการเขียนทับเพื่อป้องกันข้อมูลสูญหาย")
    else:
        current_settings = {"last_build_duration": duration}
        os.makedirs(os.path.dirname(db_settings_path), exist_ok=True)
        try:
            with open(db_settings_path, "w", encoding="utf-8") as f:
                json.dump(current_settings, f, ensure_ascii=False, indent=2)
            print("บันทึกเวลาการสร้างดัชนีลงใน db_settings.json เรียบร้อย")
        except Exception as e:
            print(f"ไม่สามารถบันทึกเวลาลงในไฟล์ได้: {e}")

if __name__ == "__main__":
    rebuild()
