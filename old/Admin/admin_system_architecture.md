# เอกสารสถาปัตยกรรมระบบสำหรับผู้ดูแลระบบ (Admin System Architecture - Diagram 1)

เอกสารฉบับนี้อธิบายรายละเอียดโครงสร้างสถาปัตยกรรมและการไหลของข้อมูล (Data & Execution Flow) ในส่วนของระบบผู้ดูแลระบบ (Admin System) ของ **TUH Chatbot AI** โรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ ซึ่งประกอบด้วยโมดูลส่วนติดต่อผู้ใช้ (Frontend), ส่วนเซิร์ฟเวอร์ประมวลผล (Backend Server API), ระบบจัดเก็บข้อมูลฐานข้อมูลดัชนี (Vector & Sparse Indices) และระบบกระบวนการทำงานเบื้องหลัง (Background Worker Rebuild Pipeline)

---

## 1. แผนผังความเชื่อมโยงระบบ (System Architecture Diagram)

```mermaid
graph LR
    %% Subgraph 1: Client Side
    subgraph Client_Side["ส่วนของผู้ใช้งาน (Client Side)"]
        User_General["👤 ผู้ใช้งานทั่วไป<br>(บุคลากร / ผู้รับบริการ)"]
        User_Admin["🔑 ผู้ดูแลระบบ / เจ้าหน้าที่<br>(Admin / IT Staff)"]
        
        Browser_Chat["💬 Web Browser (Chatbot UI)<br>- คุยกับบอทสอบถามข้อมูล (Port 5173)"]
        Browser_Admin["⚙️ Web Browser (Admin Dashboard)<br>- จัดการระบบ / บันทึกข้อมูล (Port 5173 / Test Console)"]
        
        User_General -->|เข้าใช้งานบอท| Browser_Chat
        User_Admin -->|เข้าจัดการระบบ| Browser_Admin
    end

    %% Network connection in the middle
    Network(("🌐 Internet / Localhost <br> Network"))

    %% Connect Client Side to Network
    Browser_Chat -->|HTTP Request| Network
    Browser_Admin -->|HTTP Request| Network

    %% Subgraph 2: Server Side
    subgraph Server_Side["ส่วนของเซิร์ฟเวอร์ (Server Side)"]
        WebServer["💻 Web Server (Python Backend API)<br>(Application Logic & RAG Controller)<br>Port: 8000"]
        
        Database["💾 Database & Storage<br>- db_*.json (Settings, Feedback, Unanswered)<br>- uploads/ (PDF Filesต้นฉบับ)<br>- index_db/ (ดัชนี FAISS & BM25)"]
        
        AI_Inference["🧠 AI Inference Service<br>- Google Gemini API (Cloud)<br>- Local Ollama (qwen2.5:3b)"]
        
        WebServer <-->|Read / Write / Rebuild| Database
        WebServer <-->|Query Context & Generate| AI_Inference
    end

    %% Connect Network to Server Side
    Network -->|ส่งคำขอ (API Request)| WebServer
```

---

## 2. รายละเอียดของส่วนประกอบหลักในระบบ (Component Description)

### 2.1 Client Layer (ส่วนติดต่อผู้ใช้)
*   **💬 Chat Client:** หน้าจอแชทสำหรับผู้ใช้งานทั่วไป พัฒนาด้วย React และ Tailwind CSS ช่วยให้ผู้ใช้ทั่วไปสามารถสอบถามข้อมูลระเบียบและสวัสดิการของโรงพยาบาลได้
*   **⚙️ Admin Dashboard:** หน้าจอสำหรับผู้ดูแลระบบและเจ้าหน้าที่สารสนเทศ ใช้สำหรับการตรวจสอบสถิติการใช้งาน, จัดการไฟล์เอกสาร PDF (อัปโหลด ลบ เปิด/ปิดการใช้งาน ยกเว้นบางหน้า), แก้ไขระบบตอบกลับล่วงหน้า (Custom FAQs), ดูบันทึกการส่งฟีดแบ็ก (Feedback logs) และจัดการรายการคำถามที่ระบบไม่สามารถหาคำตอบได้ (Unanswered queries)
*   **🛠️ Developer Test Console:** หน้าเว็บทดสอบแบบง่าย (`Admin/testChat/index.html`) สำหรับนักพัฒนาในการยิงคำถามและวิเคราะห์ข้อมูลเวกเตอร์แบบดิบ (ดูคะแนนความคล้ายคลึง Rank และรายละเอียดของ Chunk)

### 2.2 Backend API Server (`server.py`)
ทำหน้าที่เป็นศูนย์กลางของระบบโดยใช้ไลบรารีพื้นฐาน `http.server.HTTPServer` ของ Python ทำงานที่พอร์ต `8000` โดยมีโมดูลย่อยภายในดังนี้:
*   **API Router & Request Handler:** ตรวจสอบสิทธิ์การเข้าถึง API และส่งคำขอไปยังปลายทางที่ถูกต้อง
*   **Authentication (Login):** ตรวจสอบชื่อผู้ใช้และรหัสผ่านของผู้ดูแลระบบ (สิทธิ์เริ่มต้น: `admin` / `admin1234`) เพื่อคืนโทเค็นเซสชันจำลอง
*   **Stats & Logs Engine:** อ่านและเขียนข้อมูลสถิติของแชทบอท เช่น จำนวนครั้งการกดถูกใจ (Likes), ไม่ถูกใจ (Dislikes), และบันทึกคำถามที่ LLM ตอบไม่ได้
*   **Retriever Service:** ประมวลผลดัชนีในหน่วยความจำผ่านคลาส `HybridRetriever`
*   **AI Orchestrator (Ollama & Gemini Manager):** รับผิดชอบในการวิเคราะห์ว่ามีคีย์ `GEMINI_API_KEY` หรือมีไม่ หากมีจะส่งคำถามและบริบทไปประมวลผลบนคลาวด์ของ Google Gemini (โมเดล `gemini-2.5-flash`) หากไม่มี จะทำการสื่อสารแบบออฟไลน์ไปยัง API ของ Ollama ที่รันอยู่ในเครื่องคอมพิวเตอร์แทน (โมเดล `qwen2.5:3b`)

### 2.3 Data Storage (ระบบบันทึกและจัดการข้อมูล)
*   **Local JSON Databases:** จัดเก็บโครงสร้างแอปพลิเคชันอย่างง่ายโดยไม่จำเป็นต้องใช้ Database Server ขนาดใหญ่ ประกอบด้วยไฟล์ 4 ไฟล์ในโฟลเดอร์ `user/backend/db/`:
    *   `db_settings.json`: เก็บการตั้งค่าเซิร์ฟเวอร์ AI เช่น ค่าระดับความคิดสร้างสรรค์ (Temperature), ความยาวคำตอบสูงสุด (Max tokens), จำนวน Chunk ที่ใช้ดึงข้อมูล (Top-K), ข้อความต้อนรับตอนเริ่มแชท, และระบบคำถามยอดนิยม (Custom FAQs) ที่ผู้ดูแลระบบตั้งค่าไว้
    *   `db_documents.json`: เก็บข้อมูลเมตาดาตาของเอกสาร PDF เช่น ชื่อไฟล์, ขนาดไฟล์, สถานะ (Active / Inactive / Processing / Error), วันเวลาที่อัปโหลด, และอาร์เรย์รายการเลขหน้าที่ต้องเว้นจากการนำเข้าดัชนี (Exclude pages)
    *   `db_feedback.json`: เก็บคะแนนความพึงพอใจประเมินคำตอบของแชทบอท พร้อมข้อเสนอแนะเพิ่มเติมจากผู้ใช้งาน
    *   `db_unanswered.json`: เก็บประวัติคำถามที่ระบบตอบไม่ได้ หรือไม่มีข้อมูลในไฟล์อ้างอิง เพื่อให้เจ้าหน้าที่นำมาตอบหรืออัปโหลดเอกสารเพิ่มในภายหลัง
*   **PDF Storage (`uploads/`):** โฟลเดอร์เก็บบันทึกไฟล์ PDF ต้นฉบับที่พร้อมนำมาทำดัชนี
*   **Vector & Lexical Database (`index_db/`):** โฟลเดอร์เก็บฐานข้อมูลดัชนีสำหรับใช้ในการทำ RAG ค้นหาบริบท:
    *   `faiss.index`: ดัชนีเวกเตอร์หนาแน่น (Dense Vectors) ประมวลผลจากโมเดล `BAAI/bge-m3` และจัดเก็บด้วยโครงสร้างดัชนี FAISS Flat Inner Product
    *   `faiss_metadata.json`: แฟ้มจัดเก็บเนื้อหาข้อความจริงของ Chunk แต่ละตัวเพื่อให้ดึงข้อความขึ้นมาหลังค้นพบเวกเตอร์
    *   `bm25.pkl`: ดัชนีคำค้นหาความถี่ต่ำแบบเบาตัว (Sparse BM25 Index) ที่ผ่านการตัดคำภาษาไทยด้วย PyThaiNLP เซฟด้วยการแปลงออบเจกต์ผ่าน Serialization (Pickle)

### 2.4 Background Rebuild Process (ทาสก์ประมวลผลสร้างดัชนี)
เมื่อมีการเปลี่ยนแปลงเกี่ยวกับเอกสาร เช่น อัปโหลดไฟล์ PDF ใหม่ ลบไฟล์เก่า สลับการเปิดใช้งาน หรือเปลี่ยนชุดเลขหน้ายกเว้น ระบบจะไม่บล็อกขั้นตอนการทำงานของแอดมินบนหน้าเว็บ แต่จะสร้าง **Thread เบื้องหลัง (Background Thread)** ขึ้นมาทำงานตามลำดับดังนี้:
1.  **เรียกทำงานสคริปต์ `Admin/rebuild_db.py`**:
    *   ดึงไฟล์ PDF ที่มีสถานะ "Active" ทั้งหมดในโฟลเดอร์ `uploads/`
    *   ใช้ `fitz` (PyMuPDF) แกะตัวหนังสือออกมาทีละหน้า โดยข้ามเลขหน้าที่อยู่ในอาร์เรย์ยกเว้น (Excluded Pages) ของไฟล์นั้นๆ
    *   *กรณีพิเศษ*: หากประมวลผลไฟล์เริ่มต้นสวัสดิการสุขภาพ มธ. พ.ศ. 2566 และเลขหน้ายกเว้นเป็นค่าเริ่มต้น ระบบจะเปลี่ยนไปอ่านข้อความตารางความละเอียดสูงดั้งเดิมจาก `sample_cleaned.md` เพื่อคงความแม่นยำของตารางที่แกะด้วยเครื่องมือพิเศษ (Camelot)
2.  **ประมวลผลหั่นย่อยข้อความ (Chunking)**:
    *   แยกประเภทข้อความเป็นเนื้อหาทั่วไป (Text) และตาราง (Table)
    *   ใช้เทคนิค Parent-Child ในตาราง โดยนำเฉพาะสรุปตาราง (Child - `generate_table_description`) ไปเก็บใน `content` สำหรับทำดัชนีเวกเตอร์ และเก็บตาราง Markdown ตัวเต็ม (Parent - `raw_table`) ใน metadata เพื่อส่งเข้า LLM
    *   ป้องกันการหั่นครึ่งประโยคและทำลายคำภาษาไทยด้วยตัวตัดข้อความ `RecursiveCharacterTextSplitter` ร่วมกับ `sent_tokenize` (PyThaiNLP)
    *   บันทึกไฟล์ชิ้นส่วนรวมทั้งหมดลงใน `sample_chunks.json`
3.  **เรียกทำงานฟังก์ชันสร้างดัชนีใน `Admin/emb.py`**:
    *   ดึงเนื้อหาจาก `sample_chunks.json`
    *   ป้อนข้อความทั่วไปและข้อความ Child ของตารางเข้า SentenceTransformer เพื่อแปลงเป็นเวกเตอร์ 1024 มิติด้วย `bge-m3` และบันทึกลงไฟล์ `faiss.index`
    *   นำข้อความมาตัดคำภาษาไทยสร้างดัชนีคำค้นหา (Lexical BM25 index) และบันทึกลงไฟล์ `bm25.pkl`
4.  **สั่งโหลดดัชนีในหน่วยความจำใหม่ (Memory Reload)**:
    *   เมื่อสร้างดัชนีลงไฟล์สำเร็จ ตัวประมวลผลเบื้องหลังจะเรียกฟังก์ชัน `.load()` ของ `HybridRetriever` บนหน่วยความจำของเซิร์ฟเวอร์เพื่อให้ผลการดึงดัชนีตัวใหม่พร้อมตอบคำถามทันทีโดยไม่ต้องรีสตาร์ตระบบ

---

## 3. ลำดับและขั้นตอนการไหลของข้อมูล (Execution & Data Flow)

### 3.1 ขั้นตอนการถามคำถามของผู้ใช้งาน (RAG Query Flow)

```
[ผู้ใช้ส่งคำถาม] -> [ตรวจสอบความตรงกันล่วงหน้า (Custom FAQs)] 
                    ├──> (ตรง)  --> ดึงคำตอบจาก Custom FAQs ทันที -> [ส่งคำตอบกลับผู้ใช้]
                    └──> (ไม่ตรง) --> เข้าสู่กระบวนการ RAG
                                     │
    ┌────────────────────────────────┘
    ▼
[ประมวลผลการค้นหาด้วย HybridRetriever]
    ├──> ส่งคำถามหาเวกเตอร์ที่ใกล้เคียงจาก Dense FAISS Index (Weight = 0.4)
    └──> ส่งคำถามหาข้อความอ้างอิงที่ใกล้เคียงจาก Sparse BM25 Index (Weight = 0.6)
    ▼
[รวมและจัดอันดับผลลัพธ์ด้วย Weighted Reciprocal Rank Fusion (Weighted RRF)]
    ▼
[ดึงเนื้อหาบริบท (Context) 3 อันดับแรกมาเตรียมไว้]
    ├──> หากมีข้อมูลตาราง (Table) สลับไปหยิบตารางตัวเต็ม (Parent raw_table) ป้อนแทนข้อความสรุป
    └──> กรองเอกสารอ้างอิงเฉพาะชิ้นที่เป็น "Active" ในระบบจัดการเอกสารเท่านั้น
    ▼
[ส่งคำถาม + บริบท + System Prompt ไปยังโมเดลประมวลผลคำตอบ (AI Generation)]
    ├──> มี GEMINI_API_KEY   --> ส่งยิงขึ้น Cloud API (gemini-2.5-flash)
    └──> ไม่มี GEMINI_API_KEY --> ส่งวิเคราะห์ภายในเครื่องผ่าน Local Ollama (qwen2.5:3b)
                                   └─> หากเกิดข้อผิดพลาด/Ollama ออฟไลน์ --> ส่งข้อความอ้างอิงที่ใกล้เคียงที่สุดจากเวกเตอร์กลับไปแทน (Offline Fallback Answer)
    ▼
[ส่งคำตอบ + เอกสารระเบียบอ้างอิง (Citations) กลับไปยังผู้ใช้]
```

### 3.2 ขั้นตอนการประมวลผลเบื้องหลังของแอดมิน (Admin Document Rebuild Flow)

```
[แอดมินเปลี่ยนการจัดการเอกสาร/อัปโหลดไฟล์ PDF ใหม่] 
    │
    ▼ 
[บันทึกไฟล์ลง uploads/ และเขียนข้อมูลเมทาดาตาลง db_documents.json]
    │
    ▼
[เซิร์ฟเวอร์เรียกเริ่มทำงานทาสก์เบื้องหลัง (Background Thread)] ────> [คืนสถานะ "Processing" และตอบกลับหน้าเว็บแอดมินทันที]
    │
    ▼ (ประมวลผลต่อเบื้องหลัง)
[รีบิวด์ฐานข้อมูลผ่าน Admin/rebuild_db.py]
    ├──> สแกนหา PDF ทั้งหมดที่เป็นสถานะ Active
    ├──> ข้ามหน้าเอกสารที่ต้องการยกเว้นตาม Exclude Pages
    ├──> คัดแยกข้อความเนื้อหาทั่วไปและข้อความตาราง Markdown
    └──> หั่นย่อยข้อความด้วย pythainlp.tokenize.sent_tokenize และ LangChain Splitter
    │
    ▼
[สร้างดัชนีผ่าน Admin/emb.py]
    ├──> โหลดไฟล์ chunks และแปลงเป็นเวกเตอร์ด้วยโมเดล BAAI/bge-m3 บันทึกลง faiss.index
    └──> ตัดคำและสร้างโมเดลความถี่คำหลักด้วย BM25 Okapi บันทึกลง bm25.pkl
    │
    ▼
[ส่งคำสั่งอัปเดต HybridRetriever ในหน่วยความจำ]
    │
    ▼
[ปรับปรุงสถานะของไฟล์ใน db_documents.json เป็น "Active" หรือ "Error" หากพบปัญหา]
```

---

## 4. รายละเอียดโครงสร้างแฟ้มข้อมูลฐานข้อมูล (JSON DB Schemas)

สถาปัตยกรรมข้อมูลหลักเก็บในรูปแฟ้ม JSON มีคีย์ที่สำคัญดังนี้:

### 4.1 แฟ้มการตั้งค่าระบบ (`db_settings.json`)
```json
{
  "gemini_api_key": "string หรือเว้นว่าง",
  "model_name": "string เช่น gemini-2.5-flash หรือ qwen2.5:3b",
  "temperature": 0.2,
  "max_tokens": 400,
  "top_k": 3,
  "system_prompt": "ข้อความระบบกำกับการทำงานของบอท...",
  "welcome_message": "ข้อความต้อนรับของแชทบอท...",
  "custom_faqs": [
    {
      "question": "คำถามยอดนิยมที่แอดมินตั้ง",
      "answer": "คำตอบโดยตรงที่ไม่ผ่าน AI"
    }
  ]
}
```

### 4.2 แฟ้มจัดการไฟล์เอกสาร (`db_documents.json`)
```json
[
  {
    "filename": "ชื่อไฟล์เอกสารสวัสดิการ.pdf",
    "status": "Active | Inactive | Processing | Error",
    "pages": 19,
    "upload_date": "YYYY-MM-DD HH:MM:SS",
    "size": 606752,
    "exclude_pages": [12, 13, 14, 18]
  }
]
```

### 4.3 แฟ้มบันทึกความคิดเห็นฟีดแบ็ก (`db_feedback.json`)
```json
[
  {
    "id": "fb-1782265154207",
    "msgId": "uuid-string-of-message",
    "rating": "like | dislike",
    "comment": "ข้อเสนอแนะเพิ่มเติมจากผู้ใช้งาน",
    "query": "คำถามต้นฉบับของผู้ใช้",
    "timestamp": "YYYY-MM-DD HH:MM:SS"
  }
]
```

### 4.4 แฟ้มบันทึกคำถามที่ระบบตอบไม่ได้ (`db_unanswered.json`)
```json
[
  {
    "id": "unans-1782265154207",
    "query": "คำถามที่พิมพ์หาไม่เจอหรือไม่พบบริบทอ้างอิง",
    "count": 2,
    "timestamp": "YYYY-MM-DD HH:MM:SS",
    "status": "Pending | Resolved"
  }
]
```
