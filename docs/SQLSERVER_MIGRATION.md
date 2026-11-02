# ฐานข้อมูล Microsoft SQL Server

สถานะ: **ใช้งานจริงตั้งแต่ 2026-11-02** (`DB_ENGINE=mssql`) — ย้ายข้อมูลมาจาก TiDB Cloud ครบทุกตาราง
TiDB ยังเก็บข้อมูล ณ วันที่ย้ายไว้ (ใช้ย้อนกลับได้ ดูท้ายไฟล์)

## ⚠️ ฐานข้อมูลใช้ร่วมกับระบบอื่น

ฐานข้อมูลบน SQL Server มีตารางของหน่วยงาน/ระบบอื่นอยู่ด้วย แชทบอทเป็นเจ้าของเฉพาะ **10 ตาราง**:
`users`, `documents`, `history`, `feedback`, `unanswered`, `settings`, `forms`, `announcements`, `admin_audit_logs`, `alembic_version`

- **ห้ามอ่าน/แก้/ลบตารางอื่นเด็ดขาด** — ทุกสคริปต์และคำสั่ง SQL ต้องระบุชื่อตารางของเราตรงๆ
- `alembic/env.py` มี `include_object` กันไม่ให้ `alembic revision --autogenerate` เสนอ `drop_table` ตารางที่ไม่อยู่ใน models — ห้ามเอาออก และยังต้องตรวจไฟล์ migration ทุกครั้งก่อน `alembic upgrade head`
- user ฐานข้อมูลของแชทบอทควรมีสิทธิ์เฉพาะตารางของตัวเอง (ขอ IT จำกัดสิทธิ์ หรือแยกฐานข้อมูล)

## สิ่งที่ต่างจาก TiDB (แก้ไว้แล้วในโค้ด)

| เรื่อง | ถ้าไม่แก้จะเกิดอะไร | แก้ที่ |
|---|---|---|
| ข้อความต้องเป็น `NVARCHAR` | ภาษาไทยกลายเป็น `????` | [app/core/mssql_types.py](../services/api/app/core/mssql_types.py) |
| ปิด `setinputsizes` ของ pyodbc | บันทึกทีละแถวแล้วข้อความถูกส่งเป็น `VARCHAR` → ภาษาไทยกลายเป็น `????` (collation ของฐานข้อมูลไม่ใช่ภาษาไทย) | `settings.DB_ENGINE_OPTIONS` ใน [app/core/config.py](../services/api/app/core/config.py) — ใช้กับ `create_engine` ทุกที่ |
| `func.now()` → `SYSDATETIMEOFFSET()` | `CURRENT_TIMESTAMP` เป็นนาฬิกาเครื่องเซิร์ฟเวอร์ (เวลาไทย) แต่ถูกเก็บเป็น `+00:00` → เวลาคลาด 7 ชั่วโมง | [app/core/mssql_types.py](../services/api/app/core/mssql_types.py) |
| LIKE ต้อง escape `[` | ค้นประวัติตามแผนกผิด | [app/services/department_scope.py](../services/api/app/services/department_scope.py) |

เวลาทุกช่องเก็บเป็น `DATETIMEOFFSET` แบบ UTC — แปลงเป็นเวลาไทยตอนแสดงผล (`app/utils/timeutil.py`)

## ไฟล์ที่เกี่ยวข้อง

| ไฟล์ | หน้าที่ |
|---|---|
| [services/api/app/core/config.py](../services/api/app/core/config.py) | `DB_ENGINE=mssql` → `mssql+aioodbc` (แอป) / `mssql+pyodbc` (Alembic, สคริปต์) พร้อม `DB_ODBC_DRIVER`, `DB_ENCRYPT`, `DB_TRUST_SERVER_CERTIFICATE` |
| [services/api/sql/sqlserver/001_create_tables.sql](../services/api/sql/sqlserver/001_create_tables.sql) | สร้างตารางทั้งหมดบนฐานข้อมูลใหม่ + `alembic_version` (สร้างจาก models อัตโนมัติ) |
| [services/api/scripts/generate_sqlserver_schema.py](../services/api/scripts/generate_sqlserver_schema.py) | สร้างไฟล์ SQL ข้างบนใหม่จาก models |
| [services/api/scripts/migrate_tidb_to_sqlserver.py](../services/api/scripts/migrate_tidb_to_sqlserver.py) | คัดลอกข้อมูลจาก TiDB → SQL Server คง id เดิม และเทียบจำนวนแถว (ใช้กับปลายทางที่ว่างเท่านั้น) |
| [services/api/Dockerfile](../services/api/Dockerfile) + docker-compose.yml | build backend พร้อม Microsoft ODBC Driver 18 (`WITH_MSSQL: "true"`) |

## ค่าใน `services/api/.env`
```
DB_ENGINE=mssql
DB_HOST=<host>
DB_PORT=1433
DB_USER=<user>
DB_PASSWORD=<pass>
DB_NAME=<db>
DB_ODBC_DRIVER=ODBC Driver 18 for SQL Server
DB_ENCRYPT=true
DB_TRUST_SERVER_CERTIFICATE=true   # เซิร์ฟเวอร์ปัจจุบันใช้ใบรับรองที่ออกเอง — ถ้าได้ไฟล์ CA จาก IT ให้ติดตั้ง CA แล้วตั้งเป็น false
```
(ค่าจริงอยู่ใน `.env` บนเครื่องเซิร์ฟเวอร์เท่านั้น — repo นี้เป็น public ห้ามใส่ชื่อเครื่อง/IP/รหัสผ่านลงไฟล์ที่ track)

## แก้ตาราง (Alembic)
```bash
docker compose run --rm backend alembic revision --autogenerate -m "อธิบายสั้นๆ"
# ตรวจไฟล์ใน alembic/versions/ — ลบบรรทัด modify_comment ทิ้งได้ (SQL Server ยังไม่มี comment ของคอลัมน์)
docker compose run --rm backend alembic upgrade head
```
แล้วรัน `scripts/generate_sqlserver_schema.py` ใหม่ ให้ไฟล์ SQL ตรงกับ models

## ทำซ้ำการย้าย (เช่น ย้ายไปเซิร์ฟเวอร์ใหม่)
1. สร้างตารางบนฐานข้อมูลว่าง: `sqlcmd -S <host>,1433 -d <db> -U <user> -i services/api/sql/sqlserver/001_create_tables.sql`
2. หยุด backend (`docker compose stop backend`) กันข้อมูลใหม่หาย
3. ย้ายข้อมูล — ต้นทางตั้ง `DB_ENGINE=mysql` + ค่า TiDB ผ่าน env var, ปลายทางผ่าน `MSSQL_TARGET_URL`:
   ```bash
   python -m scripts.migrate_tidb_to_sqlserver               # ดูจำนวนแถว (ไม่เขียน)
   python -m scripts.migrate_tidb_to_sqlserver --execute     # ย้ายจริง + เทียบจำนวนแถว
   ```
4. ตั้ง `.env` เป็น `DB_ENGINE=mssql` → `docker compose up -d backend` → ตรวจล็อกอินแอดมิน, หน้าประวัติ, ถามแชทบอท 1–2 คำถาม และดูว่าภาษาไทย/เวลาที่บันทึกใหม่ถูกต้อง

## ย้อนกลับไป TiDB
ตั้ง `DB_ENGINE=mysql` + ค่า TiDB เดิมใน `services/api/.env` แล้ว `docker compose up -d backend`
ข้อมูลที่เกิดบน SQL Server หลังวันที่ย้ายจะไม่อยู่ใน TiDB
เมื่อมั่นใจว่าไม่ย้อนกลับแล้ว ควรลบข้อมูล/cluster บน TiDB Cloud (รหัสผ่าน TiDB เคยหลุดใน git — ดู security audit)
