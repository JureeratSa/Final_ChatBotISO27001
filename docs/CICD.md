# CI/CD

- **CI** (GitHub Actions, [.github/workflows/ci.yml](../.github/workflows/ci.yml)): ตรวจโค้ดอัตโนมัติทุกครั้งที่ push ทุก branch และทุก PR เข้า `main`
- **CD** ([infra/scripts/deploy.py](../infra/scripts/deploy.py)): deploy ขึ้นเครื่องเซิร์ฟเวอร์ด้วยคำสั่งเดียว รันบนเครื่องเซิร์ฟเวอร์เอง
  เพราะเซิร์ฟเวอร์และ SQL Server อยู่ในเครือข่ายโรงพยาบาล GitHub ต่อเข้ามาไม่ได้
  และ repo เป็น public จึงไม่ติดตั้ง self-hosted runner (คนนอกจะส่งโค้ดมารันบนเครื่องในโรงพยาบาลผ่าน PR ได้)

## CI ตรวจอะไรบ้าง

| Job | ตรวจ | ล้มเมื่อ |
|---|---|---|
| Backend | ruff (เฉพาะข้อผิดพลาดจริง: ตัวแปรไม่ได้ประกาศ, import ไม่ได้ใช้, syntax) | โค้ด Python มีข้อผิดพลาด |
| | `infra/scripts/check_migrations.py` | migration แตะตารางที่ไม่ใช่ของแชทบอท (ฐานข้อมูลใช้ร่วมกับระบบอื่น) |
| | build image แบบ production (`WITH_MSSQL=true`) + เปิดแอปใน image | build ไม่ผ่าน / แอปเปิดไม่ขึ้น |
| | pip-audit | library Python มีช่องโหว่ใหม่ (ตัวที่ยกเว้นไว้เขียนเหตุผลใน ci.yml) |
| Web × 2 | `npm ci` + `npm run build` + `npm audit --omit=dev --audit-level=high` | build ไม่ผ่าน / ช่องโหว่ระดับ high ขึ้นไป |
| Secret scan | gitleaks เฉพาะ commit ที่เพิ่ง push | มีรหัสผ่าน/API key ติดเข้า git |

ไม่มี test ที่ต่อฐานข้อมูลจริง — ตรวจระบบจริงหลัง deploy แทน (deploy.py รอ healthcheck ทุก container)

ดูผล: แท็บ **Actions** ของ repo บน GitHub (หรือเครื่องหมาย ✅/❌ ข้าง commit)
รันตัวตรวจบางตัวในเครื่องก่อน push ได้:
```bash
python infra/scripts/check_migrations.py
python -m ruff check --select F,E9 services/api/app services/api/alembic services/api/scripts infra/scripts
```

### ตั้งค่าบน GitHub (ทำครั้งเดียว ผ่านหน้าเว็บ)
Settings → Branches → Add branch ruleset (หรือ branch protection rule) ของ `main`:
- Require a pull request before merging
- Require status checks to pass → เลือก `Backend (services/api)`, `Web (chat-web)`, `Web (admin-web)`, `Secret scan (gitleaks)`

## CD: deploy ขึ้นเครื่องเซิร์ฟเวอร์

บนเครื่องเซิร์ฟเวอร์ ที่โฟลเดอร์ repo (branch `main` ที่ผูกกับ GitHub แล้ว):
```bash
python infra/scripts/deploy.py --check    # ซ้อม: ดึงโค้ด + ตรวจ + build แต่ไม่สลับระบบที่รันอยู่
python infra/scripts/deploy.py            # deploy จริง
```

ขั้นตอนที่สคริปต์ทำ (ล้มขั้นไหน หยุดทันที — ก่อนขั้น "สลับ" ระบบที่รันอยู่ไม่ถูกแตะเลย):
1. โฟลเดอร์ต้องไม่มีไฟล์ที่ track แล้วถูกแก้ค้าง
2. `git pull --ff-only` (ไม่ต้องการ: `--no-pull`)
3. ตรวจ migration แตะเฉพาะตารางของแชทบอท
4. ติดป้าย image ที่รันอยู่เป็น `:rollback` แล้ว `docker compose build` (ระบบเดิมยังให้บริการระหว่าง build)
5. ฐานข้อมูลต้องอยู่ที่ migration ล่าสุดแล้ว (`alembic current` — อ่านอย่างเดียว)
6. `docker compose up -d` แล้วรอทุก container healthy + `/api/health` ตอบ 200 (สูงสุด 6 นาที)
7. ไม่ผ่าน → สลับกลับไป image `:rollback` ให้อัตโนมัติ แล้วแจ้งให้ดู log

ประวัติการ deploy บันทึกต่อท้ายไฟล์ `~/tuh-deploy-history.log` (เวลา, commit, ผล) — ใช้เป็นหลักฐานการเปลี่ยนแปลงระบบ

### มี migration ใหม่
สคริปต์**ไม่รัน** `alembic upgrade head` ให้เอง (ฐานข้อมูลใช้ร่วมกับระบบอื่น ต้องมีคนตรวจก่อน) — จะหยุดที่ขั้น 5 พร้อมบอกวิธี:
1. อ่านไฟล์ใหม่ใน `services/api/alembic/versions/` ว่าแตะเฉพาะตารางของแชทบอท
2. `docker compose run --rm backend alembic upgrade head`
3. `python infra/scripts/deploy.py` ใหม่

migration ที่ "เพิ่ม" คอลัมน์/ตารางไม่ทำให้โค้ดเดิมพัง — ถ้า deploy แล้วย้อนกลับ ระบบเดิมยังใช้ฐานข้อมูลได้
ถ้าเป็นการลบ/เปลี่ยนชื่อคอลัมน์ ให้แยกเป็น 2 รอบ (รอบแรกเลิกใช้คอลัมน์ในโค้ด, รอบถัดไปค่อยลบ)

### ย้อนกลับเอง (ถ้าพบปัญหาหลัง deploy สำเร็จไปแล้ว)
```bash
docker image tag tuh-chatbot-backend:rollback tuh-chatbot-backend:latest   # ทำกับ userweb / adminweb ด้วยถ้าต้องการ
docker compose up -d --no-build
```
`:rollback` คือ image ก่อน deploy ครั้งล่าสุดเท่านั้น
