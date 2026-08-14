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
    <title>คู่มือการตั้งค่าและการย้ายฐานข้อมูลเป็น PostgreSQL - TUH Chatbot AI</title>
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
            font-size: 24px;
            border-bottom: 3px solid #0d9488;
            padding-bottom: 10px;
            margin-top: 0;
        }
        
        h2 {
            font-size: 18px;
            border-bottom: 1px solid #94a3b8;
            padding-bottom: 6px;
            color: #0f172a;
            margin-top: 2em;
        }
        
        h3 {
            font-size: 15px;
            color: #0d9488;
        }

        .cover-page {
            page-break-after: always;
            height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            border: 10px solid #0d9488;
            padding: 40px;
            box-sizing: border-box;
            background-color: #f8fafc;
        }

        .cover-title {
            font-size: 30px;
            font-weight: 700;
            color: #1e1b4b;
            margin-bottom: 15px;
            font-family: 'Outfit', 'Sarabun', sans-serif;
            line-height: 1.3;
        }

        .cover-subtitle {
            font-size: 16px;
            color: #0d9488;
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
            text-align: center;
        }

        .cover-meta p {
            margin: 5px 0;
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
            border-left: 4px solid #0d9488;
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
            background-color: #0d9488;
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

        .info-box {
            background-color: #f0fdfa;
            border-left: 4px solid #0d9488;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
            font-size: 13px;
        }
        
        .warning-box {
            background-color: #fff7ed;
            border-left: 4px solid #ea580c;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
            font-size: 13px;
        }

        .step-list {
            margin: 20px 0;
            padding-left: 0;
            list-style: none;
        }

        .step-item {
            position: relative;
            padding-left: 35px;
            margin-bottom: 20px;
        }

        .step-number {
            position: absolute;
            left: 0;
            top: 2px;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            background-color: #0d9488;
            color: white;
            text-align: center;
            line-height: 24px;
            font-weight: bold;
            font-size: 12px;
        }

        .step-title {
            font-weight: bold;
            font-size: 15px;
            color: #0f172a;
            margin-bottom: 5px;
        }

        .dialog-mockup {
            background-color: #f8fafc;
            border: 1px solid #cbd5e1;
            border-radius: 8px;
            padding: 15px;
            margin: 15px 0;
            font-size: 13px;
        }

        .dialog-row {
            display: flex;
            margin-bottom: 10px;
        }

        .dialog-label {
            width: 150px;
            font-weight: bold;
            color: #475569;
        }

        .dialog-input {
            flex: 1;
            background-color: white;
            border: 1px solid #cbd5e1;
            padding: 4px 8px;
            border-radius: 4px;
            color: #0f172a;
            font-family: monospace;
        }
    </style>
</head>
<body>

    <!-- COVER PAGE -->
    <div class="cover-page">
        <div style="margin-top: 100px;">
            <div class="cover-title">คู่มือการตั้งค่าและการย้ายฐานข้อมูลเป็น PostgreSQL</div>
            <div style="font-size: 18px; font-weight: bold; color: #64748b; margin-bottom: 10px;">การเปลี่ยนผ่านฐานข้อมูลจาก JSON เป็น Relational Database (PostgreSQL)</div>
            <div class="cover-subtitle">ระบบบริการข้อมูลสวัสดิการพนักงานโรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ (TUH Chatbot AI)</div>
        </div>
        <div class="cover-meta">
            <p><strong>จัดทำโดย:</strong> แผนกพัฒนาระบบ AI แชทบอท โรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ</p>
            <p><strong>วันที่เผยแพร่:</strong> 20 กรกฎาคม 2569</p>
            <p><strong>เวอร์ชัน:</strong> 1.0.0 (PostgreSQL Edition)</p>
        </div>
    </div>

    <!-- SECTION 1 -->
    <div>
        <h1>1. บทนำและการใช้งาน PostgreSQL ร่วมกับ TUH Chatbot AI</h1>
        <p>เพื่อยกระดับความน่าเชื่อถือและความเสถียรของระบบ <strong>TUH Chatbot AI</strong> ในการใช้งานจริง (Production) การเปลี่ยนระบบจัดเก็บข้อมูลจากโครงสร้างเดิมที่เป็นไฟล์ JSON แฟลตไฟล์ (Flat Files) มาเป็นระบบฐานข้อมูลเชิงสัมพันธ์ที่มีประสิทธิภาพสูงอย่าง <strong>PostgreSQL</strong> ถือเป็นโซลูชันที่เหมาะสมที่สุดสำหรับสภาพแวดล้อมระบบเครือข่ายของโรงพยาบาล เนื่องจาก:</p>
        
        <ul>
            <li><strong>รองรับธุรกรรมพร้อมกันสูง (Concurrency):</strong> ป้องกันปัญหาฐานข้อมูลล็อก (Database Lock) เมื่อมีพนักงานเข้ามาพิมพ์แชทสอบถามพร้อมกันจำนวนมาก</li>
            <li><strong>ความถูกต้องของข้อมูล (Data Integrity):</strong> ใช้โครงสร้าง ForeignKey เพื่อรักษาความสัมพันธ์ระหว่างตาราง เช่น ประวัติแชทกับเซสชันการคุย</li>
            <li><strong>การสืบค้นย้อนหลังที่มีประสิทธิภาพ:</strong> การใช้ SQL Index บนตารางเก็บประวัติความพึงพอใจและประวัติการถามตอบ ช่วยให้หน้าแดชบอร์ดฝั่งแอดมินดึงข้อมูลได้อย่างรวดเร็วแม้ข้อมูลจะมีมากกว่า 50,000 แถว</li>
            <li><strong>ความปลอดภัยระดับองค์กร:</strong> ข้อมูลไม่ได้ถูกวางอยู่ในรูปแบบไฟล์ที่เข้าถึงได้โดยตรง แต่จะถูกเข้ารหัสและปกป้องภายใต้สิทธิ์ผู้ใช้งานและไฟร์วอลล์ของฐานข้อมูล</li>
        </ul>
        
        <div class="info-box">
            <strong>💡 ความเข้ากันได้ของระบบ:</strong><br>
            Python สามารถเชื่อมต่อกับ PostgreSQL ได้อย่างไร้รอยต่อผ่านทางโมดูลไลบรารี <code>psycopg2</code> ซึ่งเป็น PostgreSQL Database Adapter มาตรฐานที่มีความปลอดภัยและเสถียรภาพสูง
        </div>
    </div>

    <!-- SECTION 2 -->
    <div class="page-break">
        <h1>2. ขั้นตอนการตั้งค่าใน pgAdmin 4</h1>
        <p><strong>pgAdmin 4</strong> เป็นโปรแกรมบริหารจัดการฐานข้อมูล PostgreSQL ผ่านหน้าจอผู้ใช้ (GUI) ที่ใช้งานง่ายและเป็นที่นิยมที่สุด โดยมีขั้นตอนการสร้าง Server Connection และฐานข้อมูลดังนี้:</p>

        <ul class="step-list">
            <li class="step-item">
                <div class="step-number">1</div>
                <div class="step-title">สร้างการเชื่อมต่อฐานข้อมูลใหม่ (Register Server)</div>
                <p>เปิดโปรแกรม pgAdmin 4 จากนั้นคลิกขวาที่โฟลเดอร์ <strong>Servers</strong> ที่แถบด้านซ้าย เลือก <strong>Register &gt; Server...</strong></p>
            </li>
            
            <li class="step-item">
                <div class="step-number">2</div>
                <div class="step-title">ตั้งค่าแท็บ General และ Connection</div>
                <p>หน้าต่างตั้งค่าจะแสดงขึ้นมา ให้กำหนดรายละเอียดดังนี้:</p>
                <div class="dialog-mockup">
                    <div style="font-weight: bold; border-bottom: 1px solid #e2e8f0; padding-bottom: 5px; margin-bottom: 10px; color: #0d9488;">[แท็บ General]</div>
                    <div class="dialog-row">
                        <div class="dialog-label">Name:</div>
                        <div class="dialog-input">TUH_Chatbot_Production</div>
                    </div>
                    <div style="font-weight: bold; border-bottom: 1px solid #e2e8f0; padding-bottom: 5px; margin-top: 15px; margin-bottom: 10px; color: #0d9488;">[แท็บ Connection]</div>
                    <div class="dialog-row">
                        <div class="dialog-label">Host name/address:</div>
                        <div class="dialog-input">localhost (หรือใส่ IP Address ของ Database Server)</div>
                    </div>
                    <div class="dialog-row">
                        <div class="dialog-label">Port:</div>
                        <div class="dialog-input">5432</div>
                    </div>
                    <div class="dialog-row">
                        <div class="dialog-label">Maintenance database:</div>
                        <div class="dialog-input">postgres</div>
                    </div>
                    <div class="dialog-row">
                        <div class="dialog-label">Username:</div>
                        <div class="dialog-input">postgres (หรือชื่อบัญชีที่สร้างไว้ใน PostgreSQL)</div>
                    </div>
                    <div class="dialog-row">
                        <div class="dialog-label">Password:</div>
                        <div class="dialog-input">******** (กรอกรหัสผ่านที่ตั้งตอนติดตั้ง PostgreSQL)</div>
                    </div>
                </div>
                <p>เสร็จแล้วกดปุ่ม <strong>Save</strong> เพื่อบันทึกการเชื่อมต่อ</p>
            </li>

            <li class="step-item">
                <div class="step-number">3</div>
                <div class="step-title">สร้างฐานข้อมูลสำหรับแชทบอท (Create Database)</div>
                <p>ขยายรายการของ Server ที่เราเพิ่งสร้างขึ้นมา คลิกขวาที่หัวข้อ <strong>Databases</strong> เลือก <strong>Create &gt; Database...</strong> จากนั้นในช่อง <strong>Database</strong> ให้กรอกชื่อ <code>tuh_chatbot</code> แล้วกดปุ่ม <strong>Save</strong></p>
            </li>
        </ul>
    </div>

    <!-- SECTION 3 -->
    <div class="page-break">
        <h1>3. โครงสร้างตาราง PostgreSQL SQL Schemas</h1>
        <p>ให้เปิดเครื่องมือ Query Tool ใน pgAdmin 4 (โดยการคลิกขวาที่ฐานข้อมูล <code>tuh_chatbot</code> แล้วเลือก <strong>Query Tool</strong>) จากนั้นคัดลอกคำสั่งสร้างตาราง (DDL) เหล่านี้ไปรันเพื่อเตรียมโครงสร้างตารางข้อมูล:</p>

        <pre><code>-- 1. ตารางตั้งค่าพารามิเตอร์ระบบ
CREATE TABLE settings (
    key_name VARCHAR(100) PRIMARY KEY,
    value_text TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. ตารางผู้ดูแลระบบ
CREATE TABLE admins (
    username VARCHAR(100) PRIMARY KEY,
    password_salt VARCHAR(64) NOT NULL,
    password_hash VARCHAR(128) NOT NULL,
    role VARCHAR(100) NOT NULL,
    name VARCHAR(200) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. ตารางปุ่มด่วนหน้าแรก FAQs
CREATE TABLE predefined_faqs (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    icon VARCHAR(50) DEFAULT 'fa-circle-question'
);

-- 4. ตารางทะเบียนคู่มือตอบคำถามคู่มือ FAQs
CREATE TABLE custom_faqs (
    id VARCHAR(100) PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    timestamp_str VARCHAR(50)
);

-- 5. ตารางเก็บเอกสาร PDF สำหรับค้นหา RAG
CREATE TABLE documents (
    filename VARCHAR(255) PRIMARY KEY,
    size INTEGER NOT NULL,
    pages INTEGER NOT NULL,
    upload_date VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'Active'
);

-- 6. ตารางเก็บทะเบียนแบบฟอร์มสวัสดิการ
CREATE TABLE welfare_forms (
    id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    filename VARCHAR(255),
    page VARCHAR(50),
    download_link VARCHAR(500)
);

-- 7. ตารางเก็บคำถามที่บอทตอบไม่ได้
CREATE TABLE unanswered_queries (
    id VARCHAR(100) PRIMARY KEY,
    query TEXT NOT NULL,
    count INTEGER DEFAULT 1,
    timestamp VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'Pending'
);

-- 8. ตารางเก็บประวัติคำถามคำตอบแชทและการประเมินความพึงพอใจ
CREATE TABLE chat_messages (
    id SERIAL PRIMARY KEY,
    session_key VARCHAR(100) NOT NULL,
    query TEXT NOT NULL,
    answer TEXT NOT NULL,
    rating VARCHAR(50) DEFAULT NULL, -- 'like' / 'dislike' / NULL
    comment TEXT DEFAULT NULL,
    timestamp VARCHAR(50) NOT NULL,
    model VARCHAR(100) NOT NULL,
    chunk_ids VARCHAR(255) DEFAULT NULL,
    response_time DOUBLE PRECISION DEFAULT 0.0
);
CREATE INDEX idx_chat_messages_timestamp ON chat_messages(timestamp);
CREATE INDEX idx_chat_messages_session ON chat_messages(session_key);
</code></pre>
    </div>

    <!-- SECTION 4 -->
    <div class="page-break">
        <h1>4. สคริปต์สลับย้ายข้อมูลอัตโนมัติ (Migration Script)</h1>
        <p>สคริปต์ Python ด้านล่างนี้จะช่วยดึงข้อมูลเดิมจากไฟล์ JSON ทั้งหมดในเครื่อง และย้ายเข้าไปที่ฐานข้อมูล PostgreSQL อัตโนมัติ โดยคัดลอกไปสร้างไฟล์ชื่อ <code>postgresql_migrate.py</code>:</p>

        <pre><code>import os
import json
import psycopg2

# การตั้งค่าการเชื่อมต่อ PostgreSQL
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "tuh_chatbot",
    "user": "postgres",
    "password": "YOUR_PASSWORD" # กรอกรหัสผ่านจริงที่นี่
}

def migrate_to_postgresql():
    json_dir = os.path.join("user", "backend", "db")
    
    # เชื่อมต่อ PostgreSQL
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    print("📡 เชื่อมต่อฐานข้อมูล PostgreSQL สำเร็จ")

    def load_json_file(filename):
        path = os.path.join(json_dir, filename)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    # 1. ย้ายข้อมูล Settings
    settings_data = load_json_file("db_settings.json")
    if settings_data:
        # แยกค่า Config ทั่วไปลงตาราง settings
        config_keys = ["temperature", "max_tokens", "top_k", "model_name", "welcome_message", "chat_greeting", "system_prompt"]
        for key in config_keys:
            if key in settings_data:
                cursor.execute(
                    "INSERT INTO settings (key_name, value_text) VALUES (%s, %s) ON CONFLICT (key_name) DO UPDATE SET value_text = EXCLUDED.value_text",
                    (key, str(settings_data[key]))
                )
        # แยก Predefined FAQs ลงตาราง predefined_faqs
        p_faqs = settings_data.get("predefined_faqs", [])
        cursor.execute("TRUNCATE TABLE predefined_faqs RESTART IDENTITY")
        for faq in p_faqs:
            cursor.execute(
                "INSERT INTO predefined_faqs (question, answer, icon) VALUES (%s, %s, %s)",
                (faq.get("question", ""), faq.get("answer", ""), faq.get("icon", "fa-circle-question"))
            )
        # แยก Custom FAQs ลงตาราง custom_faqs
        c_faqs = settings_data.get("custom_faqs", [])
        for faq in c_faqs:
            cursor.execute(
                "INSERT INTO custom_faqs (id, question, answer, timestamp_str) VALUES (%s, %s, %s, %s) ON CONFLICT (id) DO UPDATE SET question=EXCLUDED.question, answer=EXCLUDED.answer",
                (faq.get("id"), faq.get("question"), faq.get("answer"), faq.get("timestamp"))
            )
        print("✅ ย้ายข้อมูลตั้งค่าและ FAQs สำเร็จ")

    # 2. ย้ายข้อมูล Admin
    admin_data = load_json_file("db_admin.json")
    if admin_data:
        cursor.execute(
            "INSERT INTO admins (username, password_salt, password_hash, role, name) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (username) DO NOTHING",
            (admin_data.get("username"), admin_data.get("password_salt"), admin_data.get("password_hash"), admin_data.get("role"), admin_data.get("name"))
        )
        print("✅ ย้ายข้อมูลบัญชีแอดมินสำเร็จ")

    # 3. ย้ายข้อมูล Documents
    docs = load_json_file("db_documents.json")
    if docs:
        for doc in docs:
            cursor.execute(
                "INSERT INTO documents (filename, size, pages, upload_date, status) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (filename) DO UPDATE SET status=EXCLUDED.status",
                (doc.get("filename"), doc.get("size", 0), doc.get("pages", 0), doc.get("upload_date", ""), doc.get("status", "Active"))
            )
        print("✅ ย้ายข้อมูลเอกสาร PDF สำเร็จ")

    # 4. ย้ายข้อมูล Forms
    forms = load_json_file("db_forms.json")
    if forms:
        for f in forms:
            cursor.execute(
                "INSERT INTO welfare_forms (id, name, filename, page, download_link) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
                (f.get("id"), f.get("name"), f.get("filename"), f.get("page"), f.get("link"))
            )
        print("✅ ย้ายข้อมูลแบบฟอร์มสวัสดิการสำเร็จ")

    # 5. ย้ายข้อมูล Unanswered Logs
    unans = load_json_file("db_unanswered.json")
    if unans:
        for u in unans:
            cursor.execute(
                "INSERT INTO unanswered_queries (id, query, count, timestamp, status) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (id) DO UPDATE SET count=EXCLUDED.count, status=EXCLUDED.status",
                (u.get("id"), u.get("query"), u.get("count", 1), u.get("timestamp", ""), u.get("status", "Pending"))
            )
        print("✅ ย้ายข้อมูลคำถามค้างตอบสำเร็จ")

    # 6. ย้ายข้อมูลประวัติแชทและประเมินผลความพึงพอใจ
    history = load_json_file("db_history.json") or []
    feedback = load_json_file("db_feedback.json") or []
    
    # รวมข้อมูล Feedback (คอมเมนต์/เรตติ้ง) เข้ากับประวัติประโยค
    fb_dict = {fb.get("history_id"): fb for fb in feedback if fb.get("history_id")}
    
    cursor.execute("TRUNCATE TABLE chat_messages RESTART IDENTITY")
    for msg in history:
        hid = msg.get("id")
        fb_item = fb_dict.get(hid, {})
        
        rating = fb_item.get("rating") or None
        comment = fb_item.get("comment") or None
        
        cids = ", ".join(map(str, msg.get("chunk_ids", []))) if isinstance(msg.get("chunk_ids"), list) else str(msg.get("chunk_ids", ""))
        
        cursor.execute(
            "INSERT INTO chat_messages (session_key, query, answer, rating, comment, timestamp, model, chunk_ids, response_time) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                msg.get("session_key", "default_session"),
                msg.get("query", ""),
                msg.get("answer", ""),
                rating,
                comment,
                msg.get("timestamp", ""),
                msg.get("model", "N/A"),
                cids,
                float(msg.get("response_time", 0.0))
            )
        )
    print("✅ ย้ายและรวมประวัติแชทพร้อมผลการโหวตคะแนนสำเร็จ")

    conn.commit()
    cursor.close()
    conn.close()
    print("🎉 สลับย้ายข้อมูล JSON สู่ PostgreSQL ทั้งหมดเรียบร้อยแล้ว!")

if __name__ == "__main__":
    migrate_to_postgresql()</code></pre>
    </div>

    <!-- SECTION 5 -->
    <div class="page-break">
        <h1>5. การปรับปรุงโค้ดในไฟล์ server.py</h1>
        <p>เมื่อเปลี่ยนมาใช้ PostgreSQL แล้ว ให้เข้าไปแทนที่การอ่านเขียนไฟล์ JSON ในไฟล์ <code>user/backend/server.py</code> โดยยกเลิกการเขียนระบบโหลดแบบไฟล์ตรง ๆ และแทนที่ด้วยคำสั่งเชื่อมโยง SQL Query ดังตัวอย่างแนวทางด้านล่างนี้:</p>

        <pre><code>import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "tuh_chatbot",
    "user": "postgres",
    "password": "YOUR_PASSWORD"
}

def get_db_connection():
    # ฟังก์ชันช่วยเปิดการเชื่อมต่อ และรับผลลัพธ์เป็น Dict แบบคีย์เวิร์ด
    return psycopg2.connect(**DB_CONFIG)

# ตัวอย่างการเขียนฟังก์ชันเพื่อโหลด Settings แทนที่โครงสร้าง JSON เดิม
def load_db_settings():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # 1. โหลดข้อมูลสเกลาร์
    cursor.execute("SELECT key_name, value_text FROM settings")
    settings = {row['key_name']: row['value_text'] for row in cursor.fetchall()}
    
    # แปลงไทป์ข้อมูลกลับสู่ปกติ
    if "temperature" in settings: settings["temperature"] = float(settings["temperature"])
    if "max_tokens" in settings: settings["max_tokens"] = int(settings["max_tokens"])
    if "top_k" in settings: settings["top_k"] = int(settings["top_k"])
    
    # 2. โหลดรายการ Predefined FAQs
    cursor.execute("SELECT question, answer, icon FROM predefined_faqs ORDER BY id ASC")
    settings["predefined_faqs"] = [dict(row) for row in cursor.fetchall()]
    
    # 3. โหลดรายการ Custom FAQs
    cursor.execute("SELECT id, question, answer, timestamp_str as timestamp FROM custom_faqs")
    settings["custom_faqs"] = [dict(row) for row in cursor.fetchall()]
    
    cursor.close()
    conn.close()
    return settings

# ตัวอย่างการแก้ไขฟังก์ชันบันทึกประวัติการแชท (log_bot_response) เพื่อบันทึกลง PostgreSQL ตรงๆ
def log_bot_response(query_str, answer_str, chunk_ids, response_time, model_name, session_key="default_session"):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cids_str = ", ".join(map(str, chunk_ids)) if isinstance(chunk_ids, list) else str(chunk_ids)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute(
        "INSERT INTO chat_messages (session_key, query, answer, timestamp, model, chunk_ids, response_time) VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (session_key, query_str, answer_str, timestamp, model_name, cids_str, float(response_time))
    )
    
    # ควบคุมจำกัดขนาดไม่ให้ฐานข้อมูลโตอย่างไร้ขอบเขตในตารางใช้งานจริง (เช่น 50,000 แถว)
    cursor.execute("SELECT count(*) FROM chat_messages")
    count = cursor.fetchone()[0]
    if count > 50000:
        # ลบข้อมูลที่เก่าที่สุดทิ้งไป
        cursor.execute("DELETE FROM chat_messages WHERE id IN (SELECT id FROM chat_messages ORDER BY id ASC LIMIT %s)", (count - 50000,))
        
    conn.commit()
    cursor.close()
    conn.close()
</code></pre>

        <div class="warning-box">
            <strong>⚠️ คำแนะนำในการปรับปรุง (Migration Strategy):</strong><br>
            ก่อนทำการรันแก้ไขไฟล์ <code>server.py</code> แนะนำให้ทำการคัดลอกโฟลเดอร์สำรองตัวเก่า (Backup) หรือทำ Git Commit แยก Branch ใหม่ไว้เสมอ เพื่อป้องกันข้อผิดพลาดในการปรับแก้ตัวดึงข้อมูล SQL ในแต่ละฟังก์ชันย่อย
        </div>
    </div>

</body>
</html>
"""
    
    # Temporary paths
    temp_dir = tempfile.gettempdir()
    temp_html_path = os.path.join(temp_dir, "temp_guide.html")
    temp_pdf_path = os.path.join(temp_dir, "temp_guide.pdf")

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
            final_pdf_path = os.path.join(workspace_dir, "postgresql_migration_guide.pdf")
            
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
