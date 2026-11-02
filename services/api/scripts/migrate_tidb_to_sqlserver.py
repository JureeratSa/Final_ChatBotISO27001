"""
ย้ายข้อมูลทุกตารางจาก TiDB (MySQL) ไป Microsoft SQL Server — เตรียมไว้ ยังไม่ได้ใช้จริง
ขั้นตอนเต็มอยู่ที่ docs/SQLSERVER_MIGRATION.md

    cd services/api
    # 1) ดูจำนวนแถวที่จะย้าย (ไม่เขียนอะไร)
    python -m scripts.migrate_tidb_to_sqlserver --target "<SQL Server URL>"
    # 2) ย้ายจริง — SQL Server ต้องสร้างตารางด้วย sql/sqlserver/001_create_tables.sql ไว้แล้ว และยังว่างอยู่
    python -m scripts.migrate_tidb_to_sqlserver --target "<SQL Server URL>" --execute

ต้นทาง = DB ที่ services/api/.env ชี้อยู่ตอนนี้ (DB_ENGINE=mysql) ปลายทางรับเป็น URL ของ SQLAlchemy เช่น
    mssql+pyodbc://user:pass@host:1433/chatbot?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes
(ใส่ URL ผ่าน env MSSQL_TARGET_URL แทน --target ได้ — ไม่ให้รหัสผ่านค้างใน history ของ shell)

- ย้ายตามลำดับ foreign key (ตารางแม่ก่อน) ทั้งหมดใน transaction เดียว — ผิดพลาดตรงไหนย้อนกลับทั้งหมด
- ตารางที่ id เป็น IDENTITY เปิด IDENTITY_INSERT ชั่วคราว เพื่อคง id เดิม (foreign key ยังชี้ถูก)
- ปลายทางต้องว่าง — มีข้อมูลอยู่แล้วจะหยุดทันที ไม่เขียนทับ
- จบแล้วเทียบจำนวนแถวทุกตารางระหว่างต้นทาง/ปลายทาง
"""
import argparse
import os
import sys
from datetime import datetime, timezone

from sqlalchemy import create_engine, func, select, text

from app.core import mssql_types  # noqa: F401
from app.core.config import settings
from app.core.database import Base
from app.models import models  # noqa: F401

BATCH = 500


def _utc_aware(row) -> dict:
    """TiDB คืนเวลาแบบไม่มี timezone (เป็น UTC) — ติด UTC ให้ ไม่งั้นรันบนเครื่อง Windows แล้วถูกตีความเป็นเวลาไทย"""
    return {k: v.replace(tzinfo=timezone.utc) if isinstance(v, datetime) and v.tzinfo is None else v
            for k, v in row.items()}


def _identity_column(table):
    return next((c for c in table.primary_key.columns if c.autoincrement is True), None)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", default=os.getenv("MSSQL_TARGET_URL"), help="SQLAlchemy URL ของ SQL Server")
    parser.add_argument("--execute", action="store_true", help="ย้ายจริง (ไม่ใส่ = นับแถวอย่างเดียว)")
    args = parser.parse_args()
    if not args.target or not args.target.startswith("mssql"):
        sys.exit("ต้องระบุ --target (หรือ MSSQL_TARGET_URL) เป็น URL แบบ mssql+pyodbc://...")
    if settings.DB_ENGINE != "mysql":
        sys.exit("ต้นทางต้องเป็น TiDB — ตั้ง DB_ENGINE=mysql ใน services/api/.env ระหว่างย้ายข้อมูล")

    tables = Base.metadata.sorted_tables
    source = create_engine(settings.DATABASE_URL_SYNC)  # แบบเดียวกับ rebuild_service ที่ใช้กับ TiDB อยู่
    # use_setinputsizes=False: ตารางที่มีแถวเดียว (settings, forms) ถูก insert ทีละแถว — ไม่ปิด = ภาษาไทยกลายเป็น ????
    target = create_engine(args.target, fast_executemany=True, use_setinputsizes=False)

    with source.connect() as src:
        counts = {t.name: src.execute(select(func.count()).select_from(t)).scalar() for t in tables}
    print("จำนวนแถวต้นทาง (TiDB):")
    for name, n in counts.items():
        print(f"  {name:<20} {n:>8}")

    with target.connect() as dst:
        existing = {t.name: dst.execute(select(func.count()).select_from(t)).scalar() for t in tables}
    if any(existing.values()):
        sys.exit(f"ปลายทางมีข้อมูลอยู่แล้ว {existing} — หยุด (สคริปต์นี้ใช้กับฐานข้อมูลว่างเท่านั้น)")

    if not args.execute:
        print("\nยังไม่ได้ย้ายข้อมูล (dry-run) — ใส่ --execute เพื่อย้ายจริง")
        return

    with source.connect() as src, target.begin() as dst:
        for table in tables:
            identity = _identity_column(table)
            if identity is not None:
                dst.execute(text(f"SET IDENTITY_INSERT {table.name} ON"))
            rows = src.execute(select(table)).mappings()
            moved = 0
            while True:
                chunk = rows.fetchmany(BATCH)
                if not chunk:
                    break
                dst.execute(table.insert(), [_utc_aware(r) for r in chunk])
                moved += len(chunk)
            if identity is not None:
                dst.execute(text(f"SET IDENTITY_INSERT {table.name} OFF"))
            print(f"  ย้าย {table.name}: {moved} แถว")

    with target.connect() as dst:
        after = {t.name: dst.execute(select(func.count()).select_from(t)).scalar() for t in tables}
    diff = {k: (counts[k], after[k]) for k in counts if counts[k] != after[k]}
    print("\nจำนวนแถวตรงกันทุกตาราง ✅" if not diff else f"\n❌ จำนวนแถวไม่ตรง (ต้นทาง, ปลายทาง): {diff}")
    source.dispose()
    target.dispose()


if __name__ == "__main__":
    main()
