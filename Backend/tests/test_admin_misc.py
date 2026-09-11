"""
Integration tests สำหรับ endpoint ที่ AdminWeb เรียกใช้จริงแต่ backend ไม่เคยมี route รองรับมาก่อน
(เจอตอนตรวจโค้ด 2026-09-07 — grep หา endpoint ที่ frontend fetch() แล้วเทียบกับ route ที่มีจริง):

  - POST /api/admin/documents/update_details  (หน้าต่างแก้ไขรายละเอียดเอกสาร)
  - POST /api/admin/unanswered/analyze        (AI วิเคราะห์คำถามที่ตอบไม่ได้)

ทั้งสอง endpoint เคยตอบ 404 เสมอ เพราะไม่มี route ใน admin.py มาก่อนเลย
"""
import pytest

from tests.conftest import auth_header
from app.models.models import Document

pytestmark = pytest.mark.asyncio


# ─── POST /documents/update_details ─────────────────────────────────────────────

async def test_update_document_details_changes_display_name(client, admin_user, db_session):
    db_session.add(Document(filename="welfare.pdf", display_name="เดิม", status="Active"))
    await db_session.commit()

    resp = await client.post(
        "/api/admin/documents/update_details",
        json={"filename": "welfare.pdf", "display_name": "ชื่อใหม่"},
        headers=auth_header(admin_user.username),
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    check = await client.get("/api/admin/documents", headers=auth_header(admin_user.username))
    doc = next(d for d in check.json() if d["filename"] == "welfare.pdf")
    assert doc["display_name"] == "ชื่อใหม่"


async def test_update_document_details_requires_auth(client, db_session):
    db_session.add(Document(filename="welfare.pdf", display_name="เดิม", status="Active"))
    await db_session.commit()

    resp = await client.post(
        "/api/admin/documents/update_details",
        json={"filename": "welfare.pdf", "display_name": "แฮ็ก"},
    )
    assert resp.status_code in (401, 403)


async def test_update_document_details_404_for_missing_doc(client, admin_user):
    resp = await client.post(
        "/api/admin/documents/update_details",
        json={"filename": "does-not-exist.pdf", "display_name": "x"},
        headers=auth_header(admin_user.username),
    )
    assert resp.status_code == 404


async def test_non_owner_staff_cannot_update_details_of_someone_elses_document(
    client, other_staff_user, db_session, staff_user
):
    db_session.add(Document(
        filename="staff-doc.pdf", display_name="เดิม", status="Active", uploaded_by=staff_user.display_name
    ))
    await db_session.commit()

    resp = await client.post(
        "/api/admin/documents/update_details",
        json={"filename": "staff-doc.pdf", "display_name": "พยายามแก้ของคนอื่น"},
        headers=auth_header(other_staff_user.username),
    )
    assert resp.status_code == 403


# ─── POST /unanswered/analyze ────────────────────────────────────────────────────

async def test_analyze_query_without_llm_key_returns_neutral_result(client, admin_user, monkeypatch):
    """ไม่มี LLM API key ตั้งไว้ (ค่าปกติในสภาพแวดล้อมเทส) — ต้องไม่ error ต้องคืนค่ากลางๆ ให้ UI ใช้ต่อได้"""
    from app.core.config import settings
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", None)

    resp = await client.post(
        "/api/admin/unanswered/analyze",
        json={"query": "สิทธิลาคลอดกี่วัน"},
        headers=auth_header(admin_user.username),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "is_valid_query" in body
    assert "suggested_keywords" in body


async def test_analyze_query_detects_chitchat_without_calling_llm(client, admin_user):
    resp = await client.post(
        "/api/admin/unanswered/analyze",
        json={"query": "สวัสดีครับ"},
        headers=auth_header(admin_user.username),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_valid_query"] is False
    assert body["suggested_keywords"] == []


async def test_analyze_query_requires_auth(client):
    resp = await client.post("/api/admin/unanswered/analyze", json={"query": "test"})
    assert resp.status_code in (401, 403)
