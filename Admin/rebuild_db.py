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
        pages_text.append(page.get_text())
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
        chunk_size=1000,
        chunk_overlap=400,
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
    uploads_dir = os.path.join(root_dir, "uploads")
    if not os.path.exists(uploads_dir):
        print(f"Uploads directory not found: {uploads_dir}")
        return
        
    pdf_files = [f for f in os.listdir(uploads_dir) if f.lower().endswith(".pdf")]
    print(f"Found {len(pdf_files)} PDF documents to index.")

    all_chunks = []
    current_chunk_id = 1
    
    db_docs_path = os.path.join(root_dir, "user", "backend", "db", "db_documents.json")
    if os.path.exists(db_docs_path):
        with open(db_docs_path, "r", encoding="utf-8") as f:
            docs_db = json.load(f)
    else:
        docs_db = []
        
    active_filenames = {d["filename"] for d in docs_db if d.get("status", "Active") == "Active"}
    if not docs_db:
        active_filenames = set(pdf_files)
    
    for pdf in pdf_files:
        if pdf not in active_filenames:
            print(f"Skipping Inactive document: {pdf}")
            continue
            
        print(f"Processing document: {pdf}")
        pdf_path = os.path.join(uploads_dir, pdf)
        
        # ดึงเลขหน้าที่ยกเว้นไม่เบิก/ไม่นำเข้า
        doc_record = next((d for d in docs_db if d["filename"] == pdf), {})
        exclude_pages = doc_record.get("exclude_pages", [])
        print(f"  Excluded pages config: {exclude_pages}")
        
        default_filename = "ประกาศ มธ.สวัสดิการด้านสุขภาพ พ.ศ.2566.pdf"
        default_md_path = os.path.join(root_dir, "sample_cleaned.md")
        
        is_default_and_unchanged = (pdf == default_filename and os.path.exists(default_md_path))
        
        # แกะเนื้อหาข้อความ
        if is_default_and_unchanged:
            print("Loading pre-cleaned markdown for default document...")
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
                    print(f"  (Skipping pre-cleaned page {p_num})")
                current_page_num = p_num + 1
                
            full_text = "".join(reconstructed_blocks)
        else:
            pages = extract_text_from_pdf(pdf_path)
            text_blocks = []
            for i, page_text in enumerate(pages):
                page_num = i + 1
                if page_num in exclude_pages:
                    print(f"  (Skipping page {page_num})")
                    continue
                text_blocks.append(f"# Page {page_num}\n{page_text}")
            full_text = "\n\n".join(text_blocks)
            
        # หั่น Chunks
        chunks, next_chunk_id = chunk_document_text(full_text, pdf, start_chunk_id=current_chunk_id)
        all_chunks.extend(chunks)
        current_chunk_id = next_chunk_id
        
    print(f"Generated a total of {len(all_chunks)} chunks.")
    chunks_output_path = os.path.join(root_dir, "sample_chunks.json")
    with open(chunks_output_path, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)
    print(f"Saved combined chunks to: {chunks_output_path}")
    
    # emb Vector / BM25
    print("Starting vector embedding indexing...")
    from Admin.emb import build_indices
    build_indices()
    print("Vector database indices rebuilt successfully")

if __name__ == "__main__":
    rebuild()
