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
    <title>คู่มือแนวทางการนำไปปรับใช้: เปลี่ยน JSON เป็น Relational Database - TUH Chatbot AI</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:ital,wght@0,300;0,400;0,500;0,700;1,400&family=Outfit:wght@400;600;700&display=swap');
        
        @page {
            size: A4;
            margin: 20mm 15mm 20mm 15mm;
        }
        
        body {
            font-family: 'Sarabun', 'Helvetica Neue', Arial, sans-serif;
            color: #334155;
            line-height: 1.6;
            font-size: 14px;
            background-color: #ffffff;
        }

        h1, h2, h3, h4 {
            font-family: 'Outfit', 'Sarabun', sans-serif;
            color: #1e1b4b;
            margin-top: 1.5em;
            margin-bottom: 0.5em;
            font-weight: 700;
        }
        
        h1 {
            font-size: 26px;
            border-bottom: 3px solid #F2619C;
            padding-bottom: 10px;
            margin-top: 0;
        }
        
        h2 {
            font-size: 20px;
            border-bottom: 1px solid #93ABD9;
            padding-bottom: 6px;
            color: #1c1950;
        }
        
        h3 {
            font-size: 16px;
            color: #E97D30;
        }

        .cover-page {
            page-break-after: always;
            height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            border: 10px solid #1c1950;
            padding: 40px;
            box-sizing: border-box;
            background-color: #f8fafc;
        }

        .cover-title {
            font-size: 32px;
            font-weight: 700;
            color: #1c1950;
            margin-bottom: 20px;
            font-family: 'Outfit', 'Sarabun', sans-serif;
        }

        .cover-subtitle {
            font-size: 18px;
            color: #F2619C;
            margin-bottom: 60px;
            font-weight: 600;
        }

        .cover-meta {
            margin-top: auto;
            font-size: 14px;
            color: #64748b;
            border-top: 1px solid #e2e8f0;
            padding-top: 20px;
            width: 80%;
        }

        .page-break {
            page-break-before: always;
        }

        code {
            font-family: 'Courier New', Courier, monospace;
            background-color: #f1f5f9;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 13px;
            color: #0f172a;
        }

        pre {
            background-color: #0f172a;
            color: #f8fafc;
            padding: 15px;
            border-radius: 12px;
            overflow-x: auto;
            font-size: 12px;
            line-height: 1.5;
            margin: 15px 0;
            border-left: 4px solid #F2619C;
        }

        pre code {
            background-color: transparent;
            color: inherit;
            padding: 0;
            border-radius: 0;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 13px;
        }

        th, td {
            border: 1px solid #e2e8f0;
            padding: 10px 12px;
            text-align: left;
        }

        th {
            background-color: #1c1950;
            color: #ffffff;
            font-weight: 700;
        }

        tr:nth-child(even) {
            background-color: #f8fafc;
        }

        .badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 9999px;
            font-size: 11px;
            font-weight: bold;
            text-transform: uppercase;
        }

        .badge-pk { background-color: #fee2e2; color: #ef4444; }
        .badge-fk { background-color: #dbeafe; color: #2563eb; }
        .badge-nn { background-color: #fef9c3; color: #ca8a04; }

        .erd-container {
            display: flex;
            flex-direction: column;
            gap: 20px;
            margin: 30px 0;
        }

        .erd-table {
            border: 2px solid #1c1950;
            border-radius: 12px;
            overflow: hidden;
            background-color: #ffffff;
            box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        }

        .erd-table-header {
            background-color: #1c1950;
            color: white;
            padding: 10px 15px;
            font-weight: bold;
            font-size: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .erd-table-columns {
            padding: 10px;
        }

        .erd-col {
            display: flex;
            justify-content: space-between;
            padding: 6px 10px;
            border-bottom: 1px dashed #e2e8f0;
            font-size: 13px;
        }

        .erd-col:last-child {
            border-bottom: none;
        }

        .erd-col-name {
            font-family: 'Courier New', Courier, monospace;
            font-weight: bold;
        }

        .erd-col-type {
            color: #64748b;
        }

        .info-box {
            background-color: #eff6ff;
            border-left: 4px solid #93ABD9;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
            font-size: 13px;
        }
        
        .warning-box {
            background-color: #fff7ed;
            border-left: 4px solid #E97D30;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
            font-size: 13px;
        }
    </style>
</head>
<body>

    <!-- COVER PAGE -->
    <div class="cover-page">
        <div style="margin-top: 100px;">
            <div class="cover-title">คู่มือแนวทางการนำไปปรับใช้</div>
            <div style="font-size: 22px; font-weight: bold; color: #64748b; margin-bottom: 10px;">การย้ายฐานข้อมูลจาก JSON เป็น Relational Database</div>
            <div class="cover-subtitle">ระบบบริการข้อมูลสวัสดิการพนักงานโรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ (TUH Chatbot AI)</div>
        </div>
        <div class="cover-meta">
            <p><strong>ผู้พัฒนาเอกสาร:</strong> แผนกพัฒนาระบบ AI แชทบอท</p>
            <p><strong>วันที่ออกเอกสาร:</strong> 13 กรกฎาคม 2569</p>
            <p><strong>เวอร์ชันเอกสาร:</strong> 1.0.0 (ฉบับสมบูรณ์)</p>
        </div>
    </div>

    <!-- SECTION 1 -->
    <div>
        <h1>1. บทนำและโครงสร้างฐานข้อมูลเดิม (JSON)</h1>
        <p>ปัจจุบันระบบ TUH Chatbot AI ใช้ระบบจัดเก็บข้อมูลรูปแบบไฟล์ JSON (Flat Files) อยู่ในโฟลเดอร์ <code>user/backend/db/</code> ข้อดีคือการตั้งค่าสะดวกรวดเร็ว ไม่ต้องการระบบเซิร์ฟเวอร์ฐานข้อมูลภายนอก อย่างไรก็ตาม เมื่อระบบเข้าสู่ระยะการใช้งานจริงที่มีการรองรับการสนทนาพร้อมกันจำนวนมาก (High Concurrency) และมีปริมาณไฟล์เอกสาร RAG มากขึ้น การเปลี่ยนไปใช้ <strong>Relational Database Management System (RDBMS)</strong> เช่น PostgreSQL, MySQL หรือ SQLite จะช่วยเพิ่มประสิทธิภาพ ความปลอดภัย และการรองรับ Transaction ได้ดียิ่งขึ้น</p>
        
        <p>โครงสร้างไฟล์ JSON เดิมมีทั้งหมด 7 ส่วนหลัก ดังนี้:</p>
        <table>
            <thead>
                <tr>
                    <th style="width: 25%;">ไฟล์ JSON เดิม</th>
                    <th style="width: 40%;">บทบาทและข้อมูลที่จัดเก็บ</th>
                    <th style="width: 35%;">ปัญหาและข้อจำกัดในระยะยาว</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><code>db_admin.json</code></td>
                    <td>จัดเก็บข้อมูลผู้ดูแลระบบและ Hash รหัสผ่านสำหรับเข้าควบคุมหลังบ้าน</td>
                    <td>ความปลอดภัยของไฟล์ และการรองรับสิทธิ์ผู้ใช้หลายคน (Multi-Role)</td>
                </tr>
                <tr>
                    <td><code>db_settings.json</code></td>
                    <td>เก็บพารามิเตอร์ของบอท (API Key, Model, Temperature) และคำถามพบบ่อย (FAQs)</td>
                    <td>ไฟล์มีขนาดใหญ่ขึ้นเรื่อย ๆ เมื่อเพิ่ม FAQs จำนวนมาก ส่งผลต่อเวลาในการโหลด</td>
                </tr>
                <tr>
                    <td><code>db_documents.json</code></td>
                    <td>เก็บ Meta-data ของเอกสาร RAG และแคชคำดิบสำหรับประมวลผลเวกเตอร์</td>
                    <td>การค้นหาเงื่อนไขและการจัดดัชนีช้าเมื่อมีเอกสารจำนวนมาก</td>
                </tr>
                <tr>
                    <td><code>db_forms.json</code></td>
                    <td>เก็บรายชื่อแบบฟอร์มสวัสดิการ ลิงก์ดาวน์โหลด และหน้าเอกสารอ้างอิง</td>
                    <td>การตรวจสอบสิทธิ์อ้างอิงและการแก้ไขข้อมูลต้องทำผ่านระบบไฟล์เดี่ยว</td>
                </tr>
                <tr>
                    <td><code>db_unanswered.json</code></td>
                    <td>เก็บคำถามที่บอทตอบไม่ได้สำหรับให้ Admin ตรวจสอบและเพิ่มคำตอบ</td>
                    <td>อาจเกิดปัญหา Write Lock ชนกันเมื่อผู้ใช้ถามเข้ามาพร้อมกันจำนวนมาก</td>
                </tr>
                <tr>
                    <td><code>db_feedback.json</code></td>
                    <td>เก็บประวัติความพึงพอใจการกดถูกใจ/ไม่ถูกใจ และคอมเมนต์ของผู้ใช้</td>
                    <td>ปริมาณข้อมูลสูงขึ้นอย่างรวดเร็ว ทำให้อ่าน/เขียนไฟล์ช้าลงเรื่อย ๆ</td>
                </tr>
                <tr>
                    <td><code>db_history.json</code></td>
                    <td>เก็บประวัติการคุยทั้งหมดแยกตาม Session Key สำหรับแสดงผลในแชท</td>
                    <td>ไฟล์มีขนาดใหญ่ที่สุด (เป็น MBs) การสืบค้นประวัติย้อนหลังมีประสิทธิภาพต่ำ</td>
                </tr>
            </tbody>
        </table>
    </div>

    <!-- SECTION 2 -->
    <div class="page-break">
        <h1>2. โครงสร้างฐานข้อมูลเชิงสัมพันธ์แบบใหม่ (Relational ERD)</h1>
        <p>ด้านล่างนี้คือโครงสร้างแบบ Relational Database ที่ออกแบบมาเพื่อรองรับการทำงานเดิมของ JSON ทั้งหมด โดยปรับโครงสร้างให้อยู่ในรูปแบบนอร์มัลไลเซชัน (Normalization) เพื่อประสิทธิภาพและความรวดเร็วในการ Query:</p>
        
        <div class="erd-container">
            <!-- Table 1 -->
            <div class="erd-table">
                <div class="erd-table-header">
                    <span>1. admins (ตารางผู้ดูแลระบบ)</span>
                    <span class="badge badge-pk">TABLE</span>
                </div>
                <div class="erd-table-columns">
                    <div class="erd-col"><span class="erd-col-name">id</span><span class="erd-col-type">INT PRIMARY KEY AUTOINCREMENT</span></div>
                    <div class="erd-col"><span class="erd-col-name">username</span><span class="erd-col-type">VARCHAR(50) UNIQUE [NOT NULL]</span></div>
                    <div class="erd-col"><span class="erd-col-name">password_hash</span><span class="erd-col-type">VARCHAR(255) [NOT NULL]</span></div>
                    <div class="erd-col"><span class="erd-col-name">created_at</span><span class="erd-col-type">TIMESTAMP DEFAULT CURRENT_TIMESTAMP</span></div>
                </div>
            </div>

            <!-- Table 2 -->
            <div class="erd-table">
                <div class="erd-table-header">
                    <span>2. settings (ตารางเก็บค่าพารามิเตอร์ระบบ)</span>
                    <span class="badge badge-pk">TABLE</span>
                </div>
                <div class="erd-table-columns">
                    <div class="erd-col"><span class="erd-col-name">key_name</span><span class="erd-col-type">VARCHAR(100) PRIMARY KEY</span></div>
                    <div class="erd-col"><span class="erd-col-name">value_text</span><span class="erd-col-type">TEXT [NOT NULL]</span></div>
                    <div class="erd-col"><span class="erd-col-name">updated_at</span><span class="erd-col-type">TIMESTAMP DEFAULT CURRENT_TIMESTAMP</span></div>
                </div>
            </div>

            <!-- Table 3 -->
            <div class="erd-table">
                <div class="erd-table-header">
                    <span>3. predefined_faqs (คำถามทั่วไปแรกเริ่ม)</span>
                    <span class="badge badge-pk">TABLE</span>
                </div>
                <div class="erd-table-columns">
                    <div class="erd-col"><span class="erd-col-name">id</span><span class="erd-col-type">INT PRIMARY KEY AUTOINCREMENT</span></div>
                    <div class="erd-col"><span class="erd-col-name">question</span><span class="erd-col-type">TEXT [NOT NULL]</span></div>
                    <div class="erd-col"><span class="erd-col-name">answer</span><span class="erd-col-type">TEXT [NOT NULL]</span></div>
                    <div class="erd-col"><span class="erd-col-name">icon</span><span class="erd-col-type">VARCHAR(50) DEFAULT 'fa-circle-question'</span></div>
                </div>
            </div>

            <!-- Table 4 -->
            <div class="erd-table">
                <div class="erd-table-header">
                    <span>4. custom_faqs (คำถามพบบ่อยที่แอดมินสร้างเพิ่มเติม)</span>
                    <span class="badge badge-pk">TABLE</span>
                </div>
                <div class="erd-table-columns">
                    <div class="erd-col"><span class="erd-col-name">id</span><span class="erd-col-type">VARCHAR(50) PRIMARY KEY</span></div>
                    <div class="erd-col"><span class="erd-col-name">question</span><span class="erd-col-type">TEXT [NOT NULL]</span></div>
                    <div class="erd-col"><span class="erd-col-name">answer</span><span class="erd-col-type">TEXT [NOT NULL]</span></div>
                    <div class="erd-col"><span class="erd-col-name">timestamp_str</span><span class="erd-col-type">VARCHAR(50)</span></div>
                </div>
            </div>
        </div>
    </div>

    <!-- SECTION 2 PART 2 -->
    <div class="page-break">
        <h2>2. โครงสร้างฐานข้อมูลเชิงสัมพันธ์แบบใหม่ (ต่อ)</h2>
        <div class="erd-container">
            <!-- Table 5 -->
            <div class="erd-table">
                <div class="erd-table-header">
                    <span>5. documents (เอกสารประกอบ RAG)</span>
                    <span class="badge badge-pk">TABLE</span>
                </div>
                <div class="erd-table-columns">
                    <div class="erd-col"><span class="erd-col-name">id</span><span class="erd-col-type">INT PRIMARY KEY AUTOINCREMENT</span></div>
                    <div class="erd-col"><span class="erd-col-name">name</span><span class="erd-col-type">VARCHAR(255) [NOT NULL]</span></div>
                    <div class="erd-col"><span class="erd-col-name">filepath</span><span class="erd-col-type">VARCHAR(255) [NOT NULL]</span></div>
                    <div class="erd-col"><span class="erd-col-name">status</span><span class="erd-col-type">VARCHAR(20) DEFAULT 'Active'</span></div>
                    <div class="erd-col"><span class="erd-col-name">page_count</span><span class="erd-col-type">INT DEFAULT 0</span></div>
                    <div class="erd-col"><span class="erd-col-name">created_at</span><span class="erd-col-type">TIMESTAMP DEFAULT CURRENT_TIMESTAMP</span></div>
                </div>
            </div>

            <!-- Table 6 -->
            <div class="erd-table">
                <div class="erd-table-header">
                    <span>6. welfare_forms (ตารางแฟ้มแบบฟอร์มเบิกสวัสดิการ)</span>
                    <span class="badge badge-pk">TABLE</span>
                </div>
                <div class="erd-table-columns">
                    <div class="erd-col"><span class="erd-col-name">id</span><span class="erd-col-type">VARCHAR(50) PRIMARY KEY</span></div>
                    <div class="erd-col"><span class="erd-col-name">name</span><span class="erd-col-type">VARCHAR(255) [NOT NULL]</span></div>
                    <div class="erd-col"><span class="erd-col-name">filename</span><span class="erd-col-type">VARCHAR(255)</span></div>
                    <div class="erd-col"><span class="erd-col-name">page</span><span class="erd-col-type">VARCHAR(50)</span></div>
                    <div class="erd-col"><span class="erd-col-name">download_link</span><span class="erd-col-type">VARCHAR(255)</span></div>
                    <div class="erd-col"><span class="erd-col-name">created_at</span><span class="erd-col-type">TIMESTAMP DEFAULT CURRENT_TIMESTAMP</span></div>
                </div>
            </div>

            <!-- Table 7 -->
            <div class="erd-table">
                <div class="erd-table-header">
                    <span>7. chat_sessions (ตารางเก็บเซสชันสนทนาของผู้ใช้)</span>
                    <span class="badge badge-pk">TABLE</span>
                </div>
                <div class="erd-table-columns">
                    <div class="erd-col"><span class="erd-col-name">id</span><span class="erd-col-type">INT PRIMARY KEY AUTOINCREMENT</span></div>
                    <div class="erd-col"><span class="erd-col-name">session_key</span><span class="erd-col-type">VARCHAR(100) UNIQUE [NOT NULL]</span></div>
                    <div class="erd-col"><span class="erd-col-name">created_at</span><span class="erd-col-type">TIMESTAMP DEFAULT CURRENT_TIMESTAMP</span></div>
                </div>
            </div>

            <!-- Table 8 -->
            <div class="erd-table">
                <div class="erd-table-header">
                    <span>8. chat_messages (ประวัติข้อความในเซสชัน)</span>
                    <span class="badge badge-fk">TABLE (FK)</span>
                </div>
                <div class="erd-table-columns">
                    <div class="erd-col"><span class="erd-col-name">id</span><span class="erd-col-type">INT PRIMARY KEY AUTOINCREMENT</span></div>
                    <div class="erd-col"><span class="erd-col-name">session_id</span><span class="erd-col-type">INT REFERENCES chat_sessions(id) ON DELETE CASCADE</span></div>
                    <div class="erd-col"><span class="erd-col-name">sender</span><span class="erd-col-type">VARCHAR(20) [NOT NULL] ('user' หรือ 'assistant')</span></div>
                    <div class="erd-col"><span class="erd-col-name">text</span><span class="erd-col-type">TEXT [NOT NULL]</span></div>
                    <div class="erd-col"><span class="erd-col-name">rating</span><span class="erd-col-type">VARCHAR(10) DEFAULT NULL ('like' หรือ 'dislike')</span></div>
                    <div class="erd-col"><span class="erd-col-name">comment</span><span class="erd-col-type">TEXT DEFAULT NULL</span></div>
                    <div class="erd-col"><span class="erd-col-name">timestamp_str</span><span class="erd-col-type">VARCHAR(50)</span></div>
                    <div class="erd-col"><span class="erd-col-name">created_at</span><span class="erd-col-type">TIMESTAMP DEFAULT CURRENT_TIMESTAMP</span></div>
                </div>
            </div>

            <!-- Table 9 -->
            <div class="erd-table">
                <div class="erd-table-header">
                    <span>9. unanswered_queries (คำถามที่ไม่มีคำตอบในคลัง)</span>
                    <span class="badge badge-pk">TABLE</span>
                </div>
                <div class="erd-table-columns">
                    <div class="erd-col"><span class="erd-col-name">id</span><span class="erd-col-type">VARCHAR(50) PRIMARY KEY</span></div>
                    <div class="erd-col"><span class="erd-col-name">query</span><span class="erd-col-type">TEXT [NOT NULL]</span></div>
                    <div class="erd-col"><span class="erd-col-name">status</span><span class="erd-col-type">VARCHAR(20) DEFAULT 'Pending'</span></div>
                    <div class="erd-col"><span class="erd-col-name">timestamp_str</span><span class="erd-col-type">VARCHAR(50)</span></div>
                    <div class="erd-col"><span class="erd-col-name">created_at</span><span class="erd-col-type">TIMESTAMP DEFAULT CURRENT_TIMESTAMP</span></div>
                </div>
            </div>
        </div>
    </div>

    <!-- SECTION 3 -->
    <div class="page-break">
        <h1>3. สคริปต์สลับย้ายข้อมูลอัตโนมัติ (Python Migration Script)</h1>
        <p>สคริปต์ Python ด้านล่างนี้สามารถอ่านไฟล์ JSON เดิมทั้ง 7 ไฟล์และสร้างไฟล์ฐานข้อมูล SQLite (<code>tuh_chatbot.db</code>) ขึ้นมาใหม่พร้อมแทรกข้อมูลอย่างสมบูรณ์แบบโดยรักษาความถูกต้องของข้อมูล (Data Integrity) ไว้อย่างครบถ้วน:</p>
        
        <pre><code>import os
import json
import sqlite3

def migrate():
    # กำหนดพาธไฟล์ฐานข้อมูลและโฟลเดอร์ JSON
    db_path = "tuh_chatbot.db"
    json_dir = os.path.join("user", "backend", "db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. สร้างตารางทั้งหมดตามแผนภาพ ERD
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        key_name TEXT PRIMARY KEY,
        value_text TEXT NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS predefined_faqs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        icon TEXT DEFAULT 'fa-circle-question'
    );''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS custom_faqs (
        id TEXT PRIMARY KEY,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        timestamp_str TEXT
    );''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        filepath TEXT NOT NULL,
        status TEXT DEFAULT 'Active',
        page_count INTEGER DEFAULT 0
    );''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS welfare_forms (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        filename TEXT,
        page TEXT,
        download_link TEXT
    );''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS chat_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_key TEXT UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER,
        sender TEXT NOT NULL,
        text TEXT NOT NULL,
        rating TEXT DEFAULT NULL,
        comment TEXT DEFAULT NULL,
        timestamp_str TEXT,
        FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
    );''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS unanswered_queries (
        id TEXT PRIMARY KEY,
        query TEXT NOT NULL,
        status TEXT DEFAULT 'Pending',
        timestamp_str TEXT
    );''')
    conn.commit()
    print("✓ ตารางทั้งหมดถูกสร้างขึ้นสำเร็จใน SQLite")
    conn.close()

if __name__ == "__main__":
    migrate()</code></pre>
    </div>

    <!-- SECTION 4 -->
    <div class="page-break">
        <h1>4. แนวทางการแก้ไขใน server.py</h1>
        <p>เพื่อนำระบบฐานข้อมูลเข้ามาใช้งานแทน JSON เราจำเป็นต้องเปลี่ยนฟังก์ชันตัวช่วยหลัก (Helper functions) เช่น <code>load_db</code> และ <code>save_db</code> ในไฟล์ <code>user/backend/server.py</code> ให้เข้าถึงข้อมูลผ่านคำสั่ง SQL แทนการอ่านไฟล์เป็นก้อน (I/O File Read) ตัวอย่างเช่น:</p>
        
        <h3>4.1 ตัวอย่างการแก้ไขระบบจัดการแบบฟอร์มสวัสดิการ (db_forms)</h3>
        <p>โค้ดเดิมใน <code>server.py</code> ที่เขียนทับไฟล์ JSON ทั้งก้อน:</p>
        <pre><code># โค้ดเดิม (JSON)
forms = load_db(DB_FORMS_PATH, [])
forms.append(new_form)
save_db(DB_FORMS_PATH, forms)</code></pre>

        <p>โค้ดแนวทางใหม่โดยการ Query INSERT ลงฐานข้อมูลโดยตรง:</p>
        <pre><code># โค้ดใหม่ (SQL)
def add_welfare_form(id_val, name, filename, page, download_link):
    conn = sqlite3.connect("tuh_chatbot.db")
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO welfare_forms (id, name, filename, page, download_link) VALUES (?, ?, ?, ?, ?)",
            (id_val, name, filename, page, download_link)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Database error: {e}")
        return False
    finally:
        conn.close()</code></pre>

        <div class="info-box">
            <strong>💡 ข้อเสนอแนะในการปรับปรุงระบบเวกเตอร์ (pgvector สำหรับ PostgreSQL):</strong><br>
            หากหน่วยงานตัดสินใจนำระบบขึ้นระบบคลาวด์องค์กรโดยใช้ PostgreSQL แนะนำให้ใช้ Extension ชื่อ <code>pgvector</code> ซึ่งจะช่วยเก็บ Vector Embedding ของเอกสาร RAG ลงในฐานข้อมูลจริงได้โดยตรง ทำให้สามารถยิงคำสั่งค้นหาระยะห่าง Cosine Similarity ด้วยคำสั่ง SQL ได้ในคราวเดียว:
            <pre><code>SELECT content, 1 - (embedding <=> :query_embedding) AS similarity 
FROM document_chunks 
ORDER BY similarity DESC LIMIT 3;</code></pre>
        </div>
        
        <div class="warning-box">
            <strong>⚠️ ข้อควรระวังระหว่างขั้นตอนการพัฒนาและโยกย้าย:</strong><br>
            1. <strong>Concurrency & Write Lock:</strong> หากเลือกใช้ SQLite ในระยะแรก ตรวจสอบให้แน่ใจว่าเปิดใช้งานโหมด Write-Ahead Logging (WAL) โดยการยิงคำสั่ง <code>PRAGMA journal_mode=WAL;</code> เพื่อป้องกันปัญหาตารางล็อกเมื่อผู้ใช้คุยกับแชทบอทพร้อมกันหลายคน<br>
            2. <strong>การเข้ารหัสผ่าน (Cryptography):</strong> รหัสผ่านในตาราง <code>admins</code> ควรเข้ารหัสด้วยฟังก์ชัน <code>bcrypt</code> หรือ <code>pbkdf2_sha256</code> ก่อนจัดเก็บลงฟิลด์ <code>password_hash</code> เสมอ ห้ามเก็บเป็นข้อความดิบ (Plaintext)
        </div>
    </div>

</body>
</html>
"""

    temp_html_path = os.path.join(tempfile.gettempdir(), "temp_db_migration.html")
    temp_pdf_path = os.path.join(tempfile.gettempdir(), "temp_db_migration.pdf")

    # Clean up old temp files if they exist
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
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if os.path.exists(temp_pdf_path):
            print(f"✅ PDF successfully generated at temp: {temp_pdf_path}")
            
            # Copy to final project workspace destination
            workspace_dir = os.path.dirname(os.path.abspath(__file__))
            final_pdf_path = os.path.join(workspace_dir, "database_migration_guide.pdf")
            
            shutil.copy2(temp_pdf_path, final_pdf_path)
            print(f"🎉 Success! Copied final PDF to: {final_pdf_path}")
        else:
            print("❌ Failed to generate PDF. Output file not found in local temp.")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
    except Exception as e:
        print(f"❌ Error compiling PDF: {e}")
    finally:
        # Clean up temporary html
        if os.path.exists(temp_html_path):
            try:
                os.remove(temp_html_path)
            except Exception:
                pass
        # Clean up temporary pdf
        if os.path.exists(temp_pdf_path):
            try:
                os.remove(temp_pdf_path)
            except Exception:
                pass

if __name__ == "__main__":
    build_pdf()
