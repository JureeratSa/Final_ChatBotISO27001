# รัน TUH Chatbot ด้วย Docker

ไฟล์ที่เกี่ยวข้อง: [docker-compose.yml](../docker-compose.yml), [services/api/Dockerfile](../services/api/Dockerfile), [infra/docker/](../infra/docker/)

ผู้ใช้เข้าทาง HTTPS ที่ reverse proxy (Caddy) ตัวเดียว ตั้งแต่ 2026-10-30:

| URL | ไปที่ |
|---|---|
| `https://<host>/` | แชทบอท (`apps/chat-web`) |
| `https://<host>/admin/` | ระบบแอดมิน (`apps/admin-web`) |
| `https://<host>/api/` | Backend API (`services/api`) |
| `http://<host>:5173`, `:5174`, `:8080/tuh_chatbot_ai/...` | redirect ไป HTTPS (bookmark เดิมยังใช้ได้) |

| Service | Port บนเครื่อง | อยู่ใน container |
|---|---|---|
| `proxy` | 443, 5173, 5174, 8080 | Caddy: TLS + แยก path + redirect port เดิม |
| `userweb` | — (ผ่าน proxy) | nginx เสิร์ฟเว็บแชทบอทที่ build แล้ว |
| `adminweb` | — (ผ่าน proxy) | nginx เสิร์ฟเว็บแอดมิน (build ด้วย base `/admin/`) |
| `backend` | `127.0.0.1:8000` เท่านั้น | FastAPI + ChromaDB (ฝังใน process) + BM25 + bge-m3 + Tesseract |

- **ChromaDB ไม่ได้เป็น container แยก** ระบบใช้ `chromadb.PersistentClient` (ไลบรารีที่อ่าน/เขียนไฟล์) จึงอยู่ใน container `backend` ไปด้วย ข้อมูลเก็บใน volume `chroma`
- **ฐานข้อมูลคือ Microsoft SQL Server ของโรงพยาบาล** (ตั้งแต่ 2026-11-02) — ไม่มี container ฐานข้อมูล; image ของ backend build พร้อม ODBC Driver 18 (`WITH_MSSQL: "true"` ใน docker-compose.yml)
- backend รัน **worker เดียว** เท่านั้น (ดัชนีค้นหาและสถานะ rebuild อยู่ในหน่วยความจำของ process) ห้ามเพิ่ม `--workers`
- port ชนกับ dev server (`infra/scripts/dev.py`) — ปิดตัวนั้นก่อน

## Volume (ข้อมูลที่ต้องอยู่รอดเมื่อสร้าง container ใหม่)

| Volume | path ใน container | เนื้อหา |
|---|---|---|
| `tuh-chatbot_chroma` | `/data/chroma` | ChromaDB (dense vector) |
| `tuh-chatbot_index_db` | `/app/index_db` | `bm25.pkl` — **ต้องมาจาก rebuild ครั้งเดียวกับ ChromaDB เสมอ** สำรอง/ย้ายคู่กัน |
| `tuh-chatbot_uploads` | `/app/uploads` | PDF ที่อัปโหลด, แบบฟอร์ม, cache สกัดข้อความ/OCR |
| `tuh-chatbot_model_cache` | `/cache` | โมเดล bge-m3 (~2 GB) และข้อมูล PyThaiNLP |

`docker compose down` ไม่ลบ volume — ลบเฉพาะเมื่อสั่ง `docker compose down -v` (**ข้อมูลหายหมด**)

## ติดตั้งครั้งแรก

1. มี `services/api/.env` ครบแล้ว (ค่าเดียวกับที่ใช้รันปกติ) — compose ทับ `CHROMA_DB_DIR` และ `TESSERACT_CMD` ด้วย path ใน container ให้เอง ไม่ต้องแก้ไฟล์
2. Build:
   ```bash
   docker compose build
   ```
3. ย้ายข้อมูลเดิมเข้า volume (ครั้งเดียว) — **ปิด backend ที่รันบน Windows ก่อน** กันคัดลอก ChromaDB ระหว่างกำลังเขียน:
   ```bash
   python infra/scripts/seed_volumes.py
   ```
   คัดลอก `uploads/`, `index_db/bm25.pkl`, ChromaDB จาก `CHROMA_DB_DIR` และโมเดล bge-m3 จาก HuggingFace cache
   ถ้าไม่อยากใช้ดัชนีเดิม ใช้ `--skip-index` แล้วกด rebuild ในหน้าแอดมิน หลังเปิดระบบ
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
| สำรองดัชนี | `docker run --rm -v tuh-chatbot_chroma:/c -v tuh-chatbot_index_db:/i -v ${PWD}:/out alpine tar czf /out/index-backup.tgz /c /i` |

## HTTPS และใบรับรอง

- ตั้งชื่อที่ผู้ใช้ใช้เปิดเว็บใน `.env` ที่ root ของ repo (ไม่อยู่ใน git — repo เป็น public):
  ```
  TLS_HOSTS=localhost, <ชื่อเครื่อง>, <ชื่อเครื่อง>.<domain>
  TLS_PRIMARY_HOST=<ชื่อเครื่อง>.<domain>
  ```
  แก้แล้วสั่ง `docker compose up -d --force-recreate proxy`
- **เปิดด้วย IP ตรงๆ (`https://172.30.x.x`) ไม่ได้** — เบราว์เซอร์ไม่ส่งชื่อเครื่อง (SNI) มากับ IP proxy จึงเลือกใบรับรองไม่ได้
  ลิงก์เดิมแบบ `http://<IP>:5173` จึงถูก redirect ไปที่ `TLS_PRIMARY_HOST` แทน
- frontend ใน Docker build ด้วย `VITE_API_URL=same-origin` = เรียก API ทาง `https://<host>/api` เดียวกับหน้าเว็บ (ไม่มี CORS)
- ใบรับรองตอนนี้ออกโดย **CA ภายในของ Caddy** (เก็บใน volume `tuh-chatbot_caddy_data`, หมดอายุ root ปี 2036)
  - เครื่องผู้ใช้ที่ยังไม่ได้ติดตั้ง CA จะขึ้นคำเตือน "การเชื่อมต่อไม่เป็นส่วนตัว" (กดดำเนินการต่อได้ เพราะยังไม่เปิด HSTS)
  - ให้ IT ติดตั้งใบ root เป็น Trusted Root ผ่าน GPO: `docker compose cp proxy:/data/caddy/pki/authorities/local/root.crt ./tuh-chatbot-root-ca.crt`
  - ⚠️ ใครได้ไฟล์ `root.key` ใน volume นี้ไป จะออกใบรับรองปลอมของเว็บไหนก็ได้ที่เครื่องในโรงพยาบาลเชื่อ — จำกัดสิทธิ์เข้าเครื่อง/volume
    ระยะยาวแนะนำใช้ใบรับรองจาก CA ของโรงพยาบาล: วางไฟล์ใบรับรองในอิมเมจ/volume แล้วเปลี่ยน `local_certs` เป็น `tls <cert> <key>` ใน Caddyfile (docker-compose.yml)
- เมื่อทุกเครื่องเชื่อใบรับรองแล้ว ค่อยเปิดบรรทัด `Strict-Transport-Security` ใน Caddyfile (เปิดก่อน = ผู้ใช้กดข้ามคำเตือนไม่ได้)
- port 80 ไม่ได้เปิด เพราะ Windows ใช้อยู่ (http.sys) — บน VM Linux เพิ่ม `"80:80"` ที่ service `proxy` แล้ว Caddy จะ redirect http → https ให้เอง
- backend เชื่อ `X-Forwarded-For` จาก proxy (`TRUST_PROXY_HEADERS=true`) — บน Docker Desktop ทุกเครื่องยังเห็นเป็น IP เดียวกัน (ข้อจำกัดของ Docker Desktop) บน VM Linux จะเห็น IP จริง

## Hardening (security audit 2026-10-30)

- security headers ใส่ที่ proxy ทุก response: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, ซ่อน `Server`
- CSP แยกตามเว็บ: แชทบอทอนุญาตเฉพาะตัวเอง + Google Fonts; แอดมินเพิ่ม `cdn.ckeditor.com` (ตัวแก้ไขประกาศ) และ `blob:` (เปิด PDF)
  — เพิ่ม script/ฟอนต์/รูปจากโดเมนใหม่ ต้องแก้ CSP ใน Caddyfile (docker-compose.yml) ด้วย ไม่งั้นเบราว์เซอร์บล็อก
- proxy จำกัด request ไป `/api` ไม่เกิน 60 MB (backend: เอกสาร 50 MB, แบบฟอร์ม 20 MB — `MAX_DOCUMENT_UPLOAD_MB`, `MAX_FORM_UPLOAD_MB`)
- ทุก container: `no-new-privileges`, ตัด Linux capability ที่ไม่ใช้, จำกัด memory (backend 5 GB), log หมุนเวียน 10 MB × 5
- network แยก: `web` (proxy, userweb, adminweb) / `api` (proxy, backend) — หน้าเว็บต่อ backend ตรงไม่ได้
- ลบไฟล์ค้างของเอกสารที่ลบไปแล้วใน volume uploads: `docker compose exec backend python -m scripts.purge_orphan_upload_files [--execute]`
- ⚠️ CKEditor 4.22.1 (เว็บแอดมิน) หมดระยะ support แบบฟรีแล้ว — เนื้อหาประกาศยังผ่าน sanitize ฝั่ง backend (nh3) แต่ควรวางแผนเปลี่ยนตัวแก้ไข

## เข้าจากเครื่องอื่นใน LAN

firewall ของเครื่องต้องเปิด port 443 (และ 5173/5174/8080 ถ้าอยากให้ลิงก์เดิม redirect ได้) — port 8000 ไม่ต้องเปิดแล้ว
แนะนำให้ผู้ใช้ bookmark `https://<ชื่อเครื่อง>.<domain>/` — IP ของเครื่องมาจาก DHCP เปลี่ยนได้ แต่ชื่อเครื่องไม่เปลี่ยน
dev server (5173/5174 + backend :8000 ตรง) ยังใช้ CORS ของ backend ตามเดิม: `localhost`, วง `172.30.x.x` และ `CORS_EXTRA_HOSTS` ใน `services/api/.env`

## หมายเหตุ

- ใช้ torch รุ่น CPU (เครื่องปัจจุบันไม่มี GPU) ถ้าย้ายไปเครื่องที่มี NVIDIA GPU ต้องเปลี่ยน index ของ torch ใน [services/api/Dockerfile](../services/api/Dockerfile) และเพิ่ม `gpus: all` ใน compose
- เวอร์ชันไลบรารีหลักถูกล็อกไว้ใน [services/api/constraints.txt](../services/api/constraints.txt) ให้ตรงกับเครื่อง dev — ChromaDB เปลี่ยนรูปแบบไฟล์ข้ามเวอร์ชัน อัปเกรดแล้วให้ rebuild ดัชนีใหม่
- Tesseract ใน container ใช้ข้อมูลภาษาไทยของ Debian (`tesseract-ocr-tha`) ไม่ใช่ `tessdata_best` แบบบน Windows — ใช้หาตำแหน่งบรรทัดเพื่อไฮไลท์เท่านั้น ไม่กระทบข้อความที่ใช้ตอบ (มาจาก Typhoon OCR)
- ตั้งแต่ 2026-10-29 ใช้ Docker เป็นหลัก เลิกใช้ XAMPP — proxy ฟัง port 8080 แล้วส่ง URL เดิม
  (`:8080/tuh_chatbot_ai/` → `https://<host>/`, `.../admin/` → `https://<host>/admin/`) จึงต้องปิด Apache ของ XAMPP ไว้
- Docker Desktop เปิดเองตอน login Windows และทุก service ตั้ง `restart: unless-stopped` — รีสตาร์ทเครื่องแล้วระบบกลับมาเอง
  (ถ้าสั่ง `docker compose stop` ไว้ ต้อง `docker compose start` เองอีกครั้ง)
- Docker Desktop อ่านไฟล์บนไดรฟ์ Z: (network share) แบบ bind mount ไม่ได้ — config ที่ต้องส่งเข้า container ให้ใส่ในอิมเมจหรือเขียน inline ใน compose
