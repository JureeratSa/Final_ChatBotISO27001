"""
ชนิดคอลัมน์บน SQL Server — String/Text ต้องเป็น NVARCHAR ไม่งั้นภาษาไทยกลายเป็น ????
import ไฟล์นี้ครั้งเดียว (database.py ทำให้แล้ว) มีผลกับ create_all, Alembic และ scripts/generate_sqlserver_schema.py
บน MySQL/TiDB ไม่มีผลอะไร
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
