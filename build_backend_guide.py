import os
import subprocess
import sys
import tempfile
import shutil

def build_pdf():
    html_content = """<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>คู่มือการทำงานระบบ Backend Server - TUH Chatbot AI</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:ital,wght@0,300;0,400;0,500;0,700;1,400&family=Outfit:wght@400;600;700&display=swap');
        
        @page {
            size: A4;
            margin: 20mm 15mm 20mm 15mm;
        }
        
        body {
            font-family: 'Sarabun', 'Helvetica Neue', Arial, sans-serif;
            color: #1f2937;
            line-height: 1.6;
            font-size: 14px;
        }

        h1, h2, h3, h4 {
            font-family: 'Outfit', 'Sarabun', sans-serif;
            color: #0f172a;
            margin-top: 1.5em;
            margin-bottom: 0.5em;
            font-weight: 700;
        }

        h1 {
            font-size: 26px;
            color: #1e3b8b;
            border-bottom: 3px solid #1e3b8b;
            padding-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        h2 {
            font-size: 18px;
            color: #0f766e;
            border-left: 4px solid #0f766e;
            padding-left: 10px;
            margin-top: 2em;
        }

        h3 {
            font-size: 15px;
            color: #334155;
        }

        p {
            margin-bottom: 1.2em;
            text-align: justify;
        }

        ul, ol {
            margin-bottom: 1.2em;
            padding-left: 20px;
        }

        li {
            margin-bottom: 0.5em;
        }

        /* Tables */
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 1.5em 0;
            font-size: 13px;
        }

        th, td {
            border: 1px solid #e2e8f0;
            padding: 10px 12px;
            text-align: left;
        }

        th {
            background-color: #f1f5f9;
            color: #0f172a;
            font-weight: 700;
        }

        tr:nth-child(even) td {
            background-color: #f8fafc;
        }

        /* Code Block */
        pre {
            background-color: #1e293b;
            color: #f8fafc;
            padding: 12px 16px;
            border-radius: 6px;
            overflow-x: auto;
            font-family: 'Consolas', 'Courier New', Courier, monospace;
            font-size: 12px;
            margin: 1.2em 0;
            line-height: 1.4;
        }

        code {
            font-family: 'Consolas', 'Courier New', Courier, monospace;
            background-color: #f1f5f9;
            color: #e11d48;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 12px;
        }

        pre code {
            background-color: transparent;
            color: inherit;
            padding: 0;
            font-size: inherit;
        }

        /* Alerts */
        .alert {
            padding: 12px 16px;
            margin: 1.5em 0;
            border-left: 4px solid;
            border-radius: 4px;
            font-size: 13.5px;
        }

        .alert-note {
            background-color: #eff6ff;
            border-color: #2563eb;
            color: #1e40af;
        }

        .alert-tip {
            background-color: #ecfdf5;
            border-color: #10b981;
            color: #065f46;
        }

        .alert-warning {
            background-color: #fffbeb;
            border-color: #f59e0b;
            color: #92400e;
        }

        /* Header / Footer layout */
        .cover-page {
            display: flex;
            flex-direction: column;
            justify-content: center;
            height: 100vh;
            page-break-after: always;
            padding: 40px;
            box-sizing: border-box;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            background: linear-gradient(135deg, #f8fafc 0%, #eff6ff 100%);
        }

        .cover-title {
            font-size: 32px;
            color: #1e3b8b;
            margin-bottom: 10px;
            line-height: 1.3;
            font-weight: 700;
        }

        .cover-subtitle {
            font-size: 18px;
            color: #0f766e;
            margin-bottom: 40px;
            font-weight: 500;
        }

        .cover-meta {
            margin-top: auto;
            font-size: 13px;
            color: #64748b;
            border-top: 1px solid #cbd5e1;
            padding-top: 20px;
            line-height: 1.8;
        }

        .page-break {
            page-break-before: always;
        }

        .header-tag {
            text-align: right;
            font-size: 11px;
            color: #94a3b8;
            margin-bottom: 20px;
            border-bottom: 1px solid #e2e8f0;
            padding-bottom: 5px;
        }
    </style>
</head>
<body>

    <!-- COVER PAGE -->
    <div class="cover-page">
        <div style="font-size: 12px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 20px;">
            Technical Documentation
        </div>
        <div class="cover-title">คู่มือสถาปัตยกรรมและการทำงาน<br>ระบบ Backend Server</div>
        <div class="cover-subtitle">ระบบบริการตอบคำถามข้อมูลสารสนเทศและสวัสดิการผู้ป่วย (TUH Chatbot AI)</div>
        
        <div style="max-width: 500px; font-size: 14px; color: #475569; margin-bottom: 40px; line-height: 1.6;">
            เอกสารฉบับนี้อธิบายถึงรายละเอียดสถาปัตยกรรมฝั่งเซิร์ฟเวอร์ (Backend) การออกแบบ API Routing ระบบจัดการฐานข้อมูล JSON และกระบวนการผสานข้อมูล RAG (Retrieval-Augmented Generation) ของบอทโรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ
        </div>

        <div class="cover-meta">
            <strong>จัดทำโดย:</strong> งานสารสนเทศ (IT Department) โรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ<br>
            <strong>ระบบฐานข้อมูล RAG:</strong> Hybrid Retrieval (FAISS + BM25) ผสานด้วย RRF<br>
            <strong>สถานะเซิร์ฟเวอร์:</strong> ใช้งานจริง (Active) | พอร์ตให้บริการ: 8000 (Backend), 5173 (Frontend)<br>
            <strong>วันที่อัปเดตล่าสุด:</strong> 25 มิถุนายน 2569
        </div>
    </div>

    <!-- PAGE 1: OVERVIEW & ROUTING -->
    <div class="header-tag">คู่มือระบบสารสนเทศ TUH Chatbot AI Backend Server (พ.ศ. 2569)</div>
    
    <h1>1. สถาปัตยกรรมภาพรวมและการทำงานของเซิร์ฟเวอร์</h1>
    <p>
        เซิร์ฟเวอร์หลังบ้าน (Backend Server) ของระบบ <strong>TUH Chatbot AI</strong> พัฒนาขึ้นโดยใช้ภาษา Python ทั้งหมด โดยเลือกใช้โมดูลมาตรฐานอย่าง <code>ThreadingHTTPServer</code> และ <code>BaseHTTPRequestHandler</code> เพื่อประสิทธิภาพในการให้บริการร้องขอแบบมัลติเธรด (Multi-threaded) และลดความซับซ้อนในการติดตั้งโมดูลเว็บเฟรมเวิร์กขนาดใหญ่ภายนอก
    </p>
    <p>
        หน้าที่หลักของ Backend Server ประกอบด้วยการให้บริการ API แก่เว็บแอปพลิเคชันฝั่ง Client (สำหรับการถามตอบแชทบอทและบันทึกข้อเสนอแนะ) และฝั่ง Admin (สำหรับการตั้งค่าคีย์ API สิทธิ์ควบคุมเอกสาร ดูสถิติจราจร และวิเคราะห์คำถามที่ตอบไม่ได้)
    </p>

    <h2>1.1 การรองรับ CORS (Cross-Origin Resource Sharing)</h2>
    <p>
        เนื่องจากฝั่งเว็บแอปพลิเคชัน (Frontend) ทำงานบนพอร์ตพัฒนา <code>5173</code> (รันบน Vite) ขณะที่เซิร์ฟเวอร์หลังบ้านรันบนพอร์ต <code>8000</code> เพื่อให้เบราว์เซอร์ยอมรับการสื่อสารข้าม Origin ทางเซิร์ฟเวอร์จึงจัดตั้ง CORS Headers ในฟังก์ชัน <code>_set_headers</code> และ <code>do_OPTIONS</code> ดังนี้:
    </p>
    <pre>self.send_header('Access-Control-Allow-Origin', '*')
self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-File-Name')</pre>

    <h2>1.2 รายการเส้นทาง API (API Routes)</h2>
    <p>
        การทำงานจะดักจับคำขอร้องผ่านฟังก์ชัน <code>do_GET</code> และ <code>do_POST</code> ในคลาส <code>SearchAPIHandler</code> โดยแยกเส้นทางการทำงานออกเป็นกลุ่มผู้ใช้ทั่วไปและผู้ดูแลระบบ ดังรายละเอียดในตารางนี้:
    </p>

    <table>
        <thead>
            <tr>
                <th>เส้นทาง API (Route)</th>
                <th>Method</th>
                <th>กลุ่มผู้ใช้</th>
                <th>หน้าที่และคำอธิบาย</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><code>/</code></td>
                <td>GET</td>
                <td>ทั่วไป</td>
                <td>ตรวจสอบสถานะการออนไลน์ของระบบ (Health Check)</td>
            </tr>
            <tr>
                <td><code>/api/search</code></td>
                <td>POST</td>
                <td>ทั่วไป</td>
                <td>สอบถามแชทบอท ค้นข้อมูลด้วย Hybrid Search และส่งให้ AI ตอบกลับ</td>
            </tr>
            <tr>
                <td><code>/api/admin/login</code></td>
                <td>POST</td>
                <td>ผู้ดูแล</td>
                <td>ยืนยันตัวตนสำหรับล็อกอินเข้าหน้าควบคุมระบบหลังบ้าน (Admin Panel)</td>
            </tr>
            <tr>
                <td><code>/api/admin/stats</code></td>
                <td>GET</td>
                <td>ผู้ดูแล</td>
                <td>ดึงข้อมูลสถิติภาพรวม ยอดไลก์/ดิสไลก์ จำนวนเอกสาร และคอมเมนต์ล่าสุด</td>
            </tr>
            <tr>
                <td><code>/api/admin/settings</code></td>
                <td>GET/POST</td>
                <td>ผู้ดูแล</td>
                <td>เรียกดูหรืออัปเดตการตั้งค่าระบบ (System Prompt, อุณหภูมิ, คีย์ API, FAQ)</td>
            </tr>
            <tr>
                <td><code>/api/admin/documents</code></td>
                <td>GET</td>
                <td>ผู้ดูแล</td>
                <td>ดึงรายการเอกสาร PDF ทั้งหมดที่นำเข้ามาในระบบพร้อมประวัติการข้ามหน้า</td>
            </tr>
            <tr>
                <td><code>/api/admin/documents/toggle</code></td>
                <td>POST</td>
                <td>ผู้ดูแล</td>
                <td>สั่งเปิดใช้งาน (Active) หรือปิดใช้งาน (Inactive) เอกสาร และสั่ง Rebuild ดัชนี</td>
            </tr>
            <tr>
                <td><code>/api/admin/documents/delete</code></td>
                <td>POST</td>
                <td>ผู้ดูแล</td>
                <td>ลบไฟล์ PDF ออกจากโฟลเดอร์ uploads และสั่งจัดทำดัชนีใหม่</td>
            </tr>
            <tr>
                <td><code>/api/admin/documents/upload</code></td>
                <td>POST</td>
                <td>ผู้ดูแล</td>
                <td>รับข้อมูลไบนารีไฟล์อัปโหลด PDF ใหม่ และบันทึกลงดิสก์โฟลเดอร์ uploads</td>
            </tr>
            <tr>
                <td><code>/api/admin/feedback</code></td>
                <td>GET</td>
                <td>ผู้ดูแล</td>
                <td>ดึงรายงานข้อเสนอแนะ การประเมินผลความพึงพอใจของบอท</td>
            </tr>
            <tr>
                <td><code>/api/admin/feedback/submit</code></td>
                <td>POST</td>
                <td>ทั่วไป</td>
                <td>บันทึกคะแนน Like / Dislike หรือความคิดเห็นจากหน้าจอบทสนทนา</td>
            </tr>
            <tr>
                <td><code>/api/admin/unanswered</code></td>
                <td>GET</td>
                <td>ผู้ดูแล</td>
                <td>เรียกดูรายการคำถามที่บอทหาคำตอบในคลังเอกสารสวัสดิการไม่เจอ</td>
            </tr>
            <tr>
                <td><code>/api/admin/unanswered/resolve</code></td>
                <td>POST</td>
                <td>ผู้ดูแล</td>
                <td>เปลี่ยนสถานะคำถามที่ผู้ดูแลแก้ไขหรือจัดการคำตอบให้แล้ว (Resolved)</td>
            </tr>
            <tr>
                <td><code>/api/admin/history</code></td>
                <td>GET</td>
                <td>ผู้ดูแล</td>
                <td>เรียกประวัติบันทึกการคุยของบอทและข้อมูลความเร็วในการตอบสนอง</td>
            </tr>
        </tbody>
    </table>

    <div class="page-break"></div>
    <div class="header-tag">คู่มือระบบสารสนเทศ TUH Chatbot AI Backend Server (พ.ศ. 2569)</div>

    <h1>2. ระบบฐานข้อมูล JSON และการจัดการสถานะเอกสาร</h1>
    <p>
        เพื่อรักษาความเรียบง่ายและเป็นอิสระจาก DBMS ขนาดใหญ่ ระบบเลือกจัดเก็บข้อมูลการตั้งค่าและล็อกการทำงานในรูปแบบไฟล์ JSON ท้องถิ่น (Local JSON Files) ภายใต้โฟลเดอร์ <code>user/backend/db/</code> ซึ่งมีโครงสร้างหลัก 5 ไฟล์ ได้แก่:
    </p>

    <h2>2.1 รายละเอียดไฟล์ฐานข้อมูลภายใน</h2>
    <ul>
        <li><strong><code>db_settings.json</code>:</strong> จัดเก็บพารามิเตอร์การตั้งค่า AI ได้แก่ คีย์ Gemini API, ชื่อโมเดล (เช่น <code>gemini-2.5-flash</code> หรือ <code>qwen2.5:3b</code>), ค่าความสุ่มคำตอบ (Temperature), ข้อความต้อนรับเริ่มแรก และรายการคำถาม-คำตอบยอดนิยม (Predefined & Custom FAQs)</li>
        <li><strong><code>db_documents.json</code>:</strong> ลิสต์ข้อมูลเอกสาร PDF ทั้งหมดในระบบ ขนาดไฟล์ สถานะเปิด/ปิดการใช้งาน วันที่นำเข้า และรายการหมายเลขหน้าที่ไม่ให้ระบบนำไปตอบคำถาม (<code>exclude_pages</code>)</li>
        <li><strong><code>db_history.json</code>:</strong> เก็บบันทึกข้อมูลความถี่การใช้งานเพื่อความปลอดภัยย้อนหลัง 1,000 รายการล่าสุด ประกอบด้วยเนื้อหาคำถาม คำตอบที่ส่งกลับไป รหัสชิ้นส่วนเนื้อหาอ้างอิง (chunk_ids) โมเดล AI ที่ตอบ และเวลาที่ใช้ประมวลผล</li>
        <li><strong><code>db_feedback.json</code>:</strong> ล็อกคะแนนความพอใจและข้อเสนอแนะเพื่อนำมาวิเคราะห์ปรับปรุงประสิทธิภาพ</li>
        <li><strong><code>db_unanswered.json</code>:</strong> เก็บบันทึกคำถามที่ไม่พบข้อมูลในคลังเอกสารสวัสดิการ โดยจะนับความถี่ (count) และระบุสถานะงานค้างเพื่อเป็นตัวชี้วัดในการปรับปรุงคลังข้อมูลในอนาคต</li>
    </ul>

    <h2>2.2 การประมวลผลยกเว้นหน้าเอกสาร (Exclude Pages Setup)</h2>
    <p>
        ในระบบ <code>db_documents.json</code> ผู้ดูแลสามารถระบุอาเรย์เลขหน้า เช่น <code>"exclude_pages": [12, 13, 14, 18]</code> สำหรับกั้นหน้าเอกสารที่มีข้อมูลไม่เกี่ยวข้องหรือไม่ประสงค์จะให้หลุดเข้าไปในการประมวลผล RAG 
        โดยตัวรันดัชนี <code>rebuild_db.py</code> จะเช็กค่าชุดนี้ก่อนรวบรวมเนื้อหาเสมอ:
    </p>
    <div class="alert alert-note">
        <strong>ข้อสังเกต:</strong> หากผู้ใช้ตั้งค่าปิดไม่เอาบางหน้า (เช่น หน้าลงลายมือชื่อพยานท้ายระเบียบ) ระบบจะสแกนข้ามหน้านั้น ๆ ตั้งแต่ตอนสกัดข้อความดิบ ทำให้ผลลัพธ์เวกเตอร์ FAISS และ BM25 ไม่มีชิ้นส่วนเนื้อหาเหล่านั้นผสมอยู่
    </div>

    <h1>3. ระบบ Hybrid Retrieval Search (FAISS + BM25)</h1>
    <p>
        เพื่อให้บอทมีความเข้าใจทั้งคำศัพท์เฉพาะและบริบทความหมาย ระบบจึงประยุกต์ใช้การทำดัชนีแบบ <strong>Hybrid Retrieval</strong> โดยรวมจุดเด่นของสองระบบเข้าด้วยกัน:
    </p>
    <ol>
        <li><strong>Dense Retrieval (ค้นหาจากความหมาย):</strong> นำเนื้อหามาแปลงเป็นตัวเลขเวกเตอร์หนาแน่นผ่านโมเดล <code>BAAI/bge-m3</code> และจัดเก็บดัชนีด้วย <code>FAISS</code> (ใช้ดัชนี Flat Inner Product สำหรับ Cosine Similarity หลังจากทำการ Normalize L2)</li>
        <li><strong>Lexical Retrieval (ค้นหาจากคำตรงคีย์เวิร์ด):</strong> นำเนื้อหามาตัดคำภาษาไทยด้วยโมดูล <code>word_tokenize</code> (PyThaiNLP) และจัดทำดัชนีเก็บความถี่คำสำคัญด้วยสูตร <code>BM25Okapi</code></li>
    </ol>

    <h2>3.1 สูตรการผสานคะแนนด้วย Reciprocal Rank Fusion (RRF)</h2>
    <p>
        เมื่อคำค้นหาของฝั่ง Client ส่งเข้ามา ระบบจะเรียกใช้งานทั้ง FAISS และ BM25 ขนานกันเพื่อค้นหาดัชนีที่คะแนนสูงที่สุด จากนั้นนำลำดับ (Rank) ของผลลัพธ์มาคำนวณคะแนนประสมเพื่อจัดอันดับใหม่ (Rerank) ตามน้ำหนักความเชื่อมั่นผ่านฟังก์ชัน RRF:
    </p>
    <pre># สูตรคำนวณ RRF ถ่วงน้ำหนักเชิงอันดับ
RRF_Score = Weight * (1.0 / (RRF_K + Rank))</pre>
    <p>
        โดยระบบใช้น้ำหนักสำหรับ <strong>BM25 (ค้นหาคำตรง) อยู่ที่ 0.6</strong> และ <strong>Vector (ค้นหาความหมาย) อยู่ที่ 0.4</strong> โดยมีค่าคงที่เพื่อความเสถียร <code>RRF_K = 60</code> เอกสารที่ได้รับความสนใจสูงจากทั้งสองฝั่งจะมีคะแนน RRF สูงสุดและถูกตัดส่งไปยัง AI ตอบกลับ
    </p>

    <div class="page-break"></div>
    <div class="header-tag">คู่มือระบบสารสนเทศ TUH Chatbot AI Backend Server (พ.ศ. 2569)</div>

    <h1>4. การทำงานเชื่อมต่อกับโมเดล Generative AI</h1>
    <p>
        ระบบหลังบ้านได้รับการออกแบบให้มีความทนทานและยืดหยุ่นสูง โดยมีตัวเลือกการประมวลผลโมเดลภาษา 3 ช่องทางหลัก ขึ้นอยู่กับการมีตัวตนของคีย์และความเร็วอินเทอร์เน็ต:
    </p>

    <h2>4.1 สถาปัตยกรรมการส่งข้อมูลประวัติความจำ (Short-term Conversation History)</h2>
    <p>
        ตามคำร้องขอปัจจุบัน ฝั่ง Frontend จะแนบอาเรย์ <code>history</code> ล่าสุดย้อนหลัง 2 Turn (สูงสุด 4 ข้อความล่าสุด) ส่งเข้ามาใน Payload ของ POST Request ฝั่ง Backend Server จะทำการแปลงประวัติการสนทนานี้ให้เข้ากับฟอร์แมตของแต่ละคลาวด์เพื่อสร้างความต่อเนื่องในการสื่อสาร:
    </p>

    <h3>การแปลงข้อมูลสำหรับ Google Gemini API (คลาวด์ตรง)</h3>
    <p>
        แปลงเป็นรูปแบบข้อมูลอาเรย์ของออบเจกต์ที่มี <code>role: "user"</code> และ <code>role: "model"</code> สลับกัน พร้อมส่ง <code>systemInstruction</code> แยกต่างหากเพื่อให้คลาวด์ตอบกลับตามกฎที่เข้มงวด:
    </p>
    <pre>gemini_contents = [
    {"role": "user", "parts": [{"text": "ประวัติคำถามรอบที่ 1"}]},
    {"role": "model", "parts": [{"text": "ประวัติคำตอบรอบที่ 1"}]},
    {"role": "user", "parts": [{"text": "บริบทอ้างอิง + คำถามปัจจุบัน"}]}
]</pre>

    <h3>การแปลงข้อมูลสำหรับ OpenRouter / Local Ollama (OpenAI Format)</h3>
    <p>
        แปลงเป็นรูปแบบระบบข้อความที่มี <code>role: "system"</code>, <code>role: "user"</code> และ <code>role: "assistant"</code> สลับกันเพื่อความครอบคลุม:
    </p>
    <pre>openai_messages = [
    {"role": "system", "content": "ค่านิยมคำสั่งระบบ..."},
    {"role": "user", "content": "คำถามย้อนหลัง..."},
    {"role": "assistant", "content": "คำตอบย้อนหลัง..."},
    {"role": "user", "content": "บริบทอ้างอิง + คำถามปัจจุบัน"}
]</pre>

    <h2>4.2 ระบบดึงข้อความอ้างอิงตอบกลับเมื่อเซิร์ฟเวอร์ AI ออฟไลน์ (Fallback System)</h2>
    <p>
        หากระบบ AI ล่ม ไม่มีอินเทอร์เน็ต หรือตั้งค่าคีย์ API ผิดพลาด ระบบหลังบ้านจะไม่หยุดตอบคำถาม แต่จะมีกระบวนการพิเศษ <strong>Fallback Response</strong> โดยดึงข้อมูลจากชิ้นส่วนที่ RAG ค้นหาได้คะแนน RRF สูงสุดขึ้นมาแสดงผลตรง ๆ บนหน้าต่างแชททันที พร้อมกำกับระบุเลขหน้าและไฟล์เอกสารอ้างอิง เพื่อให้ผู้ใช้งานไม่พลาดข้อมูลสวัสดิการที่ต้องการค้นหา
    </p>

    <h1>5. ระบบงานเบื้องหลังและการสลับเปิดปิดเอกสาร (Asynchronous Rebuild)</h1>
    <p>
        เมื่อผู้ดูแลระบบสลับค่าการเปิด/ปิดไฟล์ระเบียบ หรือลบไฟล์ออกจากระบบ แผงควบคุมจะส่งการร้องขอมาที่เส้นทาง API ของ Admin ซึ่งจะต้องจัดทำดัชนีฐานข้อมูล RAG ใหม่เพื่อให้คลังข้อมูลเวกเตอร์อัปเดตตรงตามจริง
    </p>
    <p>
        เนื่องจากการโหลดโมเดล BAAI/bge-m3 และทำเวกเตอร์ Embedding ให้เอกสารทั้งหมดใช้เวลาและหน่วยประมวลผลสูง (อาจใช้เวลา 10-40 วินาที) หากประมวลผลบนเธรดหลักจะทำให้ระบบเกิดสภาวะหน้าจอค้างและ API ทราฟฟิกชะงัก (Gateway Timeout) 
        เซิร์ฟเวอร์จึงเลือกแก้ปัญหานี้ด้วยการสั่งรันสคริปต์เบื้องหลังผ่านฟังก์ชันมัลติเธรดของ Python:
    </p>
    <pre># การจัดทำดัชนีใหม่แบบอซิงโครนัสผ่าน Threading
import threading
threading.Thread(target=rebuild_vector_indices).start()</pre>
    <p>
        ฟังก์ชันนี้จะเรียกใช้งานโมดูล <code>subprocess.run(["py", "rebuild_db.py"])</code> ในเธรดแยกอิสระ ทำให้ API หลักสามารถส่งสัญญาณตอบกลับฝั่งแอดมินเพจว่า "ดำเนินการเริ่ม Rebuild แล้ว" ได้ในทันทีภายในเวลาเพียง 5 มิลลิวินาที ในขณะที่เธรดเบื้องหลังจะยังทำงานสืบค้นและทำดัชนีต่อไปอย่างราบรื่น
    </p>

    <div class="alert alert-tip">
        <strong>ข้อมูลสำคัญ:</strong> เมื่อสคริปต์ <code>rebuild_db.py</code> เบื้องหลังรันเสร็จสมบูรณ์ ระบบจะทำการโหลดตัวดึงข้อมูล <code>HybridRetriever</code> ตัวใหม่เข้าสู่แรม (Global Variable) เพื่อเปิดรับคำสั่งค้นหา RAG ชุดใหม่ให้ทันทีโดยผู้ใช้งานบนหน้าเว็บฝั่งหน้าบ้านไม่ต้องรีเฟรชหน้าเบราว์เซอร์แต่อย่างใด
    </div>

</body>
</html>
"""

    temp_dir = tempfile.gettempdir()
    temp_html_path = os.path.join(temp_dir, "backend_guide_temp.html")
    temp_pdf_path = os.path.join(temp_dir, "backend_server_guide.pdf")

    # Clean up old temporary files if they exist
    for p in [temp_html_path, temp_pdf_path]:
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass

    with open(temp_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"📄 Generated temporary HTML layout at: {temp_html_path}")

    # Search for Chrome or Edge to print to PDF
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
        # Fallback search in path
        executable = "msedge"

    print(f"🎬 Running headless print via: {executable}")
    cmd = [
        executable,
        "--headless",
        "--disable-gpu",
        f"--print-to-pdf={temp_pdf_path}",
        "--no-margins",
        "--print-to-pdf-no-header",
        temp_html_path
    ]

    try:
        # Use a short timeout to prevent hanging
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        # Verify file exists on C:
        if os.path.exists(temp_pdf_path):
            print(f"✅ PDF successfully generated at temp: {temp_pdf_path}")
            
            # Copy to final project workspace destination on Z:
            admin_dir = os.path.dirname(os.path.abspath(__file__))
            final_pdf_path = os.path.join(admin_dir, "backend_server_guide.pdf")
            
            shutil.copy2(temp_pdf_path, final_pdf_path)
            print(f"🎉 Success! Copied final PDF to: {final_pdf_path}")
        else:
            print("❌ Failed to generate PDF. Output file not found in local temp.")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
    except Exception as e:
        print(f"❌ Error compiling PDF: {e}")
    finally:
        # Clean up temporary html on C:
        if os.path.exists(temp_html_path):
            try:
                os.remove(temp_html_path)
            except Exception:
                pass
        # Clean up temporary pdf on C:
        if os.path.exists(temp_pdf_path):
            try:
                os.remove(temp_pdf_path)
            except Exception:
                pass

if __name__ == "__main__":
    build_pdf()
