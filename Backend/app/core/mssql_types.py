"""
TUH Chatbot AI — ชนิดคอลัมน์บน SQL Server
models ใช้ String / Text (บน MySQL/TiDB เก็บเป็น utf8mb4 อยู่แล้ว) แต่บน SQL Server ชนิดเดียวกันจะเป็น
VARCHAR ซึ่งเก็บภาษาไทยไม่ได้ถ้า collation ของฐานข้อมูลไม่ใช่ UTF-8 (ตัวอักษรกลายเป็น ????)
บังคับให้ทั้ง create_all, Alembic และสคริปต์สร้างตาราง (scripts/generate_sqlserver_schema.py) ใช้ NVARCHAR
มีผลเฉพาะ dialect "mssql" — MySQL/TiDB และ SQLite (pytest) ไม่เปลี่ยน
"""
from sqlalchemy import String, Text
from sqlalchemy.ext.compiler import compiles


@compiles(String, "mssql")
def _string_as_nvarchar(type_, compiler, **kw):
    # NVARCHAR(n) รับได้ถึง 4000 — ยาวกว่านั้นต้องเป็น NVARCHAR(max)
    if type_.length and type_.length <= 4000:
        return f"NVARCHAR({type_.length})"
    return "NVARCHAR(max)"


# Text เป็น subclass ของ String — ต้องลงทะเบียนแยก ไม่งั้นได้ NVARCHAR(max) จากด้านบนอยู่แล้วแต่ให้ชัดเจน
@compiles(Text, "mssql")
def _text_as_nvarchar_max(type_, compiler, **kw):
    return "NVARCHAR(max)"
