"""
Tests สำหรับ flow ปิดรายการคำถามที่บอทตอบไม่ได้ (PUT /api/admin/unanswered/{id})
  - แก้ไข: บันทึกวิธีแก้ (resolution_type) + ผู้ปิด + เวลา
  - ไม่แก้ไข: บังคับระบุเหตุผล (ignore_reason)
  - ย้อนกลับเป็น Pending: ล้างข้อมูลการปิดรายการ
  - ถูกถามซ้ำหลัง Resolved: เปิดรายการกลับเป็น Pending อัตโนมัติ
"""
import pytest
from sqlalchemy import select

from tests.conftest import auth_header
from app.models.models import UnansweredQuery
from app.schemas.schemas import UnansweredSubmit
from app.services.unanswered_service import record_unanswered_query

pytestmark = pytest.mark.asyncio


async def _seed(db_session, status="Pending"):
    db_session.add(UnansweredQuery(id="unans-1", query="ISMS คืออะไร", count=1, status=status))
    await db_session.commit()


async def test_resolve_records_method_user_and_time(client, admin_user, db_session):
    await _seed(db_session)
    resp = await client.put(
        "/api/admin/unanswered/unans-1",
        json={"status": "Resolved", "resolution_type": "custom_faq", "note": "  เพิ่ม FAQ แล้ว "},
        headers=auth_header(admin_user.username),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "Resolved"
    assert data["resolution_type"] == "custom_faq"
    assert data["note"] == "เพิ่ม FAQ แล้ว"
    assert data["resolved_by"] == admin_user.display_name
    assert data["resolved_at"]


async def test_legacy_resolve_with_status_only_still_works(client, admin_user, db_session):
    await _seed(db_session)
    resp = await client.put(
        "/api/admin/unanswered/unans-1", json={"status": "Resolved"},
        headers=auth_header(admin_user.username),
    )
    assert resp.status_code == 200
    assert resp.json()["resolution_type"] is None


async def test_ignore_requires_reason(client, admin_user, db_session):
    await _seed(db_session)
    resp = await client.put(
        "/api/admin/unanswered/unans-1", json={"status": "Ignored"},
        headers=auth_header(admin_user.username),
    )
    assert resp.status_code == 422

    resp = await client.put(
        "/api/admin/unanswered/unans-1",
        json={"status": "Ignored", "ignore_reason": "spam", "note": "พิมพ์มั่ว"},
        headers=auth_header(admin_user.username),
    )
    assert resp.status_code == 200
    assert resp.json()["ignore_reason"] == "spam"


@pytest.mark.parametrize("payload", [
    {"status": "Done"},
    {"status": "Resolved", "resolution_type": "magic"},
    {"status": "Resolved", "ignore_reason": "spam"},
    {"status": "Ignored", "ignore_reason": "spam", "resolution_type": "custom_faq"},
    {"status": "Ignored", "ignore_reason": "other", "note": "x" * 1001},
])
async def test_invalid_payloads_rejected(client, admin_user, db_session, payload):
    await _seed(db_session)
    resp = await client.put(
        "/api/admin/unanswered/unans-1", json=payload, headers=auth_header(admin_user.username)
    )
    assert resp.status_code == 422


async def test_reset_to_pending_clears_resolution(client, admin_user, db_session):
    await _seed(db_session)
    headers = auth_header(admin_user.username)
    await client.put(
        "/api/admin/unanswered/unans-1",
        json={"status": "Ignored", "ignore_reason": "chit_chat", "note": "ทักทาย"},
        headers=headers,
    )
    resp = await client.put("/api/admin/unanswered/unans-1", json={"status": "Pending"}, headers=headers)
    data = resp.json()
    assert data["status"] == "Pending"
    assert data["ignore_reason"] is None and data["note"] is None
    assert data["resolved_by"] is None and data["resolved_at"] is None


async def test_list_includes_resolution_fields(client, admin_user, db_session):
    await _seed(db_session)
    headers = auth_header(admin_user.username)
    await client.put(
        "/api/admin/unanswered/unans-1",
        json={"status": "Resolved", "resolution_type": "document_upload"},
        headers=headers,
    )
    items = (await client.get("/api/admin/unanswered", headers=headers)).json()
    assert items[0]["resolution_type"] == "document_upload"
    assert items[0]["resolved_by"] == admin_user.display_name


async def test_update_requires_auth(client, db_session):
    await _seed(db_session)
    resp = await client.put("/api/admin/unanswered/unans-1", json={"status": "Resolved"})
    assert resp.status_code in (401, 403)


async def test_repeat_question_reopens_resolved_but_not_ignored(db_session, session_maker):
    db_session.add_all([
        UnansweredQuery(id="unans-r", query="ลาป่วยได้กี่วัน", count=1, status="Resolved",
                        resolution_type="custom_faq"),
        UnansweredQuery(id="unans-i", query="หอกหผอฟ", count=1, status="Ignored",
                        ignore_reason="spam"),
    ])
    await db_session.commit()

    async with session_maker() as s:
        await record_unanswered_query(s, UnansweredSubmit(query="ลาป่วยได้กี่วัน"))
        await record_unanswered_query(s, UnansweredSubmit(query="หอกหผอฟ"))

    async with session_maker() as s:
        reopened = (await s.execute(select(UnansweredQuery).where(UnansweredQuery.id == "unans-r"))).scalar_one()
        ignored = (await s.execute(select(UnansweredQuery).where(UnansweredQuery.id == "unans-i"))).scalar_one()
    assert reopened.status == "Pending" and reopened.count == 2 and reopened.resolution_type is None
    assert ignored.status == "Ignored" and ignored.count == 2 and ignored.ignore_reason == "spam"
