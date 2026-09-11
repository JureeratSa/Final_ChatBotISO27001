# TestPFM — Performance Testing

Performance test สำหรับ `/api/chat` แยกออกจาก `Backend/tests/` โดยตั้งใจ เพราะ
`Backend/tests/` คือ pytest correctness suite (mock ทุกอย่างให้ deterministic, รันใน CI ได้)
ส่วนที่นี่คือการยิงโหลดใส่ server ที่รันจริงเพื่อวัด throughput/latency/answer quality — ไม่ควรรันใน CI

## ✅ ไม่ต้องใช้ Docker / MySQL เลย

`Backend/app/core/config.py` มี default `DATABASE_URL` ชี้ไป **TiDB Cloud production จริง**
ถ้าปล่อยให้ server ต่อ DB ปกติ ทุก request จะ background-task เขียนแถวจริงลง `ChatHistory` —
เพื่อไม่ให้เสี่ยงแตะ production เลย สคริปต์ในนี้ทุกตัว (`mock_server.py`, `run_full_server.py`)
สลับ DB ไปเป็น **SQLite ไฟล์ local** ให้อัตโนมัติผ่าน [`db_patch.py`](db_patch.py) — หลักการเดียวกับที่
`Backend/tests/conftest.py` ใช้ SQLite in-memory สำหรับ pytest — ไม่ต้องตั้งค่า `.env` เรื่อง DB
หรือเปิด Docker/MySQL ใดๆ เลย รันคำสั่งได้ทันที (ทดสอบแล้วว่าใช้งานได้จริงบนเครื่องนี้)

ข้อจำกัดที่ต้องรู้: SQLite ล็อกทั้งไฟล์ตอนเขียน (MySQL/TiDB จริง lock ระดับแถว) ที่ concurrency
สูงมากๆ ตัวเลข throughput ที่วัดได้อาจ "ต่ำกว่า" ของจริงบน production เพราะ SQLite เองกลายเป็น
คอขวดเทียม — ใช้เทียบ "relative" ระหว่างรัน (ก่อน/หลังแก้โค้ด) ได้ แต่อย่าฟันธงว่าคือ capacity จริง
ถ้าต้องการตัวเลขแม่นกับ production จริงๆ ค่อยพิจารณาต่อ MySQL local ทีหลัง (ไม่จำเป็นสำหรับตอนนี้)

`Backend/.env` ที่มีอยู่ตอนนี้ไม่ถูกใช้โดยสคริปต์ในโฟลเดอร์นี้เลย (DB ถูก override เป็น SQLite
เสมอ) จะมีไว้ก็ต่อเมื่ออยากรัน server ตัวจริงนอก TestPFM (เช่น `uvicorn app.main:app` ตรงๆ)

## โครงสร้างไฟล์

| ไฟล์ | หน้าที่ |
|---|---|
| `db_patch.py` | สลับ DB ของ app เป็น SQLite local — เรียกก่อน import `app.main` เสมอ |
| `mock_server.py` | pipeline จริงทั้งหมดแต่ stub เฉพาะ LLM call ออก (ไม่ต้องมี API key) ฟังที่ `:8001` |
| `run_full_server.py` | pipeline จริงทั้งหมด **รวม LLM call จริง** ไป OpenRouter ฟังที่ `:8000` |
| `locustfile_retrieval.py` | ยิงใส่ `mock_server.py` — วัด Custom FAQ + HybridRetriever(Chroma+BM25+RRF) + DB ล้วนๆ |
| `locustfile_full.py` | ยิงใส่ `run_full_server.py` (มี LLM call จริง) — มีต้นทุนเงิน+rate limit จริง |
| `run_stress_sweep.py` | ไล่ concurrency หลายระดับอัตโนมัติ (10→25→50→100...) สรุปเป็นตารางหา breaking point |
| `queries.py` | ชุดคำถามตัวอย่าง (RAG / chit-chat / นอกเรื่อง) ใช้ร่วมกันทั้งสอง locustfile |
| `eval/` | Pillar 2: RAG answer quality (ดูหัวข้อด้านล่าง) |
| `docker-compose.testdb.yml` | (ทางเลือกเสริม ไม่จำเป็น) MySQL local ถ้าอยากได้ตัวเลขใกล้ production กว่า SQLite |

## ทำไมต้องแยก retrieval-only กับ full pipeline

`/api/chat` มี 2 ต้นทุนที่ลักษณะต่างกันมาก:
- **Retrieval ฝั่งเราเอง** (dense search + BM25 lexical + pythainlp tokenize + RRF merge + DB) — ปรับปรุงได้ในโค้ดเรา
- **LLM call ไป OpenRouter** — network call ภายนอก มี rate limit ของเขาเอง ปรับที่โค้ดเราไม่ได้

ถ้ายิงรวมกันแล้วเจอ error/ช้า จะแยกไม่ออกว่า "ระบบเราพัง" หรือ "โดน OpenRouter จำกัด" —
จึงต้องมี `mock_server.py` เพื่อวัดฝั่งเราล้วนๆ ก่อน แล้วค่อยเทียบกับ full pipeline

**หมายเหตุจากการตรวจโค้ดจริง (`routers/chat.py`):** มีแค่ **Custom FAQ** เท่านั้นที่ short-circuit
ก่อนถึง retriever ได้ — คำถามทักทาย/หยาบคาย (chit-chat/profanity) ก็ยังเรียก `retriever.query()`
เต็มรูปแบบก่อนเสมอ แล้วค่อยถูกทิ้งคำตอบใน `query_rag()` ทีหลัง (ดูคอมเมนต์ใน `locustfile_retrieval.py`)
เป็นจุดที่น่าเก็บไว้พิจารณาปรับปรุง performance ในอนาคต

## Setup

```bash
pip install -r TestPFM/requirements.txt
```

Prerequisite: ต้อง build index (`Admin/emb.py` / `Admin/rebuild_db.py`) ไว้แล้วอย่างน้อย 1 ครั้ง
ไม่งั้น `HybridRetriever.load()` จะ fail และ `get_retriever()` คืน `None` — ทุก query จะตกไปที่
fallback path (ยังเทสได้ แต่ไม่ใช่ retrieval จริง)

## วิธีรัน — Retrieval-only (แนะนำให้เริ่มจากตรงนี้)

เทอร์มินัลที่ 1:
```bash
python TestPFM/mock_server.py
```

เทอร์มินัลที่ 2 — แบบมี UI ปรับ user สดๆ:
```bash
locust -f TestPFM/locustfile_retrieval.py --host http://localhost:8001
# เปิด http://localhost:8089
```

หรือแบบ headless กำหนดเอง:
```bash
locust -f TestPFM/locustfile_retrieval.py --host http://localhost:8001 \
    --headless -u 100 -r 10 -t 3m --csv TestPFM/results/retrieval_100u
```

หรือไล่หา breaking point อัตโนมัติ:
```bash
python TestPFM/run_stress_sweep.py \
    --locustfile TestPFM/locustfile_retrieval.py \
    --host http://localhost:8001
```

**คำขอแรกช้าผิดปกติเสมอ (cold start)** — ตอนทดสอบพบว่า request แรกใช้เวลา ~3.7s (โหลด embedding
model/index ครั้งแรก) ส่วน request ถัดไปเหลือ ~0.17s ให้ยิง warm-up request เปล่าๆ 2-3 ครั้งก่อน
เริ่มเก็บผลจริงเสมอ ไม่งั้นค่า latency รอบแรกจะทำให้ผลเพี้ยน

## วิธีรัน — Full pipeline (มี LLM จริง, ใช้เงินจริง)

เทอร์มินัลที่ 1:
```bash
python TestPFM/run_full_server.py
```
(ต้องมี `OPENROUTER_API_KEY` หรือ `GEMINI_API_KEY` ใน `Backend/.env` ไม่งั้น fallback ไป Ollama local)

เทอร์มินัลที่ 2 — **เริ่มด้วย concurrency ต่ำๆ ก่อนเสมอ**:
```bash
locust -f TestPFM/locustfile_full.py --host http://localhost:8000 \
    --headless -u 5 -r 1 -t 2m --csv TestPFM/results/full_5u
```

## Pillar 2 — RAG Answer Quality (Human Review)

| ไฟล์ | หน้าที่ |
|---|---|
| `eval/golden_qa.csv` / `.json` | Golden dataset 80 คำถาม จาก 16 หมวดนโยบาย ISO (แปลงจาก Excel ที่ทีมเตรียมไว้) |
| `eval/build_golden_qa.py` | แปลง Excel ต้นทางเป็น golden_qa.csv/.json ใหม่ได้ถ้าไฟล์ต้นทางอัปเดต |
| `eval/run_eval.py` | ยิงทุกคำถามเข้า `/api/chat` จริง สร้างรายงานให้อ่านเทียบเอง (ไม่ตัดสินถูก/ผิดอัตโนมัติ) |

รัน (ต้องมี server รันอยู่จริงก่อน — `run_full_server.py` `:8000` หรือ `mock_server.py` `:8001` ก็ได้):
```bash
python TestPFM/eval/run_eval.py --host http://localhost:8000
```

ผลลัพธ์อยู่ที่ `TestPFM/eval/results/<timestamp>/`:
- `report.html` — เปิดใน browser อ่านคู่ question/expected/actual ทีละข้อ อ่านง่ายกว่า Excel เพราะข้อความยาว
- `report.csv` — เปิดใน Excel มีคอลัมน์ `reviewer_verdict` (ถูก/บางส่วน/ผิด) กับ `reviewer_notes` เว้นว่างไว้ให้กรอกเอง
- `raw.json` — ผลดิบทั้งหมดเผื่อเอาไปประมวลผลต่อ

## วิธีอ่านผล (Load/Stress)

- **p95 / p99 latency** สำคัญกว่า average — บอก "user โชคร้าย 5-1%" รอนานแค่ไหน ซึ่งเป็นประสบการณ์จริงที่คนจะบ่น
- **Error/Fail %** — ถ้าเริ่ม > 0 ที่ concurrency ระดับไหน นั่นเริ่มเป็นสัญญาณเตือน
- **Breaking point** — concurrency ที่ p95/p99 เริ่มพุ่งขึ้นแบบไม่เป็นเส้นตรง (ไม่ใช่แค่ค่อยๆ เพิ่ม) หรือ fail % กระโดด — คือคำตอบของ "รับโหลดพร้อมกันได้แค่ไหน"
- เทียบผล retrieval-only กับ full pipeline: ถ้า full ช้ากว่ามาก แต่ retrieval-only เร็ว → คอขวดอยู่ที่ LLM/OpenRouter ไม่ใช่โค้ดเรา ปรับปรุงฝั่งเราต่อไปจะไม่ช่วยมาก ต้องพิจารณาที่ model/timeout/caching แทน
