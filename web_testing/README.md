# web_testing

ชุดทดสอบเว็บ (Unit → Integration → E2E) ตาม "แผนทดสอบเว็บ" — แยกจาก `TestPFM/` (Performance)
และ `testchatbotSPO/` (ความแม่นยำคำตอบแชทบอท) โดยเจตนา เพราะเป็นคนละเรื่องกัน (ดู CLAUDE.md)

ชื่อฟังก์ชันเทสทุกตัวขึ้นต้นด้วยรหัส test case ที่ตรงกับเอกสาร "แผนทดสอบเว็บ" (เช่น
`test_UT01_...` ตรงกับ UT-01 ในตาราง T3) เพื่อ trace กลับไปที่เอกสารออกแบบได้ตรงๆ

## โครงสร้าง

```
web_testing/
  unit/                      # Unit Test (T3) ฝั่ง Backend — pytest, ไม่พึ่ง DB/HTTP
    conftest.py              # เติม Backend/ และ project root เข้า sys.path
    test_ut_auth.py          # UT-01 ถึง UT-05 (hash password, JWT)
    test_ut_security.py      # UT-06 ถึง UT-08 (sanitize HTML, path traversal)
    test_ut_chat_logic.py    # UT-10 ถึง UT-12 (chit-chat, คำหยาบ, ความยาวคำถาม)
    test_ut_settings.py      # UT-13 (ขอบเขตค่า settings)
    test_ut_announcement.py  # UT-14 (สถานะ active ของประกาศ)
    test_ut_rag_logic.py     # UT-09 (คะแนน Weighted RRF)
    results_2026-09-21.log   # ผลรันล่าสุด (pytest)
  unit-frontend/             # Unit Test ฝั่ง Frontend (UserWeb) — Vitest
    formatters.test.js       # FE-01, FE-02 (stripHtml, formatAnnDate)
    results_2026-09-21.log   # ผลรันล่าสุด (vitest)
  integration/               # Integration Test (T3) — pytest + httpx.AsyncClient + SQLite
    conftest.py              # ยืม fixture จาก Backend/tests/conftest.py ตรงๆ (ไม่ copy โค้ดซ้ำ)
    test_it_documents.py     # IT-01, IT-02 (อัปโหลด/ลบเอกสาร)
    test_it_auth_flow.py     # IT-03 (login จริง -> ใช้ token ข้าม router)
    test_it_settings.py      # IT-04, IT-05 (settings ส่งผลถึง chat, key masking)
    test_it_feedback.py      # IT-06 (feedback dedup)
    test_it_unanswered.py    # IT-07 (unanswered increment + triage)
    test_it_announcements.py # IT-08 (ประกาศ CRUD + public active list)
    test_it_chat_history.py  # IT-09 (บันทึกประวัติแชทผ่าน background task)
    test_it_index_deletion.py # เทส Admin.emb.delete_document_from_index() ตรงๆ (sync, ไม่ใช่ HTTP)
    results_2026-09-21.log   # ผลรันล่าสุด (pytest)
```

`e2e/` ยังไม่ได้สร้าง — จะเพิ่มตามลำดับพีระมิดในเอกสารแผนทดสอบ

## วิธีรัน

```bash
# Backend Unit (จาก root ของโปรเจกต์)
python -m pytest web_testing/unit/ -v

# Backend Integration (จาก root ของโปรเจกต์)
python -m pytest web_testing/integration/ -v

# Frontend (จาก UserWeb/)
cd UserWeb
npm run test
```

Backend: ไม่ต้องตั้งค่าอะไรเพิ่ม — `conftest.py` เติม path ให้ import `app.*` จาก `Backend/`
เองอัตโนมัติ และ `Backend/.env` ที่มีอยู่แล้วจะถูกใช้ตามปกติ (เฉพาะฟังก์ชันที่ไม่แตะ DB จริง
จึงไม่มีความเสี่ยงต่อข้อมูล production แม้ใช้ `.env` เดียวกับที่ชี้ไป TiDB Cloud)

Frontend: `UserWeb/vitest.config.js` ชี้ไปที่ `../web_testing/unit-frontend/**/*.test.js` (นอก
`UserWeb/` เพื่อให้เทสทั้งฝั่ง Backend/Frontend อยู่ใต้ `web_testing/` เดียวกัน) และเปิด
`server.fs.allow` ให้ serve ไฟล์นอก root ได้ — ต้อง `npm install` ใน `UserWeb/` ก่อนครั้งแรก
(ติดตั้ง `vitest`/`jsdom` เป็น devDependencies แล้ว)

## สถานะล่าสุด (2026-09-21)

**44 passed, 0 skipped** — ครบทั้ง 14 test case แล้ว

- UT-14 แก้ไขโดยแยกฟังก์ชัน `is_announcement_active()` ออกมาจาก
  `compatibility_active_announcements()` ใน `Backend/app/routers/public.py` (พฤติกรรมเดิมทุกกรณี
  ตรวจแล้วว่า integration test เดิมของ endpoint นี้ยังผ่านตามปกติ)
- UT-09 แก้ไขโดยแยกฟังก์ชัน `weighted_rrf_score(rank, weight, rrf_k=60)` ออกมาจาก closure
  `merge_results()` ภายใน `HybridRetriever.query()` ใน `Admin/emb.py` — ได้รับอนุญาตให้แก้ RAG
  pipeline แล้ว (2026-09-21) สูตรและพฤติกรรมเดิมทุกกรณี ไม่ได้แก้ logic การคำนวณ ตรวจแล้วว่า
  `Admin/emb.py` compile ผ่านและ `HybridRetriever`/`weighted_rrf_score` import ได้ปกติ

| UT | ไฟล์ | ผล |
|---|---|---|
| UT-01 | test_ut_auth.py | Pass |
| UT-02 | test_ut_auth.py | Pass |
| UT-03 | test_ut_auth.py | Pass |
| UT-04 | test_ut_auth.py | Pass |
| UT-05 | test_ut_auth.py | Pass |
| UT-06 | test_ut_security.py | Pass |
| UT-07 | test_ut_security.py | Pass |
| UT-08 | test_ut_security.py | Pass |
| UT-09 | test_ut_rag_logic.py | Pass |
| UT-10 | test_ut_chat_logic.py | Pass |
| UT-11 | test_ut_chat_logic.py | Pass |
| UT-12 | test_ut_chat_logic.py | Pass |
| UT-13 | test_ut_settings.py | Pass |
| UT-14 | test_ut_announcement.py | Pass |

### Frontend (Vitest) — เพิ่มเติมนอกเอกสารแผนทดสอบเดิม

**12 passed, 0 failed** — `stripHtml`/`formatAnnDate` แยกออกมาจาก `UserWeb/src/App.jsx` เป็น
`UserWeb/src/utils/formatters.js` (behavior เดิมทุกกรณี ไม่ได้แก้ logic) เพื่อ unit test ได้โดยไม่ต้อง
render component เต็มรูปแบบ

รหัส FE-01/FE-02 เป็นรหัสเสริมที่ตั้งขึ้นเอง **ไม่ได้อยู่ในตาราง T3 ของเอกสาร "แผนทดสอบเว็บ" เดิม**
(เอกสารเดิมไม่ได้ระบุ test case ฝั่ง frontend ไว้) ถ้าต้องการให้เป็นทางการควรเพิ่มเข้าเอกสารแผนทดสอบ
แยกต่างหาก

| รหัส | ฟังก์ชัน | ไฟล์เทส | ผล |
|---|---|---|---|
| FE-01 | stripHtml | formatters.test.js | Pass (5 เทส) |
| FE-02 | formatAnnDate | formatters.test.js | Pass (7 เทส) |

**หมายเหตุสภาพแวดล้อม:** รันตรงจาก `UserWeb/` บน `Z:` (mapped network drive) ไม่ได้ — เจอ
`Error: ... Received protocol 'z:'` ตั้งแต่ก่อน collect เทส ตรวจแล้วว่าเป็นบั๊กระดับ
Node.js 24 (ESM loader) ร่วมกับ mapped drive ที่มีช่องว่างในชื่อ share ("Share fire") ไม่ใช่บั๊ก
จากโค้ดเทสหรือ config ที่เขียนในรอบนี้ (แม้แต่ `vite build` เปล่าๆ ก็พังแบบเดียวกัน) เพื่อให้ได้ผลจริง
ไม่ใช่ผลปลอม จึงคัดลอกไฟล์ชุดเดียวกันไปรันที่ไดรฟ์ local แล้วได้ผล 12 passed ตามด้านบน — ไฟล์ที่
commit เข้า repo คือไฟล์เดียวกับที่รันจริงทุกตัวอักษร รายละเอียดเต็มอยู่ใน
`web_testing/unit-frontend/results_2026-09-21.log`

## Integration Test (2026-09-21)

**32 passed, 0 failed** — 9 test case (IT-01 ถึง IT-09) รหัส IT- เป็นรหัสเสริมที่ตั้งขึ้นเอง
เช่นเดียวกับ FE-01/FE-02 **ไม่ได้อยู่ในตาราง T3 ของเอกสาร "แผนทดสอบเว็บ" เดิม** (เอกสารเดิมมีแค่
14 test case ฝั่ง unit) ถ้าต้องการให้เป็นทางการควรเพิ่มเข้าเอกสารแผนทดสอบแยกต่างหาก

ทุกเทสยิง endpoint จริงผ่าน `httpx.AsyncClient` เข้า FastAPI app + SQLite in-memory (fixture
ชุดเดียวกับ `Backend/tests/conftest.py` ไม่ได้ copy code ซ้ำ — ดู `web_testing/integration/conftest.py`)
ไม่แตะ TiDB Cloud จริง

| รหัส | เรื่อง | ไฟล์เทส | ผล |
|---|---|---|---|
| IT-01 | อัปโหลดเอกสาร | test_it_documents.py | Pass (3 เทส) |
| IT-02 | ลบเอกสาร (SQL/ไฟล์/ลบออกจากดัชนีค้นหาจริง) | test_it_documents.py + test_it_index_deletion.py | Pass (5 เทส) |
| IT-03 | Login จริง -> token ใช้ข้าม router | test_it_auth_flow.py | Pass (2 เทส) |
| IT-04 | ตั้งค่าส่งผลถึงพฤติกรรมแชทจริง | test_it_settings.py | Pass (3 เทส) |
| IT-05 | ปิดบัง API key ตามสิทธิ์ผู้เรียก | test_it_settings.py | Pass (3 เทส) |
| IT-06 | Feedback dedup by (query, answer) | test_it_feedback.py | Pass (5 เทส) |
| IT-07 | Unanswered เพิ่ม count + triage | test_it_unanswered.py | Pass (4 เทส) |
| IT-08 | ประกาศ CRUD + public active list | test_it_announcements.py | Pass (5 เทส) |
| IT-09 | บันทึกประวัติแชทผ่าน background task | test_it_chat_history.py | Pass (2 เทส) |

### [แก้แล้ว 2026-09-21] ช่องว่างจริงของระบบ: ลบเอกสารแล้ว ChromaDB ไม่ถูกลบจริง

พบระหว่างออกแบบ IT-02: เดิมการลบเอกสารเชื่อมกับ ChromaDB ผ่านการสั่ง `_trigger_rebuild_background()`
เท่านั้น ซึ่งเป็นการ rebuild **ทั้ง collection ใหม่หมด** (ลบ `tuh_collection` ทิ้งแล้วสร้างใหม่, โหลด
โมเดล `BAAI/bge-m3` จริง) ไม่ใช่ "ลบ vector ของไฟล์นี้ไฟล์เดียว" และอ่านสถานะเอกสาร "Active" จากไฟล์
JSON เดิม (`user/backend/db/db_documents.json`) ไม่ใช่จากตาราง SQL จริง — ผลคือลบเอกสารแล้ว vector
ยังค้างอยู่ในดัชนีจนกว่าจะมีคน rebuild เองอีกที **ได้รับอนุญาตให้แก้ไขแล้ว** (เลือก scope "แก้ให้ลบ
vector ได้จริงทันที" จาก 3 ทางเลือกที่เสนอ) — แก้โดย:

- เพิ่ม `Admin.emb.delete_document_from_index(filename, index_dir=None, chroma_dir=None, retriever=None)`
  ลบ chunk ของไฟล์นั้นออกจาก BM25 (อ่าน-กรอง-เขียนทับ `bm25.pkl`) และ ChromaDB
  (`collection.delete(where={"source": filename})`) **ทันที ไม่ต้องรอ rebuild และไม่ต้องโหลดโมเดล
  embedding เลย** (การลบไม่ต้องเข้ารหัสข้อความใหม่) — ถ้ามี `HybridRetriever` โหลดอยู่ในหน่วยความจำ
  ของเซิร์ฟเวอร์อยู่แล้ว (ระบุผ่านพารามิเตอร์ `retriever`) จะ sync `.bm25`/`.bm25_chunks` ของ instance
  นั้นด้วย ไม่ใช่แค่เขียนไฟล์เฉยๆ ไม่งั้นแชทที่กำลังทำงานอยู่จะยังเห็นข้อมูลเก่าจนกว่าจะรีสตาร์ตเซิร์ฟเวอร์
- `Backend/app/routers/admin.py`: `delete_document`/`delete_document_post` เปลี่ยนจาก
  `background_tasks.add_task(_trigger_rebuild_background)` เป็น
  `background_tasks.add_task(_delete_from_search_index, filename)` (endpoint อื่นที่ยังต้องการ
  rebuild ทั้งคลัง เช่น `toggle_document`/`update_exclude`/`approve` ไม่ได้แตะ ยังใช้
  `_trigger_rebuild_background` เหมือนเดิม)

**คำเตือนสำหรับใครมาอ่านโค้ดต่อ**: เครื่องพัฒนานี้มี ChromaDB/BM25 ของจริงอยู่ 2 ชุด
(`C:\Users\ITS\tuh-chatbot-db\chroma_db` ที่ retriever ตัวจริงใช้ กับ `<repo>/index_db/` ที่เป็น
default เวลาไม่ระบุ `index_dir`) — เทสทั้งหมดจึงต้อง mock หรือชี้ `index_dir`/`chroma_dir` ไปที่
`tmp_path` เสมอ ห้ามเรียก `delete_document_from_index()` แบบไม่ระบุพารามิเตอร์เหล่านี้ในเทสเด็ดขาด
(ดู `web_testing/integration/test_it_index_deletion.py` และคำเตือนในไฟล์ `test_it_documents.py`)
ตรวจสอบแล้วว่าหลังรันเทสทั้งหมด ทั้งสอง directory ของจริงไม่ถูกแตะต้องเลย (timestamp ไม่เปลี่ยน)

## หมายเหตุ: พบปัญหาอื่นระหว่างตรวจ regression (ยังไม่ได้แก้)

`Backend/tests/test_public.py::test_compatibility_search_returns_citations_for_rag_answer` **ล้มเหลว**
เมื่อรันแยก (`pytest tests/ -k "rag or search or announcement"` จาก `Backend/`) — ไม่เกี่ยวกับการแก้ไข
UT-09/UT-14 ในรอบนี้ (ไฟล์ที่แก้วันนี้ไม่แตะ `has_reliable_context`) สาเหตุคือ `_StubRetriever` ในเทสคืนผล
โดยไม่มี key `dense_score` เลย ทำให้ `has_reliable_context()` (เพิ่มไว้ก่อนหน้านี้ในเซสชัน) มองว่า
top dense score = 0.0 ซึ่งต่ำกว่า threshold 0.42 จึงไม่แนบ citations ทั้งที่เทสคาดหวังว่าต้องมี — น่าจะเป็น
ผลข้างเคียงจาก fix เรื่อง citation ที่ทำไปก่อนหน้า ยังไม่ได้แก้เพราะอยู่นอกขอบเขตงาน UT-09 รอบนี้

**[แก้แล้ว 2026-09-21]** `Backend/tests/test_alembic_migration.py::test_upgrade_head_creates_all_model_tables`
และ `::test_downgrade_base_drops_all_model_tables` เคยล้มเหลว เพราะ migration `8c35f97ca61f` (เพิ่ม
`uploaded_by_id`/`created_by_id` FK ก่อนหน้านี้ในเซสชัน) ใช้ `op.create_foreign_key()`/`op.drop_constraint()`
ตรงๆ ซึ่ง SQLite ไม่รองรับการ ALTER constraint แบบนี้ — แก้โดยห่อทุกจุดที่ add/drop column และ
add/drop FK constraint ด้วย `op.batch_alter_table(...)` แยก block ระหว่าง "เพิ่มคอลัมน์" กับ "เพิ่ม FK"
เสมอ (เพราะคำสั่ง backfill ข้อมูลที่รันคั่นกลางต้องเห็นคอลัมน์ที่ apply จริงแล้ว ไม่ใช่แค่ถูก queue ไว้ใน
batch) — บน MySQL/TiDB จริง batch mode (`recreate="auto"`) ส่ง ALTER ตรงๆ เหมือนเดิมทุกกรณี ไม่กระทบ
พฤติกรรมเดิมบน production ตรวจแล้วว่าเทสทั้งสองผ่านและรัน `Backend/tests/` ทั้งหมดซ้ำไม่มี regression เพิ่ม
