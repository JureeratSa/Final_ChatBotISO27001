"""
Integration tests: บันทึกการเข้าใช้งานของแอดมิน (app/services/audit_service.py)
- ล็อกอินสำเร็จ/ไม่สำเร็จ, ออกจากระบบ และคำขอที่แก้ไขข้อมูลถูกบันทึก พร้อม IP และ User-Agent
- ไม่เก็บรหัสผ่านหรือ request body ลง log
- การเปลี่ยนสิทธิ์ผู้ใช้บันทึกค่าเดิม → ค่าใหม่
- ดูบันทึกได้เฉพาะ SuperAdmin
"""
import json

import pytest
from sqlalchemy import select

from app.models.models import AdminAuditLog
from tests.conftest import auth_header

pytestmark = pytest.mark.asyncio

UA = {"user-agent": "pytest-browser/1.0"}


async def _logs(db_session):
    query = select(AdminAuditLog).order_by(AdminAuditLog.id).execution_options(populate_existing=True)
    return (await db_session.execute(query)).scalars().all()


async def test_login_success_and_failure_are_logged_without_password(client, staff_user, db_session):
    await client.post("/api/admin/login", json={"username": "staff01", "password": "wrong-pass-123"}, headers=UA)
    await client.post("/api/admin/login", json={"username": "staff01", "password": "Staff!2345"}, headers=UA)
    await client.post("/api/admin/login", json={"username": "nobody", "password": "x"}, headers=UA)

    logs = await _logs(db_session)
    assert [(l.action, l.username, l.status_code) for l in logs] == [
        ("login_failed", "staff01", 401),
        ("login_success", "staff01", 200),
        ("login_failed", "nobody", 401),
    ]
    assert logs[1].user_id == staff_user.id
    assert logs[1].department == "งานสารสนเทศ"
    assert logs[2].user_id is None
    assert all(l.ip_address and l.user_agent == "pytest-browser/1.0" for l in logs)
    stored = " ".join(f"{l.detail} {l.path}" for l in logs)
    assert "wrong-pass-123" not in stored and "Staff!2345" not in stored


async def test_admin_changes_are_logged_with_actor(client, staff_user, db_session):
    from app.models.models import UnansweredQuery
    db_session.add(UnansweredQuery(id="u-q", query="q", department=staff_user.department))
    await db_session.commit()
    await client.post("/api/admin/custom_faqs", json={"question": "q", "answer": "a"},
                      headers={**auth_header(staff_user.username), **UA})
    log = (await _logs(db_session))[-1]
    assert (log.action, log.method, log.path, log.username, log.status_code) == (
        "change", "POST", "/api/admin/custom_faqs", "staff01", 200)


async def test_denied_change_is_logged(client, staff_user, db_session):
    await client.post("/api/admin/rebuild", headers=auth_header(staff_user.username))
    log = (await _logs(db_session))[-1]
    assert (log.path, log.status_code, log.username) == ("/api/admin/rebuild", 403, "staff01")


async def test_reads_and_public_submits_are_not_logged(client, staff_user, db_session):
    await client.get("/api/admin/documents", headers=auth_header(staff_user.username))
    await client.post("/api/admin/feedback/submit", json={"msgId": "m1", "rating": "like"})
    assert await _logs(db_session) == []


async def test_permission_change_records_old_and_new_values(client, admin_user, staff_user, db_session):
    await client.put(f"/api/auth/users/{staff_user.id}",
                     json={"department": "งานการพยาบาล", "password": "NewPass!234"},
                     headers=auth_header(admin_user.username))
    log = (await _logs(db_session))[-1]
    detail = json.loads(log.detail)
    assert detail["target_user"] == "staff01"
    assert detail["changes"]["department"] == ["งานสารสนเทศ", "งานการพยาบาล"]
    assert detail["changes"]["password"] == "changed"
    assert "NewPass!234" not in log.detail


async def test_logout_is_logged(client, staff_user, db_session):
    resp = await client.post("/api/admin/logout?reason=idle", headers=auth_header(staff_user.username))
    assert resp.status_code == 200
    log = (await _logs(db_session))[-1]
    assert (log.action, log.username, json.loads(log.detail)["reason"]) == ("logout", "staff01", "idle")


async def test_only_super_admin_reads_audit_logs(client, admin_user, staff_user, db_session):
    await client.post("/api/admin/login", json={"username": "staff01", "password": "Staff!2345"})
    assert (await client.get("/api/admin/audit-logs", headers=auth_header(staff_user.username))).status_code == 403

    resp = await client.get("/api/admin/audit-logs", headers=auth_header(admin_user.username))
    assert resp.status_code == 200
    assert resp.json()[0]["action"] == "login_success"


# ─── ระบุรายการที่ถูกเพิ่ม/ลบ/แก้ ──────────────────────────────────────────────────

@pytest.fixture
def _no_rebuild(monkeypatch):
    import app.routers.admin_documents as docs_module
    monkeypatch.setattr(docs_module, "_trigger_rebuild_background", lambda: None)
    monkeypatch.setattr(docs_module, "_delete_from_search_index", lambda *_: None)


async def test_document_delete_records_which_file(client, staff_user, db_session, tmp_path, monkeypatch, _no_rebuild):
    import app.routers.admin_documents as docs_module
    from app.models.models import Document
    monkeypatch.setattr(docs_module, "UPLOADS_DIR", tmp_path)
    db_session.add(Document(filename="wifi_policy.pdf", display_name="นโยบาย wifi", status="Active",
                            department="งานสารสนเทศ"))
    await db_session.commit()

    await client.post("/api/admin/documents/delete", json={"filename": "wifi_policy.pdf"},
                      headers=auth_header(staff_user.username))
    detail = json.loads((await _logs(db_session))[-1].detail)
    assert detail["document"] == "wifi_policy.pdf"
    assert detail["document_name"] == "นโยบาย wifi"
    assert detail["department"] == "งานสารสนเทศ"


async def test_document_upload_records_filename(client, staff_user, db_session, tmp_path, monkeypatch, _no_rebuild):
    import app.routers.admin_documents as docs_module
    from Admin import pdf_ocr
    monkeypatch.setattr(docs_module, "UPLOADS_DIR", tmp_path)
    monkeypatch.setattr(pdf_ocr, "extract_pages", lambda *a, **k: [])

    await client.post("/api/admin/documents/upload", content=b"%PDF-1.4 secret body text",
                      headers={**auth_header(staff_user.username), "content-type": "application/pdf",
                               "x-file-name": "new_policy.pdf"})
    log = (await _logs(db_session))[-1]
    detail = json.loads(log.detail)
    assert (detail["document"], detail["department"]) == ("new_policy.pdf", "งานสารสนเทศ")
    assert "secret body text" not in log.detail


async def test_announcement_delete_records_title(client, admin_user, db_session):
    from app.models.models import Announcement
    db_session.add(Announcement(id=7, title="ปิดระบบปรับปรุง"))
    await db_session.commit()
    await client.post("/api/admin/announcements/delete", json={"id": 7}, headers=auth_header(admin_user.username))
    detail = json.loads((await _logs(db_session))[-1].detail)
    assert (detail["announcement_id"], detail["announcement"]) == (7, "ปิดระบบปรับปรุง")


async def test_settings_change_records_field_names_not_values(client, admin_user, db_session):
    await client.post("/api/admin/settings", json={"system_prompt": "ข้อความลับยาวๆ", "top_k": 4},
                      headers=auth_header(admin_user.username))
    log = (await _logs(db_session))[-1]
    assert json.loads(log.detail)["changed_fields"] == ["system_prompt", "top_k"]
    assert "ข้อความลับยาวๆ" not in log.detail


async def test_reading_a_document_is_not_logged(client, staff_user, db_session, tmp_path, monkeypatch):
    import app.routers.admin_documents as docs_module
    from app.models.models import Document
    monkeypatch.setattr(docs_module, "UPLOADS_DIR", tmp_path)
    (tmp_path / "a.pdf.raw.txt").write_text("x", encoding="utf-8")
    db_session.add(Document(filename="a.pdf", status="Step_Raw_Text", department="งานสารสนเทศ"))
    await db_session.commit()
    resp = await client.get("/api/admin/documents/view_raw?filename=a.pdf", headers=auth_header(staff_user.username))
    assert resp.status_code == 200
    assert await _logs(db_session) == []
