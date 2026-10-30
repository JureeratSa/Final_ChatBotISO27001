"""
เตรียมย้ายไป Microsoft SQL Server (ยังใช้ TiDB) — ตรวจโดยไม่ต้องมี SQL Server จริง
- ค่าเริ่มต้นยังเป็น MySQL/TiDB เหมือนเดิม
- DB_ENGINE=mssql สร้าง URL ของ pyodbc/aioodbc ถูกต้อง (escape รหัสผ่าน)
- ทุกตารางคอมไพล์เป็น DDL ของ SQL Server ได้ และข้อความเป็น NVARCHAR (เก็บภาษาไทยได้)
- LIKE ของการกรองประวัติตามแผนก escape [ (SQL Server ถือเป็นชุดตัวอักษร) โดยยังค้นเจอบน SQLite/MySQL
"""
import pytest
from sqlalchemy.dialects import mssql
from sqlalchemy.engine import make_url
from sqlalchemy.schema import CreateTable

from app.core.config import Settings
from app.core.database import Base
from app.models import models  # noqa: F401

pytestmark = pytest.mark.asyncio

BASE_ENV = dict(DB_HOST="db.example", DB_USER="u", DB_PASSWORD="p@ss:w/rd%1", JWT_SECRET_KEY="x" * 40)


async def test_default_engine_is_still_mysql():
    s = Settings(**BASE_ENV)
    assert s.DB_ENGINE == "mysql"
    assert s.DATABASE_URL.startswith("mysql+aiomysql://")
    assert s.DATABASE_URL_SYNC.startswith("mysql+pymysql://")


async def test_mssql_urls():
    s = Settings(**BASE_ENV, DB_ENGINE="mssql", DB_PORT=1433)
    for url_str, driver in ((s.DATABASE_URL, "mssql+aioodbc"), (s.DATABASE_URL_SYNC, "mssql+pyodbc")):
        url = make_url(url_str)
        assert url.drivername == driver
        assert url.password == "p@ss:w/rd%1"          # อักขระพิเศษในรหัสผ่านถูก escape แล้วอ่านกลับได้ตรง
        assert (url.host, url.port, url.database) == ("db.example", 1433, "chatbot")
        assert url.query["driver"] == "ODBC Driver 18 for SQL Server"
        assert url.query["Encrypt"] == "yes" and url.query["TrustServerCertificate"] == "no"


async def test_all_tables_compile_for_sql_server_with_nvarchar():
    dialect = mssql.dialect()
    for table in Base.metadata.sorted_tables:
        ddl = str(CreateTable(table).compile(dialect=dialect))
        assert "VARCHAR(" not in ddl.replace("NVARCHAR(", ""), f"{table.name} มีคอลัมน์ VARCHAR (เก็บภาษาไทยไม่ได้)"
    users = str(CreateTable(Base.metadata.tables["users"]).compile(dialect=dialect))
    assert "IDENTITY" in users and "BIT" in users


async def test_generated_schema_file_is_up_to_date():
    from scripts.generate_sqlserver_schema import OUTPUT, build_sql
    assert OUTPUT.read_text(encoding="utf-8") == build_sql(), \
        "models เปลี่ยนแล้ว — รัน `python -m scripts.generate_sqlserver_schema` ใหม่"


async def test_history_like_escapes_bracket_and_still_matches(client, db_session, admin_user):
    from app.models.models import ChatHistory, Document
    from app.services.department_scope import _like_json_item
    assert "\\[" in _like_json_item("ฟอร์ม[2568].pdf")

    db_session.add(Document(filename="ฟอร์ม[2568].pdf", display_name="f", status="Active", department="งานA"))
    db_session.add(ChatHistory(id="h1", query="q", answer="a", cited_docs='["ฟอร์ม[2568].pdf"]'))
    await db_session.commit()
    from tests.conftest import auth_header
    resp = await client.get("/api/admin/history", params={"department": "งานA"}, headers=auth_header(admin_user.username))
    assert [h["id"] for h in resp.json()] == ["h1"]
