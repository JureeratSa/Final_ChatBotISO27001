import os
import re
import time
import json
import fitz  
import camelot 
import pandas as pd

PDF_PATH = r"Z:\Intern\2026\มวล\PJChatbot\ประกาศ มธ.สวัสดิการด้านสุขภาพ พ.ศ.2566.pdf"

EXCLUDE_PAGES = [12, 13, 14, 18]

THAI_TO_ARABIC = {
    '๐': '0', '๑': '1', '๒': '2', '๓': '3', '๔': '4',
    '๕': '5', '๖': '6', '๗': '7', '๘': '8', '๙': '9'
}

def replace_thai_numbers(text):
    """ฟังก์ชันสำหรับแปลงเลขไทยเป็นเลขอาราบิกในข้อความ"""
    if not isinstance(text, str):
        return text
    text = "".join(THAI_TO_ARABIC.get(char, char) for char in text)
    text = re.sub(r'\s+([\u0e48-\u0e4b]?)\s*า', r'\1ำ', text)
    return text

def clean_table_text(text):
    """ฟังก์ชันสำหรับคลีนข้อมูลในเซลล์ตาราง (แปลงเลขไทย และลบเครื่องหมายขึ้นบรรทัดใหม่ที่ทำลายโครงสร้างตาราง)"""
    if not isinstance(text, str):
        return text
    # 1. แปลงเลขไทยเป็นอาราบิก และแก้ไขสระ ำ
    text = replace_thai_numbers(text)
    # 2. แก้ปัญหาการขึ้นบรรทัดใหม่กลางคำภาษาไทยในเซลล์
    text = re.sub(r'([\u0e00-\u0e7f])\n\s*([\u0e00-\u0e7f])', r'\1\2', text)
    # 3. แทนที่เครื่องหมายขึ้นบรรทัดใหม่อื่นๆ ด้วยช่องว่าง
    text = text.replace('\n', ' ')
    # 4. ลบช่องว่างส่วนเกิน
    text = re.sub(r' +', ' ', text)
    return text.strip()



def clean_pdf_and_extract():
    start_time = time.time()
    pdf_path = PDF_PATH

    

    output_md_path = "sample_cleaned.md"

    print(f"📖 กำลังประมวลผลไฟล์ PDF: {pdf_path}")

    # --- ส่วนที่ 2: ดึงตารางจาก PDF ด้วย Camelot (กำหนดหน้าเพื่อความรวดเร็ว) ---
    print("📊 กำลังอ่านตารางด้วย Camelot...")
    try:
        doc_temp = fitz.open(pdf_path)
        total_pages_original = len(doc_temp)
        doc_temp.close()
        
        # กรองหน้าที่ต้องการอ่านตาราง (ตัดหน้าข้ามออก)
        pages_to_read = [p for p in range(1, total_pages_original + 1) if p not in EXCLUDE_PAGES]
        pages_str = ",".join(map(str, pages_to_read))
        
        tables = camelot.read_pdf(pdf_path, pages=pages_str)
        print(f"✅ พบตารางทั้งหมด {len(tables)} ตาราง")
    except Exception as e:
        print(f"⚠️ เกิดข้อผิดพลาดในการรัน Camelot: {e}")
        tables = []

    # --- ส่วนที่ 3: ดึงข้อความปกติด้วย PyMuPDF และผสานเข้ากับตาราง ---
    print("✍️ กำลังดึงข้อความและแปลงเลขไทย...")
    try:
        doc = fitz.open(pdf_path)
        
        # เตรียมโครงสร้างข้อมูลเพื่อบันทึกเป็น .md
        md_content = []

        for page_idx in range(len(doc)):
            page_num = page_idx + 1  # ลำดับหน้าแบบ 1-indexed (ตามไฟล์ต้นฉบับ)
            
            # ตรวจสอบเพื่อข้ามหน้าที่ต้องการละเว้น
            if page_num in EXCLUDE_PAGES:
                continue
                
            page = doc[page_idx]
            H = page.rect.height
            W = page.rect.width

            # หาตารางทั้งหมดที่อยู่ในหน้านี้
            page_tables = [t for t in tables if t.page == page_num]
            table_rects = []
            
            for t in page_tables:
                x1, y1, x2, y2 = t._bbox
                rect = fitz.Rect(x1, H - y2, x2, H - y1)
                table_rects.append((rect, t))

            # ดึงคำทั้งหมดในหน้านี้มาตรวจสอบขอบเขต
            words = page.get_text("words")
            clean_words = []

            for w in words:
                w_rect = fitz.Rect(w[0], w[1], w[2], w[3])
                
                # ตรวจสอบว่าคำนี้ทับซ้อนกับพื้นที่ตารางหรือไม่
                inside_table = False
                for t_rect, _ in table_rects:
                    if w_rect.intersects(t_rect):
                        intersection = w_rect & t_rect
                        if intersection.get_area() / w_rect.get_area() > 0.5:
                            inside_table = True
                            break
                
                if not inside_table:
                    # ป้องกันข้อความโลโก้แบบอักษรที่อยู่ส่วนหัวกระดาษ (Header Area)
                    is_logo_text = False
                    if w[1] < H * 0.08:
                        if w[4].lower() in ['logo', 'ตราสัญลักษณ์', 'สัญลักษณ์', 'ตรา']:
                            is_logo_text = True
                    
                    if not is_logo_text:
                        clean_words.append(w)

            # จัดกลุ่มคำกลับมาเป็นบรรทัดและบล็อก
            from collections import defaultdict
            lines_by_block = defaultdict(lambda: defaultdict(list))
            for w in clean_words:
                block_no = w[5]
                line_no = w[6]
                lines_by_block[block_no][line_no].append(w)

            # สรรค์สร้างบล็อกข้อความธรรมดา
            blocks = []
            for b_no in lines_by_block:
                block_lines = []
                all_y0s = []
                for l_no in sorted(lines_by_block[b_no].keys()):
                    sorted_words = sorted(lines_by_block[b_no][l_no], key=lambda x: x[0])
                    line_text = " ".join(x[4] for x in sorted_words)
                    block_lines.append(line_text)
                    all_y0s.extend(w[1] for w in lines_by_block[b_no][l_no])
                
                if block_lines:
                    block_text = "\n".join(block_lines)
                    block_text = replace_thai_numbers(block_text)  # แปลงเลขไทยในข้อความธรรมดา
                    block_y0 = min(all_y0s)
                    blocks.append({
                        'type': 'text',
                        'y0': block_y0,
                        'content': block_text
                    })

            # นำข้อมูลตาราง (Markdown) มาสร้างเป็นบล็อก
            table_list_json = []
            for t_rect, table in table_rects:
                # สร้าง DataFrame ใหม่โดยการดึงข้อความจาก PyMuPDF ด้วยพิกัดเซลล์ของ Camelot โดยสนับสนุนการรวมเซลล์ (merged cells)
                num_rows = len(table.cells)
                num_cols = len(table.cells[0])
                visited = [[False for _ in range(num_cols)] for _ in range(num_rows)]
                reconstructed_rows = [["" for _ in range(num_cols)] for _ in range(num_rows)]

                for r in range(num_rows):
                    for c in range(num_cols):
                        if visited[r][c]:
                            continue
                        
                        # ค้นหาขอบเขตการรวมเซลล์ในแนวนอน (hspan)
                        c_end = c
                        while c_end + 1 < num_cols and table.cells[r][c_end].hspan and not table.cells[r][c_end].right and not table.cells[r][c_end+1].left:
                            c_end += 1
                            
                        # ค้นหาขอบเขตการรวมเซลล์ในแนวตั้ง (vspan)
                        r_end = r
                        while r_end + 1 < num_rows and table.cells[r_end][c].vspan and not table.cells[r_end][c].bottom and not table.cells[r_end+1][c].top:
                            r_end += 1
                            
                        # ทำเครื่องหมายเซลล์ในกลุ่มที่ถูกเข้าถึงแล้ว
                        for r_i in range(r, r_end + 1):
                            for c_i in range(c, c_end + 1):
                                visited[r_i][c_i] = True
                                
                        # ดึงพิกัดรวมของเซลล์ที่ผสานกัน
                        x1 = table.cells[r][c].x1
                        y1 = table.cells[r_end][c].y1
                        x2 = table.cells[r][c_end].x2
                        y2 = table.cells[r][c].y2
                        
                        # แปลงพิกัด Camelot (bottom-left) เป็น PyMuPDF (top-left)
                        cell_rect = fitz.Rect(x1, H - y2, x2, H - y1)
                        # ดึงข้อความในขอบเขตเซลล์รวม
                        cell_text = page.get_text("text", clip=cell_rect)
                        cleaned_cell_text = clean_table_text(cell_text)
                        reconstructed_rows[r][c] = cleaned_cell_text
                
                df_cleaned = pd.DataFrame(reconstructed_rows)
                table_md = df_cleaned.to_markdown(index=False)
                table_y0 = t_rect.y0
                
                blocks.append({
                    'type': 'table',
                    'y0': table_y0,
                    'content': table_md
                })
                
                # เก็บเป็น JSON records
                table_list_json.append(df_cleaned.to_dict(orient='records'))

            # เรียงบล็อกทั้งหมดจากบนลงล่างตามพิกัด y0
            blocks.sort(key=lambda x: x['y0'])

            # --- ประกอบข้อมูลรูปแบบ .md ---
            md_page = f"# Page {page_num}\n"
            for block in blocks:
                md_page += f"\n{block['content']}\n"
            md_content.append(md_page)

        # --- เขียนผลลัพธ์ลงไฟล์ .md ---
        with open(output_md_path, 'w', encoding='utf-8') as f:
            f.write("\n\n".join(md_content))

        doc.close()
        
        # คำนวณเวลาการทำงานทั้งหมด
        elapsed_time = time.time() - start_time
        
        print("\n==================================================")
        print("ประมวลผลและสร้างไฟล์ผลลัพธ์เสร็จสมบูรณ์")
        print(f"ไฟล์มาร์กดาวน์: {output_md_path}")
        print(f"เวลาที่ใช้ในการดึงข้อมูลทั้งหมด: {elapsed_time:.4f} วินาที")
        print("==================================================\n")

    except Exception as e:
        print(f"เกิดข้อผิดพลาดในขั้นตอนดึงข้อความ: {e}")

if __name__ == "__main__":
    clean_pdf_and_extract()
