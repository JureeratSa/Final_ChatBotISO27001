# รัน TUH Chatbot ด้วย Docker

ไฟล์ที่เกี่ยวข้อง: [docker-compose.yml](../docker-compose.yml), [docker/](../docker/)

| Service | Port | อยู่ใน container |
|---|---|---|
| `userweb` | http://localhost:5173 | nginx เสิร์ฟ UserWeb ที่ build แล้ว |
| `adminweb` | http://localhost:5174 | nginx เสิร์ฟ AdminWeb ที่ build แล้ว |
| `backend` | http://localhost:8000 | FastAPI + ChromaDB (ฝังใน process) + BM25 + bge-m3 + Tesseract |
| `legacy-redirect` | http://localhost:8080 | redirect URL เดิมสมัย XAMPP ไปที่ 5173/5174 |

- **ChromaDB ไม่ได้เป็น container แยก** ระบบใช้ `chromadb.PersistentClient` (ไลบรารีที่อ่าน/เขียนไฟล์) จึงอยู่ใน container `backend` ไปด้วย ข้อมูลเก็บใน volume `chroma`
- **TiDB Cloud ยังเป็นฐานข้อมูลหลักตามเดิม** — ไม่มี container ฐานข้อมูล
- backend รัน **worker เดียว** เท่านั้น (ดัชนีค้นหาและสถานะ rebuild อยู่ในหน่วยความจำของ process) ห้ามเพิ่ม `--workers`
- port ชนกับ dev server (`run_user_web.py`, `run_admin_web.py`, `run_backend.py`) — ปิดตัวเดิมก่อน

## Volume (ข้อมูลที่ต้องอยู่รอดเมื่อสร้าง container ใหม่)

| Volume | path ใน container | เนื้อหา |
|---|---|---|
| `tuh-chatbot_chroma` | `/data/chroma` | ChromaDB (dense vector) |
| `tuh-chatbot_index_db` | `/app/index_db` | `bm25.pkl` — **ต้องมาจาก rebuild ครั้งเดียวกับ ChromaDB เสมอ** สำรอง/ย้ายคู่กัน |
| `tuh-chatbot_uploads` | `/app/uploads` | PDF ที่อัปโหลด, แบบฟอร์ม, cache สกัดข้อความ/OCR |
| `tuh-chatbot_model_cache` | `/cache` | โมเดล bge-m3 (~2 GB) และข้อมูล PyThaiNLP |

`docker compose down` ไม่ลบ volume — ลบเฉพาะเมื่อสั่ง `docker compose down -v` (**ข้อมูลหายหมด**)

## ติดตั้งครั้งแรก

1. มี `Backend/.env` ครบแล้ว (ค่าเดียวกับที่ใช้รันปกติ) — compose ทับ `CHROMA_DB_DIR` และ `TESSERACT_CMD` ด้วย path ใน container ให้เอง ไม่ต้องแก้ไฟล์
2. Build:
   ```bash
   docker compose build
   ```
3. ย้ายข้อมูลเดิมเข้า volume (ครั้งเดียว) — **ปิด backend ที่รันบน Windows ก่อน** กันคัดลอก ChromaDB ระหว่างกำลังเขียน:
   ```bash
   python docker/seed_volumes.py
   ```
   คัดลอก `uploads/`, `index_db/bm25.pkl`, ChromaDB จาก `CHROMA_DB_DIR` และโมเดล bge-m3 จาก HuggingFace cache
   ถ้าไม่อยากใช้ดัชนีเดิม ใช้ `--skip-index` แล้วกด rebuild ในหน้า AdminWeb หลังเปิดระบบ
4. เปิดระบบ:
   ```bash
   docker compose up -d
   docker compose logs -f backend     # รอจนเห็น "Application startup complete"
   ```

## งานประจำ

| ต้องการ | คำสั่ง |
|---|---|
| อัปเดตหลังแก้โค้ด | `docker compose up -d --build` (เฉพาะตัวเดียว: `docker compose up -d --build adminweb`) |
| ดู log | `docker compose logs -f backend` |
| หยุด / เปิด | `docker compose stop` / `docker compose start` |
| Alembic migration | `docker compose run --rm backend alembic upgrade head` |
| รัน pytest | ใช้เครื่อง dev ตามเดิม (`cd Backend && python -m pytest`) — อิมเมจไม่มี dev dependency |
| สำรองดัชนี | `docker run --rm -v tuh-chatbot_chroma:/c -v tuh-chatbot_index_db:/i -v ${PWD}:/out alpine tar czf /out/index-backup.tgz /c /i` |

## เข้าจากเครื่องอื่นใน LAN

frontend เรียก backend ที่ `http://<host ที่เปิดเว็บ>:8000` เอง จึงเปิดจากเครื่องอื่นได้ทันทีถ้า firewall เปิด port 5173/5174/8000
CORS ของ backend อนุญาต `localhost`, วง `172.30.x.x` และชื่อเครื่องใน `CORS_EXTRA_HOSTS` (ตั้งใน `Backend/.env` — ไม่ใส่ใน docker-compose.yml เพราะ repo เป็น public) ที่ port 5173/5174/8080 ([main.py](../Backend/app/main.py))
แนะนำให้ผู้ใช้เปิดด้วยชื่อเครื่องเต็ม (`http://<ชื่อเครื่อง>.<domain>:5173`) — IP ของเครื่องมาจาก DHCP เปลี่ยนได้ แต่ชื่อเครื่องไม่เปลี่ยน
ย้ายเซิร์ฟเวอร์ไปเครื่องอื่นต้องแก้ `CORS_EXTRA_HOSTS` เป็นชื่อเครื่องใหม่ ไม่งั้นหน้าเว็บเปิดได้แต่ login ไม่ได้ ("Failed to fetch")
ถ้า backend อยู่หลัง HTTPS/โดเมนอื่น ให้ build frontend ด้วย `VITE_API_URL` (build arg ใน [web.Dockerfile](../docker/web.Dockerfile))

## หมายเหตุ

- ใช้ torch รุ่น CPU (เครื่องปัจจุบันไม่มี GPU) ถ้าย้ายไปเครื่องที่มี NVIDIA GPU ต้องเปลี่ยน index ของ torch ใน [backend.Dockerfile](../docker/backend.Dockerfile) และเพิ่ม `gpus: all` ใน compose
- เวอร์ชันไลบรารีหลักถูกล็อกไว้ใน [docker/constraints.txt](../docker/constraints.txt) ให้ตรงกับเครื่อง dev — ChromaDB เปลี่ยนรูปแบบไฟล์ข้ามเวอร์ชัน อัปเกรดแล้วให้ rebuild ดัชนีใหม่
- Tesseract ใน container ใช้ข้อมูลภาษาไทยของ Debian (`tesseract-ocr-tha`) ไม่ใช่ `tessdata_best` แบบบน Windows — ใช้หาตำแหน่งบรรทัดเพื่อไฮไลท์เท่านั้น ไม่กระทบข้อความที่ใช้ตอบ (มาจาก Typhoon OCR)
- ตั้งแต่ 2026-10-29 ใช้ Docker เป็นหลัก เลิกใช้ XAMPP — service `legacy-redirect` ฟัง port 8080 แล้วส่ง URL เดิม
  (`:8080/tuh_chatbot_ai/` → `:5173`, `:8080/tuh_chatbot_ai/admin/` → `:5174`) ให้ bookmark เดิมยังใช้ได้ จึงต้องปิด Apache ของ XAMPP ไว้
- Docker Desktop เปิดเองตอน login Windows และทุก service ตั้ง `restart: unless-stopped` — รีสตาร์ทเครื่องแล้วระบบกลับมาเอง
  (ถ้าสั่ง `docker compose stop` ไว้ ต้อง `docker compose start` เองอีกครั้ง)
- Docker Desktop อ่านไฟล์บนไดรฟ์ Z: (network share) แบบ bind mount ไม่ได้ — config ที่ต้องส่งเข้า container ให้ใส่ในอิมเมจหรือเขียน inline ใน compose
