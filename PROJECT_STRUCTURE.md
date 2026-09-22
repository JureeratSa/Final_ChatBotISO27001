# TUH Chatbot AI — โครงสร้างไฟล์และโฟลเดอร์ (สำหรับส่งมอบ)

เอกสารนี้สรุปโครงสร้างไฟล์/โฟลเดอร์ของโปรเจกต์หลังการจัดระเบียบโค้ด (refactor) เสร็จสมบูรณ์
ระบุว่าแต่ละไฟล์ทำหน้าที่อะไร เขียนด้วยภาษา/เฟรมเวิร์กอะไร และใช้ library อะไรบ้าง
**ไม่รวมไฟล์เทส** (`Backend/tests/`, `web_testing/`, `*.test.js`, `testchatbotSPO/`, `TestPFM/`)
เพราะเป็นเครื่องมือตรวจสอบคุณภาพระหว่างพัฒนา ไม่ใช่ส่วนของแอปพลิเคชันที่รันจริง

ดู [README.md](README.md) สำหรับวิธีติดตั้ง/รันระบบแบบละเอียด และ [CLAUDE.md](CLAUDE.md)
สำหรับกฎการพัฒนาต่อ

---

## ภาพรวมสถาปัตยกรรม

ระบบแบ่งเป็น 3 ส่วนแยกอิสระกัน (3-tier):

```
Backend/    → FastAPI (Python) — REST API + RAG pipeline + Auth        พอร์ต 8000
AdminWeb/   → React + Vite — หน้าหลังบ้านสำหรับแอดมิน                    พอร์ต 5174
UserWeb/    → React + Vite — แชทบอทที่ผู้ใช้ทั่วไปเห็น                    พอร์ต 5173
Admin/      → Python scripts — เครื่องมือ RAG ระดับล่าง (ไม่ใช่ FastAPI app)
```

Backend คุยกับ AdminWeb/UserWeb ผ่าน HTTP/JSON เท่านั้น (CORS เปิดเฉพาะ origin ที่กำหนดใน
`Backend/app/main.py`) ไม่มีการ import ข้ามภาษากันโดยตรง

---

## 1. `Backend/` — FastAPI REST API

**ภาษา/เฟรมเวิร์กหลัก:** Python 3 + FastAPI + SQLAlchemy (async) + Pydantic
**Database:** TiDB Cloud (MySQL-compatible) ผ่าน `aiomysql`/`pymysql` — ห้ามใช้ SQLite/Postgres นอก unit test
**Library หลักทั้งโปรเจกต์** (จาก `Backend/requirements.txt`):

| Library | ใช้ทำอะไร |
|---|---|
| `fastapi`, `uvicorn` | เว็บเฟรมเวิร์ก + ASGI server |
| `pydantic`, `pydantic-settings` | validate request/response + อ่านค่า config จาก `.env` |
| `sqlalchemy` (async), `aiomysql`, `pymysql`, `cryptography` | ORM + driver เชื่อม TiDB (async ใช้จริง, sync ใช้เฉพาะจุดที่รันใน background thread) |
| `alembic` | จัดการ database migration |
| `python-jose[cryptography]` | สร้าง/ตรวจสอบ JWT token |
| `passlib[bcrypt]` | hash รหัสผ่าน |
| `python-multipart` | รับไฟล์อัปโหลดแบบ multipart/form-data |
| `nh3` | sanitize HTML กัน Stored XSS (เนื้อหาจาก CKEditor) |
| `httpx` | เรียก LLM API (OpenRouter) แบบ async |
| `chromadb` | Vector database เก็บ dense embedding สำหรับ RAG |
| `sentence-transformers` | โมเดล embedding `BAAI/bge-m3` |
| `rank-bm25` | lexical search (BM25) |
| `pythainlp` | ตัดคำภาษาไทยสำหรับ BM25 |
| `langchain-text-splitters` | แบ่งเอกสารเป็น chunk |
| `PyMuPDF` (`fitz`) | อ่าน/ตัดหน้า PDF |
| `python-dotenv` | โหลดค่าจาก `.env` |

### โครงสร้างไฟล์

```
Backend/
├── requirements.txt, requirements-dev.txt   # รายการ library (prod / dev เช่น pytest)
├── alembic.ini, alembic/                    # ตั้งค่า + ไฟล์ migration ของ DB schema
├── scripts/
│   └── migrate_from_json.py                 # สคริปต์ one-shot ย้ายข้อมูลจากระบบ v1 (JSON) เข้า DB — รันด้วยมือครั้งเดียว ไม่รันตอน startup
└── app/
    ├── main.py                              # entry point จริง — สร้าง FastAPI app, CORS, mount router ทั้งหมด, serve static /uploads
    ├── core/
    │   ├── config.py                        # อ่าน environment variables (.env) ด้วย pydantic-settings — DB URL, JWT secret, LLM key ฯลฯ
    │   ├── database.py                      # สร้าง async SQLAlchemy engine/session, dependency get_db()
    │   ├── security.py                      # hash/verify password, สร้าง/ตรวจ JWT, safe_path()/safe_filename() กัน Path Traversal
    │   ├── rate_limit.py                    # จำกัด request ต่อ IP (in-memory) สำหรับ endpoint แพง เช่น /api/chat
    │   └── logging_config.py                # ตั้งค่า logging กลาง (แทน print() เดิม)
    ├── models/
    │   └── models.py                        # SQLAlchemy ORM models ทุกตาราง (User, Document, ChatHistory, Feedback, UnansweredQuery, Form, Announcement, SystemSettings)
    ├── schemas/
    │   └── schemas.py                       # Pydantic request/response schema ทุกตัว (validation layer)
    ├── utils/
    │   └── sanitize.py                      # sanitize_html() ด้วย nh3 — whitelist tag ที่ CKEditor อนุญาต
    ├── services/                            # business logic ที่ดึงออกจาก router (service layer)
    │   ├── rag_service.py                   # เชื่อมกับ Admin/emb.py — โหลด/reload retriever, เรียก LLM (OpenRouter), ตรวจคำหยาบ/ทักทาย
    │   ├── document_service.py              # ownership check, mapping Document→response, pipeline อนุมัติเอกสาร (raw→clean→chunk→active)
    │   ├── rebuild_service.py               # trigger rebuild vector index แบบ background, เขียนสถานะ rebuild ลง DB, ลบเอกสารออกจากดัชนีทันที
    │   ├── form_service.py                  # แปลงสตริงระบุหน้า PDF (เช่น "1,3,5-7") เป็น list เลขหน้า
    │   ├── feedback_service.py              # upsert feedback (อัปเดตแถวเดิมถ้า query+answer ตรงกัน ไม่งั้นสร้างใหม่)
    │   ├── unanswered_service.py            # บันทึกคำถามที่ตอบไม่ได้ (นับซ้ำแบบ case-insensitive) + วิเคราะห์คำถามด้วย LLM
    │   └── history_service.py               # แปลง ChatHistory row → response schema
    └── routers/                             # HTTP endpoint แต่ละ domain (ทุกไฟล์ = FastAPI APIRouter)
        ├── auth.py                          # /api/auth/* — login/refresh/logout ของผู้ใช้ทั่วไประบบ auth หลัก + CRUD บัญชีแอดมิน
        ├── chat.py                          # /api/chat — หัวใจ RAG: ค้นหา (ChromaDB+BM25+RRF) แล้วส่งให้ LLM ตอบ
        ├── public.py                        # /api/search, /api/ip, /api/announcements/active, health check, ดาวน์โหลดไฟล์ — endpoint สาธารณะ/compatibility
        ├── admin_auth.py                    # /api/admin/login, /api/admin/password/update — login จริงของ AdminWeb (ไม่ใช่ legacy ที่เลิกใช้)
        ├── admin_documents.py               # /api/admin/documents/* — CRUD เอกสาร + pipeline อนุมัติ + preview raw/cleaned/chunks
        ├── admin_settings.py                # /api/admin/settings — ตั้งค่า AI (temperature, prompt, FAQ ฯลฯ)
        ├── admin_rebuild.py                 # /api/admin/rebuild, /rebuild/status — สั่ง rebuild vector index
        ├── admin_feedback.py                # /api/admin/feedback* — ดู/บันทึก/ลบ feedback ผู้ใช้
        ├── admin_unanswered.py              # /api/admin/unanswered* — จัดการคำถามที่บอทตอบไม่ได้
        ├── admin_stats.py                   # /api/admin/stats — สรุปตัวเลขภาพรวม (dashboard)
        ├── admin_forms.py                   # /api/admin/forms* — CRUD แบบฟอร์มสวัสดิการ (อัปโหลด/ตัดหน้า PDF)
        ├── admin_announcements.py           # /api/admin/announcements* — CRUD ประกาศ
        └── admin_history.py                 # /api/admin/history* — ประวัติแชท + chunk map สำหรับลิงก์ไปหน้า PDF
```

---

## 2. `Admin/` — RAG Pipeline (เครื่องมือระดับล่าง ไม่ใช่ FastAPI app)

**ภาษา:** Python — **ห้ามแก้ไขโดยไม่จำเป็น** (กฎโปรเจกต์ข้อ 2 ใน CLAUDE.md) เพราะเป็นหัวใจของ
ระบบค้นหา ที่ `Backend/app/services/rag_service.py` เรียกใช้จริง

```
Admin/
├── emb.py         # HybridRetriever: ผสม ChromaDB (dense, BAAI/bge-m3) + BM25 (lexical, pythainlp)
│                    ด้วย Weighted RRF (dense 0.4 / lexical 0.6, rrf_k=60), delete_document_from_index()
├── cleanData.py   # ฟังก์ชันคลีนข้อความไทยจาก PDF (replace_thai_numbers ฯลฯ) ก่อนแบ่ง chunk
└── rebuild_db.py  # rebuild() — สร้าง ChromaDB + BM25 index ใหม่ทั้งหมดจากเอกสารที่ status=Active
```
Library หลัก: `chromadb`, `sentence-transformers`, `rank-bm25`, `pythainlp` (เหมือนที่ประกาศใน
`Backend/requirements.txt` เพราะ Backend import ไฟล์กลุ่มนี้ตรงๆ)

---

## 3. `AdminWeb/` — หน้าหลังบ้านแอดมิน (React)

**ภาษา/เฟรมเวิร์ก:** JavaScript (JSX) + React 18 + Vite (build tool) + Tailwind CSS
**Library หลัก** (จาก `AdminWeb/package.json`):

| Library | ใช้ทำอะไร |
|---|---|
| `react`, `react-dom` | UI framework |
| `vite`, `@vitejs/plugin-react` | dev server + build (ไม่ใช้ Create React App) |
| `tailwindcss`, `postcss`, `autoprefixer` | CSS utility framework |
| `@fortawesome/fontawesome-free` | ไอคอน |
| CKEditor 4 (โหลดผ่าน `<script>` CDN ใน `index.html` ไม่ใช่ npm package) | rich text editor สำหรับเขียนเนื้อหาประกาศ |

ไม่มี state management library (Redux ฯลฯ) — ใช้ React Context (`AdminContext`) + custom hooks ล้วน
ไม่มี chart library ภายนอก — กราฟทั้งหมด (เส้นแนวโน้ม/โดนัท CSAT) วาดด้วย SVG มือเอง

### โครงสร้างไฟล์

```
AdminWeb/
├── index.html                  # HTML shell — โหลด CKEditor CDN + main.jsx
└── src/
    ├── main.jsx                 # entry point — mount <App /> เข้า DOM
    ├── App.jsx                  # ประกอบ hook ทั้งหมดเข้าด้วยกัน, ตั้งค่า contextValue, routing แบบ activeTab-string (ไม่ใช้ React Router)
    ├── context/
    │   └── AdminContext.jsx     # React Context กลาง — ทุกหน้า (page) อ่านข้อมูล/handler ผ่านนี้ที่เดียว
    ├── layouts/
    │   └── AdminShell.jsx       # โครง layout รวม (sidebar เมนู + topbar) ที่ทุกหน้าใช้ร่วมกัน
    ├── hooks/                   # ที่เก็บ state + business logic แยกตาม domain (ดึงออกจาก App.jsx เดิม)
    │   ├── useAuth.js               # login/logout, เก็บ token
    │   ├── useProfile.js            # เปลี่ยนรหัสผ่านตัวเอง
    │   ├── useTheme.js               # dark mode
    │   ├── useDashboardData.js       # ดึงข้อมูลสถิติ/แนวโน้มสำหรับหน้า Dashboard
    │   ├── useDocumentsState.js      # CRUD เอกสาร + pipeline อนุมัติ + preview/แก้ chunk (hook ใหญ่สุด)
    │   ├── useFormsState.js          # CRUD แบบฟอร์มสวัสดิการ
    │   ├── useAnnouncementsState.js  # CRUD ประกาศ
    │   ├── useUsersState.js          # จัดการบัญชีแอดมิน (เฉพาะ System Administrator)
    │   ├── useHistoryState.js        # ประวัติแชท + กรองวันที่ + export CSV
    │   ├── useFeedbackAndUnansweredState.js  # ตอบ FAQ จากคำถามที่ตอบไม่ได้, แก้ FAQ ปุ่มหน้าแรก
    │   ├── useSettingsState.js       # บันทึกการตั้งค่า AI
    │   └── useDeleteConfirmation.js  # popup ยืนยันลบ ใช้ร่วมกันทุก domain
    ├── pages/                   # แต่ละหน้า = component ที่ "ไม่มี hook ของตัวเอง" อ่านทุกอย่างจาก AdminContext
    │   ├── LoginPage.jsx             # หน้า login (render ก่อน login สำเร็จ รับ props ตรงจาก App.jsx ไม่ผ่าน Context)
    │   ├── DashboardPage.jsx         # หน้าภาพรวม — ประกอบ component ย่อยใน components/dashboard/
    │   ├── DocumentsPage.jsx         # จัดการเอกสาร RAG — ประกอบ component ย่อยใน components/documents/
    │   ├── SatisfactionPage.jsx      # กราฟความพึงพอใจแยกช่วงเวลา
    │   ├── AnnouncementsPage.jsx     # จัดการประกาศ (ใช้ CKEditorWrapper)
    │   ├── LogsPage.jsx              # ล็อกคำถามที่ตอบไม่ได้
    │   ├── HistoryPage.jsx           # ประวัติแชททั้งหมด + export CSV
    │   ├── FaqsPage.jsx              # แก้ไข FAQ ปุ่มหน้าแรก
    │   ├── SettingsPage.jsx          # ตั้งค่าโมเดล AI/prompt
    │   ├── ProfilePage.jsx           # เปลี่ยนรหัสผ่านตัวเอง
    │   └── UsersPage.jsx             # จัดการบัญชีแอดมิน
    └── components/
        ├── CKEditorWrapper.jsx           # ห่อ CKEditor 4 (CDN) ให้ใช้แบบ controlled component
        ├── documents/
        │   ├── ChunkEditorGrid.jsx       # ตาราง/กริดแก้ไข chunk เอกสาร (ใช้ร่วมกัน 2 จุด: preview pipeline + edit-details modal)
        │   └── ChunkCard.jsx             # การ์ดแสดง/แก้ chunk เดี่ยว
        └── dashboard/
            ├── StatCard.jsx              # การ์ดตัวเลขสรุป (เอกสาร/คำถาม/like-dislike ฯลฯ)
            ├── TrendLineChart.jsx        # กราฟเส้นแนวโน้ม (SVG มือเขียน + อัลกอริทึมกันจุดทับกัน)
            ├── CsatDoughnutChart.jsx     # กราฟโดนัทคะแนนความพึงพอใจ (SVG)
            ├── PendingQuestionsTable.jsx # ตารางคำถามค้างตอบ
            ├── ActiveAnnouncementsPanel.jsx # แผงประกาศที่กำลังใช้งาน
            ├── TrendDrawer.jsx           # แผงเลื่อนออกด้านข้าง แสดง Q&A ของจุดที่คลิกบนกราฟ
            └── AnswerFaqModal.jsx        # popup ตอบคำถามที่ตอบไม่ได้ให้กลายเป็น FAQ
```

---

## 4. `UserWeb/` — แชทบอทฝั่งผู้ใช้ (React)

**ภาษา/เฟรมเวิร์ก:** JavaScript (JSX) + React 18 + Vite + Tailwind CSS
**⚠️ UI/พฤติกรรมของส่วนนี้ถูกล็อกตามกฎโปรเจกต์ — ห้ามเปลี่ยนโดยไม่ได้รับอนุญาต**

**Library หลัก** (จาก `UserWeb/package.json`):

| Library | ใช้ทำอะไร |
|---|---|
| `react`, `react-dom` | UI framework |
| `vite`, `@vitejs/plugin-react` | dev server + build |
| `tailwindcss`, `postcss`, `autoprefixer` | CSS utility framework |
| `@fortawesome/fontawesome-free` | ไอคอน |
| `axios` | มีติดตั้งไว้ในโปรเจกต์ (การเรียก API จริงในโค้ดปัจจุบันใช้ `fetch()` builtin ของเบราว์เซอร์เป็นหลัก) |

### โครงสร้างไฟล์

```
UserWeb/
├── index.html                  # HTML shell
└── src/
    ├── main.jsx                 # entry point — mount <App />
    ├── App.jsx                  # ประกอบ hook ทั้งหมด + render UI แชท (state/logic ทั้งหมดอยู่ใน hooks/)
    ├── logo.png, dog.png, dog_light.png, bot_avatar.jpg   # รูปภาพมาสคอต/โลโก้ที่ใช้ตรงใน component
    ├── utils/
    │   ├── chatUtils.js          # API_URL, ข้อความต้อนรับ default, escapeHtml(), parseMarkdown() (กัน XSS+จำกัด URL scheme), getBotResponse() (fallback ตอบตามคำสำคัญ/FAQ)
    │   └── formatters.js         # stripHtml(), formatAnnDate() — ฟังก์ชันช่วยจัดรูปแบบข้อความ/วันที่ประกาศ
    ├── hooks/                   # แยก state + effect ตามความรับผิดชอบ (ดึงออกจาก App.jsx เดิม)
    │   ├── useClock.js               # นาฬิกาเรียลไทม์ (อัปเดตทุก 1 วิ) สำหรับนับเวลา session หมดอายุ
    │   ├── useTheme.js               # dark mode + มาสคอต/อวาตาร์ที่เปลี่ยนตามธีม
    │   ├── useSidebarResize.js       # ลาก-ปรับความกว้าง sidebar (mouse+touch)
    │   ├── useFontSize.js            # ปรับขนาดตัวอักษร
    │   ├── useSidebarToggle.js       # เปิด/ปิด sidebar, คัดลอกข้อความ (copiedId)
    │   ├── useChatSessions.js        # sessions ทั้งหมด, session หมดอายุอัตโนมัติ (1 ชม.), สร้าง/ลบบทสนทนา — จุดที่ซับซ้อนที่สุด
    │   ├── useWelcomeSettings.js     # โหลดข้อความต้อนรับ/คำทักทาย/FAQ จาก Backend ตอนเปิดแอป
    │   ├── useFaqVisibility.js       # โชว์/ซ่อนปุ่ม FAQ ตามการสลับบทสนทนา
    │   ├── useChatInput.js           # ช่องพิมพ์, การพิมพ์ของบอท, ส่งข้อความไปยัง /api/search, forced-feedback trigger
    │   ├── useFeedbackModal.js       # ฟอร์มให้คะแนนความพึงพอใจทั่วไป
    │   ├── useDislikeModal.js        # ฟอร์มระบุเหตุผลไม่พอใจ (กดปุ่ม dislike ข้อความ)
    │   ├── useAnnouncements.js       # โหลด/แสดง popup ประกาศที่กำลังใช้งาน
    │   └── useUserIp.js              # ดึง IP ผู้ใช้มาแสดง
    └── components/
        ├── Sidebar.jsx           # แถบเมนูซ้าย — รายการบทสนทนา, ธีม, ขนาดฟอนต์, ปุ่มเริ่มแชทใหม่
        ├── InputBar.jsx          # แถบพิมพ์ข้อความด้านล่างหน้าจอแชท
        ├── MessageBubble.jsx     # ฟองข้อความ (ผู้ใช้/บอท) + ปุ่ม like/dislike/copy
        ├── GuideModal.jsx        # popup คู่มือการใช้งาน
        ├── FeedbackModal.jsx     # popup ให้คะแนน (ทั่วไป/บังคับหลัง 3 คำถาม)
        ├── DislikeModal.jsx      # popup ระบุเหตุผลไม่พอใจ
        └── AnnouncementModal.jsx # popup ประกาศ
```

---

## 5. ไฟล์ระดับ root

```
run_backend.py     # สคริปต์รัน Backend (uvicorn) แบบสั้น — python + uvicorn
run_user_web.py    # สคริปต์รัน UserWeb dev server (เรียก npm ภายใน) — python (wrapper เรียก Node/npm)
run_admin_web.py   # สคริปต์รัน AdminWeb dev server (เรียก npm ภายใน) — python (wrapper เรียก Node/npm)
README.md          # คู่มือติดตั้ง/รันระบบแบบละเอียด
CLAUDE.md          # กฎการพัฒนาที่ต้องยึดถือ (DB, RAG, UI, security, branch, commit)
```

---

## สรุปจำนวนไฟล์หลังจัดระเบียบ (ไม่รวมเทส)

| ส่วน | ไฟล์หลักก่อน refactor | หลัง refactor |
|---|---|---|
| `Backend/app/routers/admin.py` | ไฟล์เดียว 1,549 บรรทัด | แยกเป็น 10 router ไฟล์ + 6 service ไฟล์ |
| `AdminWeb/src/App.jsx` | 1,786 บรรทัด | 591 บรรทัด + 12 hook + 9 component |
| `AdminWeb/src/pages/DashboardPage.jsx` | 778 บรรทัด | 209 บรรทัด + 7 component |
| `AdminWeb/src/pages/DocumentsPage.jsx` | 1,146 บรรทัด | 936 บรรทัด + 2 component |
| `UserWeb/src/App.jsx` | 1,244 บรรทัด | 439 บรรทัด + 13 hook + 1 util ไฟล์ |

ทุกไฟล์แยกตาม **domain เดียว รับผิดชอบเดียว** (single responsibility) — ไม่มีไฟล์ไหนที่ผสม
route handler + business logic + database query ปนกันเหมือนโครงสร้างเดิมอีกต่อไป
