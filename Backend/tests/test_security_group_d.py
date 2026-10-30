"""
Security audit 2026-10-30 — กลุ่ม D (Low)
L1 ไม่ส่ง chunk ดิบ/ชื่อโมเดลจริง · L3 เวลาตอบล็อกอินเท่ากัน · L4 logout ยกเลิก token ใบนั้น
L5 รายการประกาศทั้งหมดต้องล็อกอิน · L6 ไม่ส่งข้อความ error ภายใน · L9 status เอกสาร
L11 chunks-map ตามแผนก + limit · L13 IP ใน audit log · L15 เปลี่ยนรหัสแล้ว token เก่าใช้ไม่ได้ (ไม่ขึ้นกับจังหวะเวลา)
"""
import json

import pytest

from app.core.config import settings
from app.models.models import Announcement, Document
from tests.conftest import auth_header

pytestmark = pytest.mark.asyncio

STRONG = "Tuh#Chat2026q"


async def _login(client, username, password):
    resp = await client.post("/api/admin/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['token']}"}


# ─── L1 ────────────────────────────────────────────────────────────────────────

async def test_search_response_has_no_raw_chunks(client):
    body = (await client.post("/api/search", json={"query": "สวัสดีครับ"})).json()
    assert "results" not in body
    assert set(body) == {"answer", "citations", "form_links"}


async def test_public_model_label_hides_real_model_name():
    from app.routers.chat import public_model_label
    assert public_model_label("google/gemma-4-31B-it") == "llm"
    assert public_model_label("custom_faq") == "custom_faq"
    assert public_model_label("fallback") == "fallback"


# ─── L3 ────────────────────────────────────────────────────────────────────────

async def test_unknown_user_still_runs_bcrypt(monkeypatch):
    import app.core.security as security
    calls = []
    real = security.verify_password
    monkeypatch.setattr(security, "verify_password", lambda p, h: calls.append(h) or real(p, h))
    assert security.verify_user_password("whatever", None) is False
    assert calls == [security._DUMMY_PASSWORD_HASH]


# ─── L4 / L15 ──────────────────────────────────────────────────────────────────

async def test_logout_revokes_only_that_token(client, staff_user):
    first = await _login(client, staff_user.username, "Staff!2345")
    second = await _login(client, staff_user.username, "Staff!2345")     # อีกเครื่องของคนเดียวกัน
    assert (await client.get("/api/admin/documents", headers=first)).status_code == 200

    assert (await client.post("/api/admin/logout", headers=first)).status_code == 200
    assert (await client.get("/api/admin/documents", headers=first)).status_code == 401
    assert (await client.get("/api/admin/documents", headers=second)).status_code == 200


@pytest.mark.parametrize("attempt", range(3))   # เดิมผ่านบ้างไม่ผ่านบ้างตามจังหวะวินาที
async def test_password_change_revokes_tokens_immediately(client, staff_user, attempt):
    h = await _login(client, staff_user.username, "Staff!2345")
    assert (await client.post("/api/admin/password/update", json={"new_password": STRONG}, headers=h)).status_code == 200
    assert (await client.get("/api/admin/documents", headers=h)).status_code == 401
    assert (await client.get("/api/admin/documents", headers=await _login(client, staff_user.username, STRONG))).status_code == 200


async def test_superadmin_reset_revokes_target_tokens(client, admin_user, staff_user):
    h = await _login(client, staff_user.username, "Staff!2345")
    resp = await client.put(f"/api/auth/users/{staff_user.id}", json={"password": STRONG},
                            headers=auth_header(admin_user.username))
    assert resp.status_code == 200
    assert (await client.get("/api/admin/documents", headers=h)).status_code == 401


# ─── L5 / L6 ───────────────────────────────────────────────────────────────────

async def test_admin_announcement_list_requires_login(client, db_session, staff_user):
    db_session.add(Announcement(title="ร่าง", start_date="2100-01-01", end_date="2100-01-02"))
    await db_session.commit()
    assert (await client.get("/api/admin/announcements")).status_code in (401, 403)
    assert (await client.get("/api/admin/announcements", headers=auth_header(staff_user.username))).status_code == 200


async def test_invalid_token_detail_is_generic(client):
    resp = await client.get("/api/admin/documents", headers={"Authorization": "Bearer not.a.jwt"})
    assert resp.status_code == 401
    assert "Invalid token" not in resp.json()["detail"]


# ─── L9 ────────────────────────────────────────────────────────────────────────

async def test_document_status_only_active_or_inactive(client, db_session, staff_user, monkeypatch):
    import app.routers.admin_documents as docs_module
    monkeypatch.setattr(docs_module, "_trigger_rebuild_background", lambda: None)
    db_session.add(Document(filename="d.pdf", display_name="d", status="Step_Raw_Text", department=staff_user.department))
    await db_session.commit()
    h = auth_header(staff_user.username)
    assert (await client.put("/api/admin/documents/d.pdf", json={"status": "Step_Chunk_Preview"}, headers=h)).status_code == 422
    assert (await client.put("/api/admin/documents/d.pdf", json={"status": "Inactive"}, headers=h)).status_code == 200


# ─── L11 ───────────────────────────────────────────────────────────────────────

async def test_chunks_map_is_department_scoped(client, db_session, staff_user, admin_user, tmp_path, monkeypatch):
    (tmp_path / "sample_chunks.json").write_text(json.dumps([
        {"chunk_id": 1, "content": "ของแผนกเรา", "metadata": {"source": "mine.pdf", "page": 1}},
        {"chunk_id": 2, "content": "ของแผนกอื่น", "metadata": {"source": "theirs.pdf", "page": 1}},
    ], ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(type(settings), "ADMIN_DIR", property(lambda self: str(tmp_path / "Admin")))
    db_session.add_all([
        Document(filename="mine.pdf", display_name="m", department=staff_user.department),
        Document(filename="theirs.pdf", display_name="t", department="งานอื่น"),
    ])
    await db_session.commit()

    staff_map = (await client.get("/api/admin/history/chunks-map", headers=auth_header(staff_user.username))).json()
    assert set(staff_map) == {"1"}
    admin_map = (await client.get("/api/admin/history/chunks-map", headers=auth_header(admin_user.username))).json()
    assert set(admin_map) == {"1", "2"}


async def test_history_limit_is_clamped(client, admin_user):
    resp = await client.get("/api/admin/history", params={"limit": 10**9}, headers=auth_header(admin_user.username))
    assert resp.status_code == 200


# ─── L13 ───────────────────────────────────────────────────────────────────────

async def test_audit_ip_follows_trusted_proxy_setting(monkeypatch):
    from starlette.requests import Request
    from app.services.audit_service import _client_ip
    req = Request({"type": "http", "headers": [(b"x-forwarded-for", b"10.9.8.7")], "client": ("172.18.0.9", 1)})
    assert _client_ip(req) == "172.18.0.9"
    monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", True)
    assert _client_ip(req) == "10.9.8.7"
