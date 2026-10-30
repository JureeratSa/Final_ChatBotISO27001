"""
สร้างไฟล์ SQL สร้างตารางบน Microsoft SQL Server จาก SQLAlchemy models (ตัวเดียวกับที่ใช้กับ TiDB)
คอลัมน์/ชนิด/ความยาว/index/foreign key ตรงกับ TiDB ปัจจุบัน (Alembic head) — ข้อความทุกช่องเป็น NVARCHAR

รัน (ไม่ต้องต่อฐานข้อมูล ไม่ต้องติดตั้ง ODBC driver):
    cd Backend && python -m scripts.generate_sqlserver_schema
ผลลัพธ์: Backend/sql/sqlserver/001_create_tables.sql  (แก้ models แล้วรันใหม่ทุกครั้ง)

ไฟล์ที่ได้สร้างตาราง alembic_version พร้อม revision ล่าสุดด้วย — หลังรันบน SQL Server แล้ว
`alembic upgrade head` ครั้งต่อไปจะเริ่มจาก migration ใหม่ ไม่รันประวัติ migration เดิมของ MySQL ซ้ำ
"""
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.dialects import mssql
from sqlalchemy.schema import CreateIndex, CreateTable

from app.core import mssql_types  # noqa: F401  — String/Text → NVARCHAR
from app.core.database import Base
from app.models import models  # noqa: F401  — ลงทะเบียนทุกตารางเข้า Base.metadata

BACKEND_DIR = Path(__file__).resolve().parents[1]
OUTPUT = BACKEND_DIR / "sql" / "sqlserver" / "001_create_tables.sql"


def alembic_head() -> str:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return ScriptDirectory.from_config(cfg).get_current_head()


def build_sql() -> str:
    dialect = mssql.dialect()
    head = alembic_head()
    parts = [
        "-- TUH Chatbot AI — ตารางบน Microsoft SQL Server",
        "-- สร้างอัตโนมัติจาก Backend/app/models/models.py ด้วย scripts/generate_sqlserver_schema.py — อย่าแก้มือ",
        f"-- ตรงกับ Alembic revision {head} (schema เดียวกับ TiDB)",
        "-- รันบนฐานข้อมูลว่าง: sqlcmd -S <host> -d <db> -U <user> -i 001_create_tables.sql",
        "SET XACT_ABORT ON;",
        "BEGIN TRANSACTION;",
        "",
    ]
    for table in Base.metadata.sorted_tables:          # เรียงตาม foreign key (ตารางแม่ก่อน)
        parts.append(str(CreateTable(table).compile(dialect=dialect)).strip() + ";")
        for index in sorted(table.indexes, key=lambda i: i.name or ""):
            parts.append(str(CreateIndex(index).compile(dialect=dialect)).strip() + ";")
        parts.append("")
    parts += [
        "CREATE TABLE alembic_version (",
        "\tversion_num VARCHAR(32) NOT NULL,",
        "\tCONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)",
        ");",
        f"INSERT INTO alembic_version (version_num) VALUES ('{head}');",
        "",
        "COMMIT;",
        "",
    ]
    return "\n".join(parts)


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(build_sql(), encoding="utf-8")
    print(f"เขียน {OUTPUT.relative_to(BACKEND_DIR)} แล้ว ({len(Base.metadata.sorted_tables)} ตาราง)")


if __name__ == "__main__":
    main()
