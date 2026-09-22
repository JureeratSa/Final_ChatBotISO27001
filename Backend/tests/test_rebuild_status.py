"""
Integration tests: POST /api/admin/rebuild, GET /api/admin/rebuild/status

Regression test สำหรับปัญหา _rebuild_status เดิมเป็น module-level dict ในหน่วยความจำของ
process เดียว — ถ้ารัน uvicorn หลาย worker แต่ละ worker เห็นสถานะคนละค่ากัน ตอนนี้ย้ายไปเก็บ
ในตาราง settings (คอลัมน์ rebuild_status/rebuild_message) แทน ยืนยันว่าอ่าน/เขียนผ่าน DB จริง
"""
import pytest
from sqlalchemy import select

from tests.conftest import auth_header
import app.routers.admin_rebuild as admin_module
from app.models.models import SystemSettings

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _skip_real_background_rebuild(monkeypatch):
    """ตัด background task จริงออก (import Admin.rebuild_db + ต่อ DB จริงผ่าน pymysql) —
    หนักเกินไปและต้องพึ่ง network สำหรับ unit test"""
    monkeypatch.setattr(admin_module, "_trigger_rebuild_background", lambda: None)


async def test_rebuild_status_idle_when_no_settings_row(client, admin_user):
    resp = await client.get("/api/admin/rebuild/status", headers=auth_header(admin_user.username))
    assert resp.status_code == 200
    assert resp.json()["status"] == "idle"


async def test_trigger_rebuild_persists_processing_status_to_db(client, admin_user, db_session):
    resp = await client.post("/api/admin/rebuild", headers=auth_header(admin_user.username))
    assert resp.status_code == 200
    assert resp.json()["status"] == "processing"

    result = await db_session.execute(select(SystemSettings))
    cfg = result.scalar_one_or_none()
    assert cfg is not None
    assert cfg.rebuild_status == "processing"


async def test_rebuild_status_reflects_db_state_across_requests(client, admin_user, db_session):
    """
    จำลองว่ามี worker อื่นเขียนสถานะ "success" ลง DB ไปแล้ว (เช่น background task ใน worker
    อื่นเขียนเสร็จ) request สถานะจาก worker นี้ (ที่ใช้ client/db_session คนละตัว) ต้องเห็น
    ค่าล่าสุดจาก DB เสมอ ไม่ใช่ค่าที่ค้างอยู่ใน memory ของตัวเอง
    """
    db_session.add(SystemSettings(id="config", rebuild_status="success", rebuild_message="เสร็จแล้ว", last_build_duration=12.5))
    await db_session.commit()

    resp = await client.get("/api/admin/rebuild/status", headers=auth_header(admin_user.username))
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert body["duration"] == 12.5


async def test_trigger_rebuild_returns_processing_message_when_already_running(client, admin_user, db_session):
    db_session.add(SystemSettings(id="config", rebuild_status="processing"))
    await db_session.commit()

    resp = await client.post("/api/admin/rebuild", headers=auth_header(admin_user.username))
    assert resp.status_code == 200
    assert "กำลังประมวลผลอยู่แล้ว" in resp.json()["message"]


async def test_rebuild_endpoints_require_auth(client):
    resp1 = await client.post("/api/admin/rebuild")
    resp2 = await client.get("/api/admin/rebuild/status")
    assert resp1.status_code in (401, 403)
    assert resp2.status_code in (401, 403)
