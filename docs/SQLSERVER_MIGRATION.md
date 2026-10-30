# ย้ายฐานข้อมูลจาก TiDB ไป Microsoft SQL Server

สถานะ: **เตรียมไว้แล้ว ยังไม่ได้ใช้** — ระบบยังต่อ TiDB (`DB_ENGINE=mysql` ค่าเริ่มต้น) จนกว่าจะได้บัญชี SQL Server

## สิ่งที่เตรียมไว้

| ไฟล์ | หน้าที่ |
|---|---|
| [services/api/app/core/config.py](../services/api/app/core/config.py) | `DB_ENGINE=mssql` → ใช้ `mssql+aioodbc` (แอป) / `mssql+pyodbc` (Alembic, สคริปต์) พร้อม `DB_ODBC_DRIVER`, `DB_ENCRYPT`, `DB_TRUST_SERVER_CERTIFICATE` |
| [services/api/app/core/mssql_types.py](../services/api/app/core/mssql_types.py) | ข้อความทุกคอลัมน์เป็น `NVARCHAR` บน SQL Server (ไม่งั้นภาษาไทยกลายเป็น `????`) |
| [services/api/sql/sqlserver/001_create_tables.sql](../services/api/sql/sqlserver/001_create_tables.sql) | สร้างตารางครบ 9 ตาราง + index + foreign key + `alembic_version` — คอลัมน์/ความยาวตรงกับ TiDB (ตรวจเทียบกับ TiDB จริงแล้ว 2026-10-30) |
| [services/api/scripts/generate_sqlserver_schema.py](../services/api/scripts/generate_sqlserver_schema.py) | สร้างไฟล์ SQL ข้างบนใหม่จาก models (แก้ models แล้วต้องรันใหม่ทุกครั้ง) |
| [services/api/scripts/migrate_tidb_to_sqlserver.py](../services/api/scripts/migrate_tidb_to_sqlserver.py) | คัดลอกข้อมูลทุกตารางจาก TiDB → SQL Server คง id เดิม และเทียบจำนวนแถว |
| [services/api/requirements-mssql.txt](../services/api/requirements-mssql.txt) | `pyodbc`, `aioodbc` |
| [services/api/Dockerfile](../services/api/Dockerfile) | `--build-arg WITH_MSSQL=true` ติดตั้ง Microsoft ODBC Driver 18 (ทดสอบ build แล้ว driver โหลดได้) |

ไม่ต้องเขียน query ใหม่ — โค้ดใช้ SQLAlchemy ORM ทั้งหมด (ไม่มี raw SQL / ฟังก์ชันเฉพาะ MySQL)
แก้เพิ่มแค่ LIKE ของการกรองประวัติตามแผนกให้ escape `[` (SQL Server ถือเป็นชุดตัวอักษร)

## สิ่งที่ต้องขอจากผู้ดูแล SQL Server
- host / port (ปกติ 1433), ชื่อฐานข้อมูล (ว่าง), user / password ที่มีสิทธิ์สร้างตาราง (ระหว่างติดตั้ง) และอ่าน/เขียน (ใช้งานปกติ)
- SQL Server 2017 ขึ้นไป (ใช้ `DATETIMEOFFSET`, `NVARCHAR(max)`)
- ใบรับรอง TLS ของเซิร์ฟเวอร์ออกโดย CA ที่เครื่องเชื่อหรือไม่ (ถ้าไม่ ต้องตั้ง `DB_TRUST_SERVER_CERTIFICATE=true`)
- firewall ให้เครื่อง/VM ที่รัน backend ต่อเข้า port ของ SQL Server ได้

## ขั้นตอนตอนได้ key แล้ว

1. **สร้างตาราง** บนฐานข้อมูลว่าง:
   ```bash
   sqlcmd -S <host>,1433 -d <db> -U <user> -i services/api/sql/sqlserver/001_create_tables.sql
   ```
2. **build backend ที่มี ODBC driver** — ตั้ง `WITH_MSSQL: "true"` ใต้ `build.args` ของ service `backend` ใน docker-compose.yml แล้ว `docker compose build backend`
3. **ย้ายข้อมูล** (ระหว่างนี้ `services/api/.env` ยังชี้ TiDB) — หยุดใช้งานระบบชั่วคราวกันข้อมูลใหม่หาย:
   ```bash
   docker compose stop proxy
   docker compose run --rm -e MSSQL_TARGET_URL="mssql+pyodbc://<user>:<pass>@<host>:1433/<db>?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes" \
       backend python -m scripts.migrate_tidb_to_sqlserver            # ดูจำนวนแถว
   docker compose run --rm -e MSSQL_TARGET_URL="..." backend python -m scripts.migrate_tidb_to_sqlserver --execute
   ```
4. **สลับไป SQL Server** ใน `services/api/.env`:
   ```
   DB_ENGINE=mssql
   DB_HOST=<host>
   DB_PORT=1433
   DB_USER=<user>
   DB_PASSWORD=<pass>
   DB_NAME=<db>
   # DB_TRUST_SERVER_CERTIFICATE=true   (เฉพาะถ้าใบรับรองของ SQL Server ไม่ได้ออกโดย CA ที่เชื่อถือ)
   ```
   แล้ว `docker compose up -d backend proxy` → ตรวจ login แอดมิน, หน้าประวัติ, ถามแชทบอท 1–2 คำถาม
5. **ตรวจ Alembic**: `docker compose run --rm backend alembic current` ต้องได้ revision เดียวกับในไฟล์ SQL
6. **ปิด TiDB**: เมื่อใช้ SQL Server ได้แน่นอนแล้ว ลบข้อมูล/cluster บน TiDB Cloud (รหัสผ่าน TiDB เคยหลุดใน git — ดู security audit)

ย้อนกลับ: ตั้ง `DB_ENGINE=mysql` + ค่า TiDB เดิมใน `services/api/.env` แล้ว `docker compose up -d backend` (ข้อมูลที่เกิดบน SQL Server หลังสลับจะไม่ย้อนกลับไป TiDB)

## หลังย้ายแล้ว
- migration ใหม่ (`alembic revision --autogenerate`) สร้างจาก SQL Server ได้ตามปกติ — ตรวจไฟล์ก่อน upgrade ทุกครั้ง
- migration เดิมในโฟลเดอร์ `alembic/versions` เขียนสำหรับ MySQL ไม่ต้องรันบน SQL Server (ไฟล์ SQL ตั้ง revision ล่าสุดให้แล้ว)
