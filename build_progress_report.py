import os
import subprocess
import sys
import tempfile
import shutil
import datetime

def build_pdf():
    today = datetime.date.today()
    thai_months = ["มกราคม","กุมภาพันธ์","มีนาคม","เมษายน","พฤษภาคม","มิถุนายน",
                   "กรกฎาคม","สิงหาคม","กันยายน","ตุลาคม","พฤศจิกายน","ธันวาคม"]
    date_str = f"{today.day} {thai_months[today.month-1]} {today.year + 543}"

    html_content = f"""<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>รายงานความคืบหน้า - ระบบ TUH Chatbot AI</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:ital,wght@0,300;0,400;0,500;0,700;1,400&family=Outfit:wght@400;600;700&display=swap');

        @page {{
            size: A4;
            margin: 18mm 15mm 18mm 15mm;
        }}

        * {{ box-sizing: border-box; }}

        body {{
            font-family: 'Sarabun', 'Helvetica Neue', Arial, sans-serif;
            color: #1e293b;
            line-height: 1.65;
            font-size: 13.5px;
            margin: 0; padding: 0;
        }}

        h1 {{
            font-family: 'Outfit', 'Sarabun', sans-serif;
            font-size: 22px;
            color: #0f172a;
            border-bottom: 3px solid #0ea5e9;
            padding-bottom: 8px;
            margin-top: 0;
            margin-bottom: 14px;
        }}

        h2 {{
            font-family: 'Outfit', 'Sarabun', sans-serif;
            font-size: 15px;
            color: #0369a1;
            border-left: 4px solid #0ea5e9;
            padding-left: 10px;
            margin-top: 22px;
            margin-bottom: 10px;
        }}

        h3 {{
            font-size: 13.5px;
            color: #334155;
            margin-top: 14px;
            margin-bottom: 6px;
            font-weight: 700;
        }}

        p {{ margin-bottom: 10px; text-align: justify; }}

        ul, ol {{
            margin-bottom: 10px;
            padding-left: 20px;
        }}
        li {{ margin-bottom: 4px; }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 12px 0;
            font-size: 12.5px;
        }}
        th, td {{
            border: 1px solid #cbd5e1;
            padding: 8px 10px;
            text-align: left;
            vertical-align: top;
        }}
        th {{
            background-color: #0ea5e9;
            color: #ffffff;
            font-weight: 700;
            font-size: 12px;
        }}
        tr:nth-child(even) td {{ background-color: #f0f9ff; }}

        .cover-page {{
            display: flex;
            flex-direction: column;
            justify-content: center;
            min-height: 90vh;
            page-break-after: always;
            padding: 50px 40px;
            background: linear-gradient(160deg, #0c1a2e 0%, #0f3460 50%, #1a5276 100%);
            color: #fff;
            border-radius: 4px;
        }}
        .cover-eyebrow {{
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 3px;
            text-transform: uppercase;
            color: #7dd3fc;
            margin-bottom: 18px;
        }}
        .cover-hospital {{
            font-size: 16px;
            color: #bae6fd;
            margin-bottom: 6px;
        }}
        .cover-title {{
            font-family: 'Outfit', sans-serif;
            font-size: 38px;
            font-weight: 700;
            line-height: 1.2;
            margin-bottom: 8px;
            color: #ffffff;
        }}
        .cover-subtitle {{
            font-size: 18px;
            color: #7dd3fc;
            margin-bottom: 40px;
        }}
        .cover-desc {{
            font-size: 14px;
            color: #bae6fd;
            max-width: 480px;
            line-height: 1.7;
            margin-bottom: 50px;
        }}
        .cover-meta {{
            border-top: 1px solid rgba(255,255,255,0.2);
            padding-top: 20px;
            font-size: 12.5px;
            color: #94a3b8;
            line-height: 2.0;
        }}
        .cover-meta strong {{ color: #e2e8f0; }}

        .tag-row {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-bottom: 30px;
        }}
        .tag {{
            background: rgba(14,165,233,0.25);
            color: #7dd3fc;
            border: 1px solid rgba(14,165,233,0.4);
            border-radius: 20px;
            padding: 4px 14px;
            font-size: 11.5px;
            font-weight: 600;
        }}

        .page-break {{ page-break-before: always; }}

        .section-header {{
            background: linear-gradient(90deg, #0ea5e9 0%, #0284c7 100%);
            color: white;
            padding: 10px 16px;
            border-radius: 4px;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .section-num {{
            background: rgba(255,255,255,0.25);
            border-radius: 50%;
            width: 28px;
            height: 28px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 14px;
            flex-shrink: 0;
        }}
        .section-title {{
            font-family: 'Outfit', sans-serif;
            font-size: 17px;
            font-weight: 700;
        }}

        .status-badge {{
            display: inline-block;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 700;
            white-space: nowrap;
        }}
        .done {{ background:#dcfce7; color:#166534; }}
        .progress {{ background:#fef9c3; color:#854d0e; }}
        .plan {{ background:#f1f5f9; color:#475569; }}

        .card {{
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            padding: 14px 16px;
            margin-bottom: 12px;
            background: #f8fafc;
        }}
        .card-title {{
            font-weight: 700;
            color: #0369a1;
            margin-bottom: 6px;
            font-size: 13.5px;
        }}

        .highlight-box {{
            background: #eff6ff;
            border: 1px solid #bfdbfe;
            border-left: 4px solid #3b82f6;
            border-radius: 4px;
            padding: 10px 14px;
            margin: 12px 0;
            font-size: 13px;
        }}
        .warning-box {{
            background: #fffbeb;
            border: 1px solid #fde68a;
            border-left: 4px solid #f59e0b;
            border-radius: 4px;
            padding: 10px 14px;
            margin: 12px 0;
            font-size: 13px;
        }}
        .success-box {{
            background: #f0fdf4;
            border: 1px solid #bbf7d0;
            border-left: 4px solid #22c55e;
            border-radius: 4px;
            padding: 10px 14px;
            margin: 12px 0;
            font-size: 13px;
        }}

        .header-tag {{
            text-align: right;
            font-size: 10.5px;
            color: #94a3b8;
            border-bottom: 1px solid #e2e8f0;
            padding-bottom: 5px;
            margin-bottom: 16px;
        }}

        .progress-bar-wrap {{
            background: #e2e8f0;
            border-radius: 8px;
            height: 10px;
            width: 100%;
            margin: 4px 0 10px 0;
            overflow: hidden;
        }}
        .progress-bar {{
            height: 10px;
            border-radius: 8px;
            background: linear-gradient(90deg, #0ea5e9, #0284c7);
        }}

        .two-col {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }}
    </style>
</head>
<body>

<!-- COVER PAGE -->
<div class="cover-page">
    <div class="cover-eyebrow">รายงานความคืบหน้าโครงการ · Progress Report</div>
    <div class="cover-hospital">โรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ (TUH)</div>
    <div class="cover-title">TUH Chatbot AI Suite</div>
    <div class="cover-subtitle">ระบบแชทบอทถามตอบสวัสดิการและแผงจัดการข้อมูล (2 โครงการหลัก)</div>

    <div class="tag-row">
        <span class="tag">RAG + LLM</span>
        <span class="tag">Dual Webapps</span>
        <span class="tag">Hybrid Search</span>
        <span class="tag">Admin Dashboard</span>
        <span class="tag">PBKDF2 Hashing</span>
        <span class="tag">PDF Pipeline</span>
    </div>

    <div class="cover-desc">
        เอกสารฉบับนี้สรุปความคืบหน้าการพัฒนาระบบ TUH Chatbot AI Suite 
        ซึ่งได้รับการพัฒนาขึ้นโดยแยกแพลตฟอร์มหน้าบ้านออกเป็น 2 เว็บไซต์อิสระจากกันอย่างสมบูรณ์ 
        รายงานระบุถึงสถาปัตยกรรม ฟีเจอร์ที่พัฒนาเสร็จสิ้น และการเปรียบเทียบเชิงวิจัยของ Dense Retrieval
    </div>

    <div class="cover-meta">
        <strong>จัดทำโดย:</strong> งานสารสนเทศ (IT Department)<br>
        <strong>วันที่รายงาน:</strong> {date_str}<br>
        <strong>สถานะปัจจุบัน:</strong> กำลังพัฒนาส่วนปรับปรุง (Active Enhancement)<br>
        <strong>Backend Port:</strong> 8000 | <strong>User Chatbot Web:</strong> 5175 | <strong>Admin Control Web:</strong> 5174
    </div>
</div>

<!-- PAGE 1: OVERVIEW -->
<div class="header-tag">รายงานความคืบหน้า · TUH Chatbot AI · {date_str}</div>

<div class="section-header">
    <div class="section-num">1</div>
    <div class="section-title">ภาพรวมสถาปัตยกรรมระบบ (แยก 2 เว็บไซต์หลัก)</div>
</div>

<p>
    โครงการ <strong>TUH Chatbot AI Suite</strong> ได้รับการพัฒนาขึ้นโดยแยกส่วนหน้าบ้าน (Frontend Web Applications) 
    ออกเป็น **2 เว็บไซต์ย่อยอย่างเป็นเอกเทศจากกัน (Decoupled Micro-frontend architecture)** เพื่อให้ง่ายต่อการบำรุงรักษา 
    ความปลอดภัย และความคล่องตัวในการปรับแต่งดีไซน์ มีลักษณะการเชื่อมต่อดังนี้:
</p>

<h2>1.1 รายละเอียดการแยก 2 เว็บไซต์ (Dual Webapps)</h2>
<ul>
    <li>
        <strong>เว็บไซต์ที่ 1: ระบบแชทบอทบริการบุคลากร (User Chatbot Webapp - Port 5175)</strong><br>
        พัฒนาด้วย React + Vite เน้นการทำงานที่ลื่นไหล รวดเร็ว ธีมพาสเทล ฟ้า-ม่วง พร้อมแอนิเมชันสำหรับผู้ใช้สอบถามสวัสดิการ
    </li>
    <li>
        <strong>เว็บไซต์ที่ 2: ระบบจัดการและวิเคราะห์สำหรับผู้ดูแล (Admin Dashboard Webapp - Port 5174)</strong><br>
        พัฒนาด้วย React + Vite และไอคอน FontAwesome จัดการแดชบอร์ดสถิติ ข้อมูล PDF ประกาศข่าวสาร และการปรับตั้งค่าระบบ AI 
        ได้รับการยกระดับดีไซน์ด้วยเอฟเฟกต์แก้วโปร่งแสง (Glassmorphism) สอดรับกับหน้าผู้ใช้
    </li>
    <li>
        <strong>ระบบเชื่อมต่อข้อมูลหลังบ้าน (Python API Server - Port 8000)</strong><br>
        รันด้วย Python HTTP Server คอยให้บริการ RAG Pipeline, เชื่อมต่อ Vector DB และเก็บข้อมูลลงฐานข้อมูล JSON
    </li>
</ul>

<h2>1.2 ตารางสรุปเทคโนโลยีที่แยกทำงานจริง</h2>
<table>
    <thead><tr><th>ส่วนประกอบ</th><th>เทคโนโลยี</th><th>หน้าที่และรูปแบบการแยกเว็บไซต์</th></tr></thead>
    <tbody>
        <tr><td><strong>User Chat Web</strong></td><td>React + Vite (Port 5175)</td><td>โปรเจกต์หน้าบ้านแยกอิสระ สำหรับบุคลากรถามคำถามสวัสดิการ</td></tr>
        <tr><td><strong>Admin Dashboard Web</strong></td><td>React + Vite (Port 5174)</td><td>โปรเจกต์หน้าบ้านแยกอิสระ สำหรับผู้ดูแลจัดการคลังข้อมูลและตั้งค่า RAG</td></tr>
        <tr><td><strong>Backend Server</strong></td><td>Python (Port 8000)</td><td>ให้บริการข้อมูล API แก่ทั้ง 2 เว็บไซต์ผ่าน CORS setup</td></tr>
        <tr><td><strong>Dense Search (Selected)</strong></td><td>FAISS (local_faiss) + BGE-M3</td><td>วิเคราะห์และค้นหาความหมายเวกเตอร์ (ประเมินแล้วรันเร็วสุดที่ ~76ms)</td></tr>
        <tr><td><strong>Sparse Search</strong></td><td>BM25Okapi + PyThaiNLP</td><td>สืบค้นดัชนีคำสำคัญไทย/เลขปี/สวัสดิการเฉพาะตรงตัว</td></tr>
        <tr><td><strong>AI Model (Core)</strong></td><td>Google Gemini 2.5 Flash</td><td>โมเดลหลักผ่าน OpenRouter ตอบเร็วเฉลี่ย 2 วินาที (มีระบบ Offline Fallback)</td></tr>
    </tbody>
</table>

<div class="highlight-box">
    <strong>สถาปัตยกรรมด้านความปลอดภัยใหม่:</strong> รหัสผ่านเข้าสู่ระบบของ Admin ได้รับการปรับปรุงให้จัดเก็บผ่านกระบวนการแฮชแบบทิศทางเดียว 
    <strong>PBKDF2-HMAC-SHA256 ร่วมกับเกลือ Salt ขนาด 16 ไบต์</strong> (รันวนซ้ำ 100,000 รอบ) บันทึกลงไฟล์ความปลอดภัย 
    `db_admin.json` แทนการเช็คข้อความตรงๆ ทำให้รหัสผ่านมีความปลอดภัยสูงตามมาตรฐานสากล
</div>

<div class="page-break"></div>
<div class="header-tag">รายงานความคืบหน้า · TUH Chatbot AI · {date_str}</div>

<!-- PAGE 2: DATA PIPELINE -->
<div class="section-header">
    <div class="section-num">2</div>
    <div class="section-title">กระบวนการเตรียมข้อมูลและการเปรียบเทียบ Dense Retrieval</div>
</div>

<h2>2.1 ข้อมูลผลการสืบค้นผสมผสาน (Hybrid Search & Embedding Tech)</h2>
<p>
    จากการเปรียบเทียบประสิทธิภาพของตัวเลือก **Dense Retrieval** ทั้ง 3 รูปแบบบนระบบประมวลผลจริง 
    ผลลัพธ์ปรากฏว่ามีความแตกต่างด้านความหน่วงในการตอบสนอง (Search Latency) และทรัพยากรที่ใช้อย่างมีนัยสำคัญ:
</p>

<table>
    <thead><tr><th>Embedding Technology</th><th>โมเดลที่ใช้</th><th>เวลาสร้างดัชนี</th><th>ความเร็วเสิร์ชเฉลี่ย (ms)</th><th>หน่วยความจำ (RAM) ที่ใช้เพิ่ม</th></tr></thead>
    <tbody>
        <tr><td><strong>1. local_faiss (แนะนำ/เลือกใช้)</strong></td><td>BAAI/bge-m3 (Local)</td><td>~13.61 วินาที</td><td>🚀 <strong>~76.78 ms</strong></td><td>+326.01 MB (โหลดโมเดลเข้า RAM)</td></tr>
        <tr><td><strong>2. cloud_gemini</strong></td><td>text-embedding-004</td><td>~2.28 วินาที</td><td>🐢 ~355.34 ms</td><td><strong>+0.00 MB</strong> (คำนวณบนคลาวด์)</td></tr>
        <tr><td><strong>3. local_chroma</strong></td><td>BAAI/bge-m3 (Local)</td><td>~53.66 วินาที</td><td>⚡ ~82.37 ms</td><td>+291.99 MB (Overhead Chroma)</td></tr>
    </tbody>
</table>

<h2>2.2 ผลวิเคราะห์และการนำมาปรับใช้</h2>
<ul>
    <li>
        <strong>ทำไมเลือก local_faiss:</strong> ให้ความเร็วในการเสิร์ชสูงที่สุด (~76ms) ซึ่งเร็วกว่า cloud_gemini ถึง 4.6 เท่า 
        เนื่องจากไม่ต้องส่งข้อมูลไปแปลงเป็นเวกเตอร์บนอินเทอร์เน็ตทุกครั้ง อีกทั้งระบบจัดเก็บไฟล์ FAISS เดี่ยวทำให้สร้างดัชนีเร็วมาก 
        และทำงานแบบออฟไลน์ได้ 100%
    </li>
    <li>
        <strong>การประยุกต์ใช้ RRF (Reciprocal Rank Fusion):</strong> ผสานผลลัพธ์จาก FAISS (ค่าน้ำหนัก 0.4) และ BM25 (ค่าน้ำหนัก 0.6) 
        ร่วมกับการขยายชุดคำค้นพ้องภาษาไทย (Query Expansion) เช่น "สามี" -> "คู่สมรส", "ลูก" -> "บุตร" เพื่อจับคู่กับตัวประกาศกฎหมายจริง
    </li>
</ul>

<div class="card">
    <div class="card-title">ความแม่นยำในการแยกวิเคราะห์เอกสารตาราง (Table Parent-Child Chunking)</div>
    <p style="font-size:12.5px; margin:0;">
        โครงสร้างข้อมูลสวัสดิการของโรงพยาบาลส่วนใหญ่อยู่ในรูปแบบตารางเปรียบเทียบ ระบบ RAG นี้จึงใช้วิธีสกัดตารางตัวเต็มเป็น Parent Markdown 
        สำหรับส่งต่อให้โมเดลสรุปผล และสกัดคำย่อตารางเป็น Child Chunk สำหรับให้บอทค้นหาคีย์เวิร์ด ช่วยลบปัญหาเรื่องบอทอ่านตารางไม่รู้เรื่องได้อย่างสมบูรณ์
    </p>
</div>

<div class="page-break"></div>
<div class="header-tag">รายงานความคืบหน้า · TUH Chatbot AI · {date_str}</div>

<!-- PAGE 3: FRONTEND FEATURES DEVELOPED -->
<div class="section-header">
    <div class="section-num">3</div>
    <div class="section-title">ฟีเจอร์เด่นของแต่ละเว็บไซต์ที่พัฒนาสำเร็จแล้ว</div>
</div>

<h2>3.1 แผงควบคุมระบบผู้ดูแล (Admin Control Webapp - Port 5174)</h2>
<p>
    หน้าจัดการระบบเป็นเว็บไซต์แยกโปรเจกต์ที่เชื่อมต่อ API กับหลังบ้าน มีความสามารถครบครันในการควบคุมการทำงานของแชทบอท:
</p>

<div class="card">
    <div class="card-title">ฟีเจอร์สำคัญด้านการจัดการและความปลอดภัย (Security & Management)</div>
    <ul>
        <li><strong>ความปลอดภัยระบบล็อกอิน:</strong> ป้องกันข้อมูลผ่านระบบ Hashing (PBKDF2-SHA256) และสุ่ม Salt ขนาด 16 ไบต์ ปลอดภัย 100% <span class="status-badge done">เสร็จสิ้น</span></li>
        <li><strong>ระบบเพิ่มและแก้ไขประกาศข่าวสาร (Edit Announcements):</strong> สามารถกดปุ่มดินสอแก้ไขหัวข้อ เนื้อหา หรือวันที่ของประกาศเก่า แล้วจัดเก็บลงฐานข้อมูลได้ทันทีผ่านระบบ UI สะดวกโดยไม่ต้องเขียนโปรแกรมเพิ่มเติม <span class="status-badge done">เสร็จสิ้น</span></li>
        <li><strong>UI ธีมดีไซน์ใหม่สอดคล้องแชทบอท:</strong> ปรับปรุง CSS ทั่วทั้งโปรเจกต์ให้สลับเป็นโหมดพื้นหลังสีพาสเทลไล่เฉดสีพลิ้วไหว (Ambient Flow) พร้อมการ์ดแก้วกึ่งโปร่งแสง (Glassmorphic cards) หรูหราทันสมัย <span class="status-badge done">เสร็จสิ้น</span></li>
        <li><strong>การจัดการเอกสาร PDF ความรู้:</strong> เพิ่มเอกสาร กำหนดหน้าที่ต้องการข้าม (Exclude) ทำการ Build และ Reload คลังข้อมูลได้สดใหม่ทันทีในคลิกเดียว <span class="status-badge done">เสร็จสิ้น</span></li>
        <li><strong>ระบบตั้งค่าระดับลึก (AI & RAG Settings):</strong> ปรับแต่งอุณหภูมิความคิดสร้างสรรค์ของ AI (Temperature), เลือกรุ่นโมเดลหลัก, จัดการ FAQs ยอดนิยม และ Export ข้อมูลประวัติการแชทเป็นไฟล์ CSV <span class="status-badge done">เสร็จสิ้น</span></li>
    </ul>
</div>

<h2>3.2 หน้าแชทสอบถามสวัสดิการบุคลากร (User Chat Webapp - Port 5175)</h2>
<p>
    เว็บไซต์สำหรับพนักงานในการค้นคว้าข้อมูล มีอินเทอร์เฟซแบบแชทบอทที่เข้าใจง่าย เป็นมิตร และลื่นไหล:
</p>

<div class="two-col">
    <div class="card">
        <div class="card-title">ความสามารถหลักของหน้าแชท</div>
        <ul>
            <li>คุยโต้ตอบกับ Mascot "ขาหมู" ด้วยคำถามภาษาไทยที่เป็นธรรมชาติ</li>
            <li>แสดงกล่องลิงก์ "ดาวน์โหลดแบบฟอร์มสวัสดิการ" ที่แอดมินอัปโหลดไว้ให้อัตโนมัติ</li>
            <li>แสดงประวัติข้อความและสืบค้นความคุ้นเคยเดิมแบบ Context Memory</li>
        </ul>
    </div>
    <div class="card">
        <div class="card-title">ระบบตอบรับและข้อเสนอแนะ</div>
        <ul>
            <li>แสดงรายชื่อไฟล์อ้างอิงและหน้าที่ใช้ตอบคำถามอย่างโปร่งใส</li>
            <li>ปุ่มโหวต Like/Dislike และการพิมพ์ข้อเสนอแนะความพึงพอใจ</li>
            <li>ปุ่มคลิกถามแบบด่วนสำหรับข้อสงสัยที่พบบ่อย (Predefined FAQs)</li>
        </ul>
    </div>
</div>

<div class="page-break"></div>
<div class="header-tag">รายงานความคืบหน้า · TUH Chatbot AI · {date_str}</div>

<!-- PAGE 4: PROGRESS & FUTURE PLAN -->
<div class="section-header">
    <div class="section-num">4</div>
    <div class="section-title">สรุปสถานะการพัฒนาปัจจุบันและแผนงานถัดไป</div>
</div>

<h2>4.1 ตารางประเมินระดับความสำเร็จรายส่วนประกอบ</h2>
<table>
    <thead><tr><th>ระบบย่อยของซอฟต์แวร์ (Components)</th><th>ความคืบหน้า</th><th>รายละเอียดการปรับปรุงล่าสุด</th></tr></thead>
    <tbody>
        <tr>
            <td><strong>User Chat Webapp (Port 5175)</strong></td>
            <td><div class="progress-bar-wrap"><div class="progress-bar" style="width:90%"></div></div>90%</td>
            <td>หน้าจอแชทรองรับสไลด์ดาวน์โหลดฟอร์ม และแสดงประกาศ HR เรียบร้อย</td>
        </tr>
        <tr>
            <td><strong>Admin Dashboard Webapp (Port 5174)</strong></td>
            <td><div class="progress-bar-wrap"><div class="progress-bar" style="width:95%"></div></div>95%</td>
            <td>เพิ่มฟีเจอร์แก้ไขประกาศ, เปลี่ยนโทนสี Glassmorphism ธีมพาสเทลเสร็จสิ้น</td>
        </tr>
        <tr>
            <td><strong>RAG Data Clean & Index Pipeline</strong></td>
            <td><div class="progress-bar-wrap"><div class="progress-bar" style="width:95%"></div></div>95%</td>
            <td>ระบบ Parent-Child หั่นข้อมูลตารางมีความแม่นยำสูง ดัชนีโหลดใหม่เข้า RAM เรียบร้อย</td>
        </tr>
        <tr>
            <td><strong>ความปลอดภัยในการพิสูจน์ตัวตน (Security)</strong></td>
            <td><div class="progress-bar-wrap"><div class="progress-bar" style="width:90%"></div></div>90%</td>
            <td>ย้ายการล็อกอินมาใช้ระบบแฮชความปลอดภัยสูง PBKDF2-HMAC-SHA256 สำเร็จ</td>
        </tr>
        <tr>
            <td><strong>การสืบค้นผสมผสาน (Hybrid Search RRF)</strong></td>
            <td><div class="progress-bar-wrap"><div class="progress-bar" style="width:90%"></div></div>90%</td>
            <td>ใช้งาน local_faiss เป็นตัวหลัก ร่วมกับ BM25 และการขยายคำพ้องไทย</td>
        </tr>
    </tbody>
</table>

<h2>4.2 ประเด็นความคืบหน้าและข้อค้นพบเชิงพัฒนา</h2>
<div class="success-box">
    <strong>การทดสอบเปรียบเทียบในขั้นตอน UAT เบื้องต้น:</strong> ระบบตอบสนองเสิร์ชได้ภายใน ~76ms (ฝั่งสืบค้นเวกเตอร์) 
    และเมื่อส่งต่อให้ Gemini 2.5 Flash สรุปความคำตอบโดยรวมพร้อมส่งกลับถึงผู้ใช้เฉลี่ยจะอยู่ที่ **1.5 - 2.5 วินาที** 
    ซึ่งรวดเร็วกว่าระบบเดิมที่ใช้โมเดล DeepSeek v4-flash ผ่านคลาวด์ซึ่งล่าช้าถึง 14 วินาทีเป็นอย่างมาก
</div>

<h2>4.3 แผนงานระยะถัดไป (Next Steps)</h2>
<ul>
    <li><strong> UAT ขั้นสมบูรณ์:</strong> เปิดให้ฝ่ายบุคคล (HR) และพนักงานกลุ่มตัวอย่างเริ่มทดสอบใช้งานจริง เพื่อจัดเก็บชุดคำถามที่ตอบไม่ได้และฟีดแบ็กด้านการประยุกต์คำตอบ</li>
    <li><strong> ระบบสลับการเชื่อมต่อ DB สำรอง:</strong> พัฒนาระบบรองรับการขยายคลังข้อมูล PDF ปริมาณมาก โดยเตรียมแผนย้ายจากฐานข้อมูลไฟล์ JSON ไปใช้ฐานข้อมูลระบบจัดเก็บความสัมพันธ์ (เช่น SQLite) ก่อนส่งงานในอนาคต</li>
    <li><strong> ทำประเมินความถูกต้อง (RAG Evaluation):</strong> วัดค่าความเกี่ยวเนื่องและความถูกต้องผ่านเครื่องมือวัดประสิทธิภาพเพื่อให้มั่นใจว่า AI ไม่มีอาการหลอน (Hallucination)</li>
</ul>

<div class="footer">
    <p>จัดทำโดยระบบแชทบอทอัจฉริยะวิจัยและทดสอบประสิทธิภาพ | วันที่ประเมินผล: 1 กรกฎาคม 2026</p>
</div>

</body>
</html>
"""

    temp_dir = tempfile.gettempdir()
    temp_html_path = os.path.join(temp_dir, "progress_report_temp.html")
    temp_pdf_path  = os.path.join(temp_dir, "progress_report.pdf")

    for p in [temp_html_path, temp_pdf_path]:
        if os.path.exists(p):
            try: os.remove(p)
            except: pass

    with open(temp_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Generated HTML at: {temp_html_path}")

    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    ]
    executable = None
    for p in edge_paths:
        if os.path.exists(p):
            executable = p
            break
    if not executable:
        executable = "msedge"

    print(f"Printing PDF via: {executable}")
    cmd = [
        executable, "--headless", "--disable-gpu",
        f"--print-to-pdf={temp_pdf_path}",
        "--no-margins", "--print-to-pdf-no-header",
        temp_html_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
        if os.path.exists(temp_pdf_path):
            print(f"PDF generated at: {temp_pdf_path}")
            base_dir = os.path.dirname(os.path.abspath(__file__))
            final_pdf = os.path.join(base_dir, "progress_report.pdf")
            shutil.copy2(temp_pdf_path, final_pdf)
            print(f"Final PDF saved to: {final_pdf}")
        else:
            print("FAILED: PDF not found")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        for p in [temp_html_path, temp_pdf_path]:
            if os.path.exists(p):
                try: os.remove(p)
                except: pass

if __name__ == "__main__":
    build_pdf()
