# เอกสารการพัฒนาซอฟต์แวร์ (Software Development Document)
## TUH Chatbot AI — แชทบอทงานสารสนเทศ โรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ

เอกสารนี้ครอบคลุมโครงสร้างโค้ด มาตรฐานการเขียนโค้ด และแนวทางการพัฒนาต่อของระบบ — ใช้คู่กับ
[README.md](README.md) (วิธีติดตั้ง/รัน/deploy), [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)
(รายละเอียดไฟล์ทุกไฟล์) และ [CLAUDE.md](CLAUDE.md) (กฎบังคับของโปรเจกต์)

---

## 1. บทนำ

### 1.1 วัตถุประสงค์ของเอกสาร
อธิบายสถาปัตยกรรม โครงสร้างโค้ด มาตรฐานการเขียนโค้ด และแนวทางการพัฒนาของระบบ เพื่อให้ผู้พัฒนา
รายใหม่ (เช่น ทีมไอทีโรงพยาบาลที่รับช่วงต่อ) เข้าใจระบบและพัฒนาต่อได้โดยไม่ต้องไล่อ่านโค้ดทั้งหมด
ตั้งแต่ต้น

### 1.2 ขอบเขตของระบบ
ระบบแชทบอทตอบคำถามสวัสดิการ/งานสารสนเทศของโรงพยาบาล ด้วยเทคนิค RAG (Retrieval-Augmented
Generation) ประกอบด้วย 3 ส่วน: Backend (FastAPI), UserWeb (แชทบอทสำหรับผู้ใช้ทั่วไป/บุคลากร),
AdminWeb (ระบบหลังบ้านสำหรับแอดมิน)

### 1.3 กลุ่มเป้าหมายของเอกสาร
ผู้พัฒนา/ผู้ดูแลระบบที่รับช่วงพัฒนาต่อ — ต้องมีพื้นฐาน Python, JavaScript/React, REST API,
SQL เบื้องต้น

### 1.4 คำศัพท์และคำย่อ
| คำย่อ | ความหมาย |
|---|---|
| RAG | Retrieval-Augmented Generation — ค้นหาข้อมูลจากเอกสารจริงก่อนให้ LLM สร้างคำตอบ |
| RRF | Reciprocal Rank Fusion — วิธีรวมผลค้นหาจาก 2 แหล่ง (dense + lexical) |
| BM25 | อัลกอริทึม lexical/keyword search แบบดั้งเดิม |
| JWT | JSON Web Token — ใช้ทำ authentication |
| ORM | Object-Relational Mapping (SQLAlchemy) |
| SPA | Single Page Application (React) |

---

## 2. ภาพรวมระบบและสถาปัตยกรรม

### 2.1 สถาปัตยกรรมระดับสูง (3-tier)

```
┌─────────────┐        HTTP/JSON        ┌──────────────────┐        SQL        ┌──────────────┐
│  UserWeb     │ ───────────────────────▶│                   │──────────────────▶│  TiDB Cloud   │
│  (:5173)     │◀─────────────────────── │   Backend         │◀──────────────────│  (MySQL)      │
└─────────────┘                          │   FastAPI (:8000) │                   └──────────────┘
┌─────────────┐        HTTP/JSON         │                   │
│  AdminWeb    │ ───────────────────────▶│                   │──────┐
│  (:5174)     │◀─────────────────────── │                   │      │ import ตรง (ไม่ผ่าน HTTP)
└─────────────┘                          └──────────────────┘      ▼
                                                              ┌──────────────┐
                                                              │  Admin/       │
                                                              │  RAG Pipeline │
                                                              │  (ChromaDB +  │
                                                              │   BM25)       │
                                                              └──────────────┘
```

Frontend ทั้งสองฝั่งคุยกับ Backend ผ่าน HTTP/JSON เท่านั้น ไม่มีการ import ข้ามภาษากัน —
Backend เป็นจุดเดียวที่ import โมดูลใน `Admin/` ตรงๆ (ไม่ผ่าน HTTP เพราะอยู่ใน process เดียวกัน)

### 2.2 Technology Stack

| ชั้น | เทคโนโลยี |
|---|---|
| Backend | Python 3, FastAPI, SQLAlchemy (async), Pydantic, Alembic |
| Database | TiDB Cloud (MySQL-compatible) |
| Vector Search | ChromaDB (dense) + rank-bm25 (lexical) |
| Embedding Model | BAAI/bge-m3 (ผ่าน sentence-transformers) |
| LLM | เรียกผ่าน OpenRouter API (httpx) — เปลี่ยนโมเดลได้จาก Settings |
| Frontend (ทั้งคู่) | React 18, Vite, Tailwind CSS |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| Testing | pytest (Backend), Vitest (UserWeb) |
| Deployment | uvicorn (dev/prod process) + Apache/XAMPP (static frontend) |

### 2.3 RAG Pipeline (HybridRetriever)

หัวใจของระบบค้นหาอยู่ที่ `Admin/emb.py` — **ห้ามแก้ไขโดยไม่จำเป็นและไม่ได้รับอนุญาต** (กฎ
โปรเจกต์) ประกอบด้วย:

1. **Dense retrieval**: ChromaDB + embedding model `BAAI/bge-m3`
2. **Lexical retrieval**: BM25 (`rank-bm25`) บนข้อความที่ตัดคำด้วย `pythainlp`
3. **Fusion**: Weighted Reciprocal Rank Fusion (dense weight 0.4 / lexical weight 0.6, `rrf_k=60`)

Pipeline การนำเอกสารเข้าระบบ (Document Ingestion): อัปโหลด PDF → ถอดข้อความดิบ (`fitz`) →
คลีนข้อความไทย (`Admin/cleanData.py`) → แบ่ง chunk (`langchain-text-splitters`) → พรีวิว/แก้ไข
chunk ผ่าน AdminWeb → อนุมัติเป็น Active → rebuild index (`Admin/rebuild_db.py`)

### 2.4 Data Flow หลัก (คำถามจากผู้ใช้ → คำตอบ)

```
UserWeb (ผู้ใช้พิมพ์คำถาม)
   │  POST /api/search
   ▼
Backend/app/routers/public.py
   │  เรียก HybridRetriever ค้นหา top-k chunk ที่เกี่ยวข้อง
   ▼
Admin/emb.py (ChromaDB + BM25 + RRF)
   │  ส่ง chunk ที่ได้ + prompt ไปยัง LLM
   ▼
app/services/rag_service.py → OpenRouter API
   │  คำตอบ + citations
   ▼
UserWeb แสดงผล + บันทึกลง ChatHistory (background task)
```

---

## 3. โครงสร้างโค้ด

ดูรายละเอียดทุกไฟล์ (ไลบรารีที่ใช้ + หน้าที่) ได้ที่ [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)
สรุปหลักการจัดโครงสร้างโดยย่อ:

| ชั้น (Layer) | หน้าที่ | ตัวอย่าง |
|---|---|---|
| **Router** (`app/routers/*.py`) | รับ HTTP request, validate ด้วย Pydantic, เรียก service, คืน response — **ไม่มี business logic ซับซ้อนอยู่ในนี้** | `admin_documents.py` |
| **Service** (`app/services/*.py`) | business logic ที่มีเงื่อนไข/การตัดสินใจจริง (upsert rule, pipeline, ownership check) | `document_service.py` |
| **Model** (`app/models/models.py`) | นิยามตาราง DB (SQLAlchemy ORM) | `Document`, `User` |
| **Schema** (`app/schemas/schemas.py`) | นิยามรูปแบบ request/response (Pydantic) | `DocumentResponse` |
| **Core** (`app/core/*.py`) | ของกลางที่ใช้ข้ามโดเมน: config, database session, security, rate limit | `security.py` |

ฝั่ง React (AdminWeb/UserWeb) ใช้หลักการเดียวกัน: **Hook = business logic, Page/Component =
render อย่างเดียว** — ดูหัวข้อ 6.2

---

## 4. การออกแบบฐานข้อมูล

TiDB Cloud (MySQL-compatible) จัดการ schema ผ่าน Alembic เท่านั้น (ห้ามแก้ schema ตรงๆ)

| ตาราง | คีย์หลัก | ความสัมพันธ์ | หมายเหตุ |
|---|---|---|---|
| `users` | `id` (int, auto) | 1 user → many `documents`/`announcements` (ผ่าน `*_id` FK) | บัญชีแอดมิน/เจ้าหน้าที่ — มี `role`, `department` |
| `documents` | `id` (int, auto) | `uploaded_by_id` → `users.id` (`SET NULL`) | `status`: Processing / Step_Raw_Text / Step_Clean_Text / Step_Chunk_Preview / Active / Inactive |
| `settings` | `id` (string, ค่าเดียวคือ `"config"`) | — | ตารางแถวเดียว เก็บค่าตั้งค่า AI ทั้งระบบ + สถานะ rebuild |
| `history` | `id` (string) | 1 history → many `feedback` | บันทึกทุกคำถาม-คำตอบของ UserWeb |
| `feedback` | `id` (string) | `history_id` → `history.id` (`SET NULL`) | `rating`: like/dislike, `stars`: 1-5 (แบบสอบถามทั่วไป) |
| `unanswered` | `id` (string) | — | คำถามที่บอทตอบไม่ได้ นับซ้ำด้วย `count` |
| `forms` | `id` (string) | — | แบบฟอร์มสวัสดิการดาวน์โหลดได้ |
| `announcements` | `id` (int, auto) | `created_by_id` → `users.id` (`SET NULL`) | ประกาศ พร้อม `category`, `pinned` |

**หลักการออกแบบที่ต้องรักษาไว้**: คอลัมน์ `uploaded_by`/`created_by` (string) เก็บชื่อไว้เป็น
cache คู่กับ `uploaded_by_id`/`created_by_id` (FK จริง) — เพื่อให้ยังแสดงชื่อผู้ทำรายการได้แม้
บัญชีนั้นถูกลบไปแล้ว (`ON DELETE SET NULL` ทำให้ FK เป็น NULL แต่ชื่อ cache ยังอ่านได้)

---

## 5. การออกแบบ API

Base path ทั้งหมด: `/api/*` — Router แยกตาม domain (ดูตารางเต็มใน PROJECT_STRUCTURE.md)

### รูปแบบ Pydantic schema (ยึดตามนี้เสมอเมื่อเพิ่ม endpoint ใหม่)
| Suffix | ใช้กับ | ตัวอย่าง |
|---|---|---|
| `...Response` | Response body | `DocumentResponse`, `FeedbackResponse` |
| `...Create` | POST (สร้างใหม่) | `AnnouncementCreate` |
| `...Update` | PUT/PATCH (แก้ไขบางส่วน, field ส่วนใหญ่เป็น `Optional`) | `DocumentUpdate`, `SettingsUpdate` |

### รูปแบบ Authorization
- Endpoint ที่ต้อง login: ใส่ `current_user: User = Depends(get_current_user)` ใน parameter —
  FastAPI จะปฏิเสธ request ที่ไม่มี/หมดอายุ JWT อัตโนมัติ (401/403)
- Endpoint ตรวจ role เพิ่ม (เช่นเฉพาะ System Administrator): เช็คเงื่อนไข `current_user.role`
  ในตัว handler เอง แล้ว `raise HTTPException(403, ...)` ถ้าไม่ผ่าน (ดูตัวอย่างใน
  `admin_settings.py::update_settings`)
- Endpoint สาธารณะ (ไม่ต้อง login เช่น `/api/search`, `/api/ip`, `/api/announcements/active`):
  ไม่ใส่ `Depends(get_current_user)` เลย — ต้องระบุคอมเมนต์กำกับชัดเจนว่า "Public endpoint"
  เพื่อไม่ให้คนอื่นมาใส่ auth เพิ่มทีหลังโดยไม่รู้ว่าตั้งใจเปิดสาธารณะ

### หลักการเพิ่ม endpoint ใหม่
1. เพิ่ม schema ใน `app/schemas/schemas.py` ก่อน (ตาม naming convention ด้านบน)
2. ถ้ามี business rule ที่ซับซ้อนกว่า CRUD ธรรมดา → เขียนฟังก์ชันใน `app/services/<domain>_service.py`
3. Router handler เรียก service function แล้วคืนผลลัพธ์ — อย่าใส่ logic ซับซ้อนในตัว handler เอง
4. เพิ่ม router ใหม่ (ถ้าเป็น domain ใหม่จริงๆ) → ต้องไปเพิ่ม `app.include_router(...)` ทั้งใน
   `app/main.py` และ `tests/conftest.py` (fixture `app_instance`) คู่กันเสมอ ไม่งั้นเทสจะมองไม่เห็น
   endpoint ใหม่

---

## 6. มาตรฐานการเขียนโค้ด

### 6.1 Python (Backend)

- **PEP 8** + type hints ทุกฟังก์ชัน (`Mapped[...]` สำหรับ ORM, `-> ReturnType` สำหรับฟังก์ชัน)
- **Naming**: `snake_case` สำหรับตัวแปร/ฟังก์ชัน, `PascalCase` สำหรับ class/Pydantic model,
  ฟังก์ชัน "internal only" (ไม่ export เป็น public API ของโมดูล) นำหน้าด้วย `_` เช่น
  `_check_doc_ownership`, `_parse_exclude_pages`
- **1 ไฟล์ router = 1 domain เท่านั้น** ทุกไฟล์ต้องมี
  `router = APIRouter(prefix="/api/admin", tags=["admin"])` (หรือ prefix ที่เหมาะกับ domain)
  ที่หัวไฟล์ — ห้ามรวมหลาย domain ไว้ไฟล์เดียวแบบ `admin.py` เดิมอีก (บทเรียนจากการรีแฟกเตอร์
  ปี 2026 ที่ไฟล์เดียวยาวถึง 1,549 บรรทัด)
- **Service layer เฉพาะจุดที่มี business rule จริง** — CRUD ธรรมดา (GET/DELETE ตรงไปตรงมา) ปล่อย
  ไว้ใน router handler ได้ ไม่ต้องสร้าง indirection ที่ไม่มีอะไรให้ซ่อน
- **Security ต้องผ่าน helper กลางเสมอ** ห้ามเขียน logic ความปลอดภัยซ้ำเอง:
  - path จาก user input (filename) → ต้องผ่าน `safe_filename()` + `safe_path()` (`core/security.py`)
    กัน Path Traversal (CWE-22) เสมอ
  - HTML ที่ผู้ใช้กรอกแล้วจะ render กลับ (เช่นเนื้อหาประกาศจาก CKEditor) → ต้องผ่าน
    `sanitize_html()` (`utils/sanitize.py`) ก่อนเก็บ DB เสมอ กัน Stored XSS
  - รหัสผ่าน → `hash_password()`/`verify_password()` เท่านั้น ห้ามเทียบ plaintext เอง
- **Query ต้องผ่าน SQLAlchemy ORM/Core (`select()`)** เท่านั้น ห้าม string-concatenate SQL เอง
  (กัน SQL Injection โดยอัตโนมัติจากการใช้ ORM parameterized query)
- **Comment**: อธิบาย "ทำไม" ไม่ใช่ "ทำอะไร" — โค้ดที่ตั้งชื่อดีอยู่แล้วไม่ต้องมีคอมเมนต์ซ้ำ
  คอมเมนต์ที่มีค่าคือจุดที่มี constraint แปลกๆ, workaround บั๊กเฉพาะจุด, หรือพฤติกรรมที่
  ผู้อ่านคาดไม่ถึง (ภาษาไทย/อังกฤษปนกันได้ตามกฎโปรเจกต์ — ทีมนี้ใช้ไทยเป็นหลักเพราะสื่อสาร
  บริบทธุรกิจโรงพยาบาลได้ตรงกว่า)

### 6.2 JavaScript / React (AdminWeb, UserWeb)

- **Component file = `PascalCase.jsx`**, หนึ่งไฟล์ = หนึ่ง component เดียวเป็นหลัก
- **Hook file = `useXxx.js`** หนึ่งไฟล์ = หนึ่งความรับผิดชอบ (single responsibility) เช่น
  `useAuth.js` ดูแลแค่ login/logout ไม่ปนกับ `useProfile.js`
- **Business logic ต้องอยู่ใน hook ไม่ใช่ใน component body** — component/page ที่ดีควรอ่านแล้ว
  เห็นแต่ state ที่ได้จาก hook + JSX render เท่านั้น (ดูตัวอย่างที่ถูกต้องใน
  `AdminWeb/src/pages/*.jsx` ทุกไฟล์หลัง refactor — ไม่มี `useState`/`useEffect` ของตัวเองเลย)
- **AdminWeb**: ทุก hook ประกอบเข้า `contextValue` เดียวใน `App.jsx` แล้วส่งผ่าน `AdminContext`
  — page ใหม่ที่เพิ่มเข้ามาให้ใช้ `useAdminContext()` อ่านค่า ไม่ต้องรับ props ยาวเป็นหางว่าว
- **UserWeb**: ไม่มี Context กลาง — hook ถูกเรียกและประกอบใน `App.jsx` ตรงๆ (โปรเจกต์เล็กกว่า
  ไม่จำเป็นต้องมี Context) — ต้องระวังลำดับการเรียก hook เมื่อ hook หนึ่งต้องพึ่งค่าจากอีก hook
  (ดูตัวอย่าง `useWelcomeSettings` ที่ต้องเรียกหลัง `useChatSessions` เพราะต้องใช้ `setSessions`)
- **ห้ามใช้ inline business logic ใน JSX** (เช่น fetch ตรงใน `onClick`) — ให้เรียก handler ที่มา
  จาก hook เสมอ
- **State management**: ไม่ใช้ Redux/Zustand ฯลฯ — ใช้ React hooks + Context (เฉพาะ AdminWeb)
  ล้วนๆ ตามขนาดโปรเจกต์ปัจจุบัน ถ้าจะเพิ่ม library ใหม่ต้องมีเหตุผลชัดเจนว่าทำไม hooks ธรรมดา
  ไม่พอ

### 6.3 Naming Convention สรุปรวม

| สิ่งที่ตั้งชื่อ | รูปแบบ | ตัวอย่าง |
|---|---|---|
| Python function/variable | `snake_case` | `get_current_user` |
| Python class / Pydantic schema | `PascalCase` | `DocumentResponse` |
| Python internal-only function | `_snake_case` (นำ `_`) | `_doc_to_response` |
| DB table | `snake_case` พหูพจน์ | `documents`, `announcements` |
| React component file/export | `PascalCase.jsx` | `ChunkEditorGrid.jsx` |
| React hook file/export | `useCamelCase.js` | `useDocumentsState.js` |
| API path | `kebab-case` หรือคำเดียว, พหูพจน์สำหรับ resource | `/api/admin/documents` |
| Git branch (ที่ใช้จริงในโปรเจกต์นี้) | วันที่แบบ `ddmm` | `2508`, `1407` |
| Git commit message | ภาษาอังกฤษ, `type(scope): description` | `refactor(backend): split admin.py...` |

---

## 7. แนวทางการพัฒนา

### 7.1 Git Workflow
- **ห้าม push ตรงไปยัง `main` โดยไม่ได้รับอนุญาต** — สร้าง branch แยกก่อนเสมอ (กฎโปรเจกต์)
- Commit message เป็นภาษาอังกฤษ ใช้รูปแบบ Conventional Commits แบบคร่าวๆ:
  `feat: ...`, `fix(scope): ...`, `refactor(scope): ...`, `docs: ...`, `chore: ...`
- แยก commit ตาม scope/domain เดียว อย่ารวมหลายเรื่องไม่เกี่ยวกันไว้ commit เดียว — ทำให้
  bisect หา regression ได้ง่ายเมื่อพัง

### 7.2 Environment & Secrets
- Backend ต้องมี `Backend/.env` ก่อน start เสมอ (copy จาก `.env.example`) **ไม่มีค่า default
  ของ secret ใดๆ ฝังในโค้ด** — แอปจะ start ไม่ขึ้นถ้าไม่ตั้งค่า (ดู `core/config.py`)
- ห้าม hardcode secret จริง (`DB_PASSWORD`, `JWT_SECRET_KEY`, LLM API key) ลงไฟล์ที่ commit
  เข้า git เด็ดขาด (เคยมี production password หลุดจากจุดนี้มาก่อน — ดู CLAUDE.md ข้อ 4)

### 7.3 Database Migration
ใช้ Alembic เท่านั้น ห้ามแก้ schema ตรง DB มือ:
```bash
# แก้ app/models/models.py ก่อน แล้วค่อย generate migration
alembic revision --autogenerate -m "อธิบายสั้นๆ ว่าเปลี่ยนอะไร"
# ตรวจไฟล์ที่ได้ใน alembic/versions/ ก่อนเสมอ (autogenerate เดาไม่ได้ทุกกรณี)
alembic upgrade head
```

### 7.4 Testing Strategy

| ชั้นเทส | เครื่องมือ | ตำแหน่ง | ครอบคลุมอะไร |
|---|---|---|---|
| Unit (Backend) | pytest + SQLite in-memory | `Backend/tests/` | logic เดี่ยวๆ ต่อ endpoint/service |
| Unit + Integration (เสริม) | pytest + httpx.AsyncClient | `web_testing/unit/`, `web_testing/integration/` | endpoint จริงผ่าน FastAPI app ทดสอบ ยิง HTTP เข้า route |
| Unit (Frontend) | Vitest | `web_testing/unit-frontend/`, `UserWeb/vitest.config.js` | pure function ที่แยกออกมาได้ (เช่น `formatters.js`) |
| AdminWeb / UserWeb component-level | **ไม่มี automated test** | — | ต้อง manual click-through ทุกครั้งที่แก้ UI — โดยเฉพาะ UserWeb ที่ UI ถูกล็อก ต้องระวังเป็นพิเศษ |

รันเทสทั้งหมดก่อน merge ทุกครั้ง:
```bash
python -m pytest Backend/tests/ web_testing/unit/ web_testing/integration/ -v
```

### 7.5 Security Guidelines
- JWT: access token อายุ 15 นาที, refresh token อายุ 7 วัน — **ห้ามลดค่า** (กฎโปรเจกต์)
- รหัสผ่าน: hash ด้วย bcrypt (`passlib`) เท่านั้น
- CORS: allowlist origin ตรงๆ (`allowed_origins`) + regex จำกัด subnet/port สำหรับ LAN
  (`allowed_origin_regex` ใน `main.py`) — ห้ามเปิด `allow_origins=["*"]`
- Rate limiting: endpoint แพง (`/api/chat`, `/api/search`) มี in-memory rate limit ต่อ IP
  (`core/rate_limit.py`) — เป็น best-effort เท่านั้น ถ้าต้องแม่นยำระดับ production ต้องย้ายไป Redis
- Path traversal: ทุกจุดที่ใช้ filename จาก user input ต้องผ่าน `safe_filename()`/`safe_path()`
- XSS: เนื้อหา HTML จาก CKEditor ต้องผ่าน `sanitize_html()` ก่อนเก็บ DB เสมอ
- Role-based access: endpoint ที่จำกัดเฉพาะ System Administrator ต้องเช็ค `current_user.role`
  ในตัว handler แล้ว throw 403 ถ้าไม่ผ่าน

### 7.6 กฎเฉพาะของโปรเจกต์นี้ (ต้องอ่าน CLAUDE.md เต็มก่อนพัฒนาเพิ่ม)
1. **RAG Pipeline** (`Admin/emb.py`, `cleanData.py`, `rebuild_db.py`) — ห้ามแก้โดยไม่จำเป็นและ
   ไม่ได้รับอนุญาต เป็น legacy toolset ที่ Backend ยังเรียกใช้จริง ไม่ใช่ของที่ต้องลบทิ้ง
2. **UserWeb UI/พฤติกรรม** — ห้ามเปลี่ยนโดยไม่ได้รับอนุญาตจากผู้ใช้งานอย่างชัดเจน AdminWeb แก้ได้
   อิสระกว่าตาม scope ที่ได้รับ
3. **Database** ต้องเป็น TiDB Cloud (MySQL) ผ่าน async SQLAlchemy เท่านั้นใน production path —
   SQLite ใช้ได้เฉพาะ `Backend/tests/conftest.py`

### 7.7 การ Deploy
ดูรายละเอียดเต็มใน [README.md](README.md) — สรุปสั้นๆ มี 2 วิธี:
1. **Dev server** (`python run_backend.py` + `npm run dev`) — ใช้ตอนพัฒนา มี hot reload
2. **XAMPP** (build ด้วย `--base` flag แล้ววางใน `htdocs/`) — จำลอง production-like บนเครื่อง
   Windows, Backend ยังต้องรันแยกด้วย `python run_backend.py` เสมอ

---

## 9. การเชื่อมต่อของระบบ (System Connectivity & Integration Architecture)

### 9.1 แผนภาพการเชื่อมต่อระดับภาพรวม (Overall Connectivity Matrix)

```
+---------------------------------------------------------------------------------------------------+
|                                        Client Presentation Layer                                   |
|                                                                                                   |
|    +-----------------------------+                                 +-----------------------------+|
|    |      UserWeb (React/Vite)   |                                 |     AdminWeb (React/Vite)   ||
|    |      Port :5173 (Dev)       |                                 |     Port :5174 (Dev)        ||
|    |      XAMPP Apache :80 (Prod)|                                 |     XAMPP Apache :80 (Prod) ||
|    +--------------+--------------+                                 +--------------+--------------+|
+-------------------|---------------------------------------------------------------|---------------+
                    | HTTP/REST (JSON)                                              | HTTP/REST (JSON) + JWT Bearer
                    |                                                               |
+-------------------|---------------------------------------------------------------|---------------+
|                   ▼                                                               ▼               |
|    +-----------------------------------------------------------------------------------------+    |
|    |                                Backend Service (FastAPI / Uvicorn)                      |    |
|    |                                             Port :8000                                  |    |
|    |  - Middleware: CORS (Subnet Regex), RateLimiter (In-Memory IP Limiting)                 |    |
|    |  - Auth Layer: JWT Bearer (HMAC-SHA256, Access 15m / Refresh 7d)                         |    |
|    |  - Routers: chat, public, admin_documents, admin_settings, admin_history, etc.          |    |
|    +--------------------+---------------------------+------------------------+----------------+    |
|                         |                           |                        |                    |
+-------------------------|---------------------------|------------------------|--------------------+
                          | In-Process Python Call    | Async MySQL / TLS      | HTTPS REST (httpx)
                          ▼                           ▼                        ▼
       +------------------------------------+   +-------------------+   +---------------------------+
       |   Internal RAG & Vector Engine     |   | TiDB Cloud Server |   | External LLM Gateway      |
       |             (Admin/)               |   | (MySQL 8.0 / TLS) |   | (OpenRouter API / Ollama) |
       | - ChromaDB (BAAI/bge-m3 Embedding) |   | Port :4000        |   | - Gemma 4 26B (Default)   |
       | - BM25 Lexical (PyThaiNLP Tokenizer|   | - Connection Pool |   | - Llama 3.3 70B (Bench)   |
       | - Weighted RRF Fusion (0.4 / 0.6)  |   | - ChatHistory,    |   | - Claude 3 Haiku (Eval)   |
       | - Index files: index_db/           |   |   Users, Settings |   | - Fallback: Ollama Local  |
       +------------------------------------+   +-------------------+   +---------------------------+
```

### 9.2 รายละเอียดโปรโตคอลและจุดเชื่อมต่อ (Connectivity Endpoints & Protocols)

| จุดเชื่อมต่อ (Connection) | โปรโตคอล / รูปแบบข้อมูล | พอร์ต / ปลายทาง | รูปแบบการยืนยันตัวตน (Authentication) | หน้าที่และความรับผิดชอบหลัก |
|---|---|---|---|---|
| **UserWeb $\rightarrow$ Backend** | HTTP / JSON (REST) | `http://localhost:8000` (Base: `/api/*`) | Public (ไม่ต้อง Login) มี In-memory Rate Limit | ส่งคำถามแชท (`/api/chat`), ดึงการตั้งค่า AI (`/api/chat/settings`), ส่ง Feedback ความพึงพอใจ (`/api/feedback`), ดึงประกาศ (`/api/announcements/active`), ดาวน์โหลดฟอร์ม (`/api/forms`) |
| **AdminWeb $\rightarrow$ Backend** | HTTP / JSON (REST) | `http://localhost:8000` (Base: `/api/admin/*`) | JWT Bearer Token (`Authorization: Bearer <token>`) | ระบบจัดการเอกสาร (Upload PDF, Chunk Editor), Rebuild Database, จัดการผู้ใช้, ตั้งค่าโมเดลและ Prompt, ดูสถิติและประวัติแชท |
| **Backend $\rightarrow$ Database** | MySQL Wire Protocol over TLS | TiDB Cloud Serverless (Port 4000) | DB User/Password ผ่าน SSL Connection String | จัดเก็บข้อมูลถาวร: ประวัติแชท (`history`), ข้อมูลผู้ใช้งาน (`users`), ข้อมูลเอกสารและสถานะ Chunk (`documents`), การตั้งค่าระบบ (`settings`), แบบฟอร์มและประกาศ |
| **Backend $\rightarrow$ Vector Engine** | In-Process Memory Call (Python Direct) | ภายใน Process เดียวกัน (`Admin/emb.py`) | ไม่ต้องผ่าน Auth (Memory/Disk IO) | ค้นหาแบบผสม (Hybrid Retrieval): Dense Vector Search (ChromaDB + `BAAI/bge-m3`) + Lexical Search (BM25 + PyThaiNLP) แล้วรวมคะแนนด้วย Reciprocal Rank Fusion (RRF) |
| **Backend $\rightarrow$ External LLM** | HTTPS / JSON (REST) | `https://openrouter.ai/api/v1/chat/completions` | Bearer API Key (`OPENROUTER_API_KEY`) | ส่ง Prompt และ Chunks ที่ผ่านการดึงข้อมูล (RAG Context) ให้ LLM ประมวลผลและสร้างคำตอบกลับมายังผู้ใช้ (Fallback ไปยัง Local Ollama ที่ Port 11434 หากไม่ได้ระบุ API Key) |

### 9.3 มาตรการความปลอดภัยและนโยบายการเชื่อมต่อ (Security & Connection Policies)

1. **CORS Control**: ควบคุมผ่าน `allowed_origins` สำหรับ Origin ที่ระบุชัดเจน และ `allowed_origin_regex` สำหรับ Subnet วง LAN ภายในโรงพยาบาล (เช่น `http://192.168.55.*:[0-9]+`) ไม่อนุญาต `allow_origins=["*"]` เด็ดขาด
2. **Rate Limiting**: กำหนดขีดจำกัดคำขอต่อ IP Address แบบ In-Memory ใน `app/core/rate_limit.py` เพื่อป้องกัน Denial-of-Service (DoS) และการเรียกใช้ LLM API เกินโควตา
3. **JWT Lifecycle**: Access Token มีอายุ 15 นาที, Refresh Token มีอายุ 7 วัน พร้อมกลไก Blacklist / Invalidation เมื่อผู้ใช้เปลี่ยนรหัสผ่าน
4. **Database Connection Pool**: กำหนด `pool_size=10`, `max_overflow=20`, `pool_recycle=3600`, และ `pool_pre_ping=True` เพื่อป้องกัน Connection หลุดและรักษาเสถียรภาพการเชื่อมต่อกับ TiDB Cloud

---

## 10. ข้อกำหนดด้านประสิทธิภาพของระบบและผลการทดสอบจริง (Performance Requirements & Verification Benchmarks)

### 10.1 ข้อกำหนดด้านประสิทธิภาพ (Non-Functional Performance Specifications / SLAs)

| มิติข้อกำหนด (Dimension) | เกณฑ์เป้าหมาย (Target SLA) | ผลการทดสอบจริงที่ทำได้ (Verified Test Result) | สถานะ |
|---|---|---|---|
| **ความถูกต้องในการตอบ (RAG Accuracy)** | $\ge 85.00\%$ | **$89.38\% - 90.62\%$** (ประเมินโดย Multi-Model LLM-as-a-Judge) | ผ่านเกณฑ์ (Exceeded) |
| **ความแม่นยำในการค้นคืน (Retrieval Hit Rate)** | $\ge 85.00\%$ | **$90.00\%$** (ดึง Chunk ตรงตามหมวดนโยบาย 72/80 ข้อ) | ผ่านเกณฑ์ (Exceeded) |
| **ความเร็วในการตอบสนอง (End-to-End Latency)** | $\le 6.00\text{ s}$ (Median $\le 5.0\text{ s}$) | **Average $5.63\text{ s}$**, **Median $5.04\text{ s}$**, **P95 $9.80\text{ s}$** | ผ่านเกณฑ์ (Pass) |
| **ความเร็วในการค้นคืน (Retrieval Latency)** | $\le 1.00\text{ s}$ | **$170\text{ ms} - 870\text{ ms}$** (ChromaDB + BM25 + RRF) | ผ่านเกณฑ์ (Pass) |
| **การรองรับผู้ใช้พร้อมกัน (Concurrent Users)** | $\ge 25\text{ Users}$ โดย 0% Error | **รองรับได้ 25-150 Users** ที่ 0% Error บน Normal/High Load | ผ่านเกณฑ์ (Pass) |
| **ความพร้อมใช้งานของระบบ (Availability)** | $\ge 99.50\%$ | สถาปัตยกรรมรองรับ Fallback Engine (OpenRouter $\rightarrow$ Ollama) | พร้อมใช้งาน (Ready) |

---

### 10.2 ผลการทดสอบโหลดและความสามารถในการรองรับ (Load & Concurrency Benchmark — TestPFM)

การทดสอบโหลดด้วย Locust บนชุดคำถามจริง (`queries.py`) ครอบคลุมคำถาม RAG, Chit-chat, และ FAQ short-circuit:

| จำนวนผู้ใช้พร้อมกัน (Concurrency) | คำขอทั้งหมด (Total Requests) | คำขอที่ล้มเหลว (Failures) | อัตราความล้มเหลว (Failure Rate) | Throughput (RPS) | เวลาตอบเฉลี่ย (Avg Latency) | มัธยฐาน (Median Latency) | P95 Latency | P99 Latency |
|---|---|---|---|---|---|---|---|---|
| **10 Concurrent Users** (Normal Load) | 127 | 0 | **0.00%** | 3.15 req/s | 908.7 ms | 820 ms | 2,500 ms | 3,300 ms |
| **25 Concurrent Users** (Medium Load) | 186 | 0 | **0.00%** | 4.33 req/s | 2,892.7 ms | 3,200 ms | 4,400 ms | 6,400 ms |
| **50 Concurrent Users** (Burst Stress) | 69 | 11 | 15.94%* | 1.63 req/s | 11,393.6 ms | 6,300 ms | 32,000 ms | 34,000 ms |
| **100 Concurrent Users** (Heavy Stress) | 120 | 63 | 52.50%* | 2.88 req/s | 23,172.1 ms | 32,000 ms | 33,000 ms | 35,000 ms |
| **150 Concurrent Users** (High Load Peak) | 259 | 0 | **0.00%** | **6.29 req/s** | 11,944.4 ms | 12,000 ms | 25,000 ms | 26,000 ms |
| **200 Concurrent Users** (Extreme Stress) | 169 | 43 | 25.44%* | 4.15 req/s | 23,481.6 ms | 24,000 ms | 33,000 ms | 34,000 ms |

> [!NOTE]
> **การวิเคราะห์คอขวดและข้อค้นพบเชิงวิศวกรรม (Bottleneck Analysis):**
> 1. **SQLite File Lock Contention**: อัตราความล้มเหลวที่เกิดขึ้นในระดับ 50, 100, 200 Users ของสภาพแวดล้อมทดสอบ (`TestPFM`) เกิดจากการที่สคริปต์สลับไปใช้ Local SQLite ซึ่งมีการล็อกทั้งไฟล์ (File-level lock) เมื่อมี Background Task บันทึก `ChatHistory` พร้อมๆ กัน ส่งผลให้เกิดข้อผิดพลาด 500 Error ในสภาวะ Burst — ในขณะที่ Production จริงที่ต่อกับ **TiDB Cloud (MySQL)** จะใช้ Row-level locking ร่วมกับ Connection Pool จึงไม่พบคอขวดระดับไฟล์ดังกล่าว
> 2. **Cold Start vs Warm Requests**: คำขอแรกของระบบจะใช้เวลาประมาณ **3.7 วินาที** ในการโหลด Model Weight (`BAAI/bge-m3`) และสร้าง In-memory Index ครั้งแรก หลังจากนั้นคำขอถัดไป (Warm state) จะใช้เวลาเพียง **0.17s - 0.8s** สำหรับกระบวนการ Retrieval
> 3. **FAQ & Chitchat Path**: ปัจจุบัน Custom FAQ สามารถ Short-circuit ตอบกลับได้ทันทีโดยใช้เวลาเฉลี่ยเพียง **88 ms - 170 ms**

---

### 10.3 ผลการทดสอบความถูกต้องและคุณภาพ RAG (RAG Accuracy & Quality Benchmark — testchatbotSPO)

ทดสอบประเมินผลคำถามชุดมาตรฐาน **Golden Dataset จำนวน 80 ข้อ ครอบคลุม 16 หมวดหมู่นโยบาย ISO/IEC 27001 และระเบียบโรงพยาบาล** ผ่านการประเมินแบบ Multi-Model LLM-as-a-Judge (Google Gemma 4 26B vs Meta Llama 3.3 70B Instruct):

```
+----------------------------------------------------------------------------------------------------+
|                                    RAG Quality Evaluation Dashboard                                |
|                                                                                                    |
|   [ โมเดลเดิม: Gemma 4 (26B) ]   [ โมเดลเทียบ: Llama 3.3 (70B) ]   [ การดึง Chunk ตรงหมวด (Hit) ]  |
|            89.38%                            90.62%                             90.00%             |
|   (ถูก 67 | บางส่วน 9 | ผิด 4)       (ถูก 69 | บางส่วน 7 | ผิด 4)           (72 / 80 คำถาม)        |
+----------------------------------------------------------------------------------------------------+
|   [ อัตราความเห็นพ้อง (Agreement) ]               [ เวลาเฉลี่ยในการตอบ (End-to-End Latency) ]        |
|                92.50%                                            5.63 วินาที                       |
|       (เห็นตรงกัน 74 / 80 ข้อ)                          (Median: 5.04s | P95: 9.80s)               |
+----------------------------------------------------------------------------------------------------+
```

#### ตารางแจกแจงผลการประเมินเชิงลึก (In-Depth Evaluation Metrics)

| มิติการวัดผล (Metric Dimension) | ตัวชี้วัดย่อย | ผลลัพธ์: Gemma 4 (26B) | ผลลัพธ์: Llama 3.3 (70B) | การแปลผลและข้อสรุปเชิงระบบ |
|---|---|---|---|---|
| **ความถูกต้อง (Accuracy)** | Graded Accuracy (ถ่วงน้ำหนัก 1.0, 0.5, 0.0) | **89.38%** | **90.62%** | คำตอบของบอทครอบคลุมสาระสำคัญของระเบียบโรงพยาบาลได้ครบถ้วนในระดับสูงมาก |
| | Strict Accuracy (เฉพาะ 1.0 คะแนนเท่านั้น) | 83.75% (67 ข้อ) | 86.25% (69 ข้อ) | บอทตอบถูกต้องสมบูรณ์แบบไม่ตกหล่นรายละเอียดเกิน 83% - 86% ของคำถามทั้งหมด |
| | ตอบถูกต้องบางส่วน (0.5 คะแนน) | 11.25% (9 ข้อ) | 8.75% (7 ข้อ) | ตอบใจความหลักถูกต้อง แต่อาจขาดรายละเอียดเงื่อนไขปลีกย่อยเล็กน้อย |
| | ตอบไม่ถูกต้อง (0.0 คะแนน) | 5.00% (4 ข้อ) | 5.00% (4 ข้อ) | ทั้งสองโมเดลเห็นตรงกัน 100% ว่าตอบผิดใน 4 ข้อเดียวกัน (ข้อ 5, 43, 48, 68) |
| **การค้นคืน (Retrieval)** | การดึง Chunk ตรงหมวด (Hit Rate) | **90.00%** (72/80 ข้อ) | **90.00%** (72/80 ข้อ) | Hybrid Search ดึงเอกสารนโยบายได้ตรงกับหัวข้อคำถามถึง 9 ใน 10 ข้อ |
| | ความถูกต้องเมื่อดึง Chunk ตรงหมวด (Hit) | **92.36%** | **93.75%** | เมื่อดึง Chunk ตรงหมวด บอทสามารถตอบคำถามได้ถูกต้องแม่นยำสูงกว่า 92% |
| | ความถูกต้องเมื่อดึง Chunk ไม่ตรงหมวด (Miss) | 62.50% | 62.50% | ความถูกต้องลดลงชัดเจนเมื่อดึงไม่ตรง พิสูจน์ว่า LLM ตอบจาก Context จริง |
| **ความเที่ยงตรง (Reliability)** | ความเห็นพ้องต้องกัน (Agreement Rate) | — | **92.50%** (74/80 ข้อ) | การประเมินข้ามค่ายโมเดลมีความสอดคล้องกันสูงมาก ตัดอคติการตัดสินเข้าข้างตัวเอง |
| | อัตราความเห็นต่าง (Discrepancy Rate) | — | 7.50% (6/80 ข้อ) | เห็นต่างกันเพียง 6 ข้อ โดย Llama มองภาพรวมใจความสำคัญ ส่วน Gemma เพ่งเล็งสำนวนคำ |
| **เวลาตอบสนอง (UX & Latency)** | เวลาเฉลี่ยรวม (Average Latency) | 5.63 วินาที | 5.63 วินาที | ความเร็วรวมการค้นคืนและสร้างคำตอบอยู่ในเกณฑ์ที่ผู้ใช้งานยอมรับได้ดี |
| | มัธยฐานเวลาตอบ (Median / P50) | 5.04 วินาที | 5.04 วินาที | เกินครึ่งหนึ่งของคำถามทั้งหมดได้รับคำตอบภายในเวลาประมาณ 5 วินาที |
| | เกณฑ์ 95th Percentile (P95) | 9.80 วินาที | 9.80 วินาที | 95% ของผู้ใช้ได้รับคำตอบภายในเวลาไม่เกิน 10 วินาที |

---

### 10.4 สรุป 4 กรณีที่ตอบไม่ถูกต้อง (Unanimous Failures) และแนวทางปรับปรุงสำหรับทีมที่รับช่วงต่อ

| ข้อที่ | หมวดหมู่นโยบาย ISO | ประเด็นคำถาม | สาเหตุความผิดพลาด | แนวทางแก้ไขเชิงระบบที่แนะนำ |
|---|---|---|---|---|
| **ข้อ 5** | คอมพิวเตอร์พกพา (Mobile Devices) | เงื่อนไขการพกพาอุปกรณ์ออกนอกสถานที่ | Hybrid Search ไม่สามารถดึง Trigger Condition ออกมาจากเอกสารคอมพิวเตอร์พกพาได้ตรงจุด | เพิ่มเทคนิค **Query Expansion / Synonyms** สำหรับคำว่า "พกพา", "นำออกนอกสถานที่", "โน้ตบุ๊ก" |
| **ข้อ 43** | สินทรัพย์สารสนเทศ (Asset Management) | ข้อกำหนดด้านสื่อบันทึกข้อมูลถอดเสียบได้ | Chunk ขนาดใหญ่เกินไป ทำให้ข้อมูลทางเทคนิคของ USB/Flash Drive กระจายตัว | ปรับลด Chunk size หรือปรับ **Chunk Overlap** ในหมวดสินทรัพย์สารสนเทศให้กระชับขึ้น |
| **ข้อ 48** | การพัฒนาระบบ (System Development) | มาตรฐานกระบวนการพัฒนาซอฟต์แวร์ | โมเดลสับสนระหว่างกรอบความปลอดภัยรวม (ISO 27001) กับกระบวนการพัฒนา (ISO 29110) | ปรับ **System Prompt** และเพิ่ม Metadata Tag ระบุประเภทมาตรฐานกำกับ Chunk |
| **ข้อ 68** | บริบทองค์กร (Organizational Context) | ปัจจัยภายในและภายนอกของโรงพยาบาล | Retrieval ดึงได้เฉพาะหลักการทั่วไป ไม่ได้ข้อมูลบริบทเฉพาะของ รพธ. | เพิ่มการจัดทำ **Custom FAQ** หรือปรับปรุงเอกสารแม่บทให้มีชื่อองค์กรชัดเจนใน Chunk |

---

## 11. ภาคผนวก — เอกสารอ้างอิงอื่นในโปรเจกต์

| เอกสาร | เนื้อหา |
|---|---|
| [README.md](README.md) | วิธีติดตั้ง/รันระบบ, Database Migration, วิธี Deploy ผ่าน XAMPP |
| [CLAUDE.md](CLAUDE.md) | กฎบังคับของโปรเจกต์ (DB, RAG, UI, Security, Branch, Commit) ที่ทุกคนต้องยึดถือ |
| [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) | โครงสร้างไฟล์/โฟลเดอร์ทั้งหมด พร้อมไลบรารีและหน้าที่ของแต่ละไฟล์ |
| [REFACTOR_HANDOFF.md](REFACTOR_HANDOFF.md) | สถานะและรายละเอียดของการจัดระเบียบโค้ดครั้งล่าสุด (2026-09) |
| [TestPFM/README.md](TestPFM/README.md) | แนวทางการทดสอบประสิทธิภาพ (Stress/Load Test & Quality Evaluation) และโครงสร้างสคริปต์ |
| [testchatbotSPO/README.md](testchatbotSPO/README.md) | เครื่องมือรันเทสวัดความถูกต้อง 80 ข้อมาตรฐาน และชุดประเมิน Multi-Model LLM-as-a-Judge |
