"""
Integration Test — Unanswered Queries (IT-07)
ยิง endpoint จริง (submit ซ้ำ -> triage ผ่าน PUT -> DELETE) เพื่อพิสูจน์ logic นับจำนวนซ้ำแบบ
case-insensitive (admin.py:878-883) ซึ่งเป็นคนละ code path จากที่ /api/chat เรียกผ่าน
save_unanswered() ตอนตอบไม่ได้ (ดู IT-09 กับ test_chat.py ที่มีอยู่แล้วสำหรับ path นั้น)
"""
import pytest

from tests.conftest import auth_header

pytestmark = pytest.mark.asyncio


# ─── IT-07: ส่งคำถามเดิมซ้ำ (ตัวพิมพ์ต่าง) ต้องเพิ่ม count ไม่สร้างแถวใหม่ ──────────

async def test_IT07_repeated_submission_case_insensitive_increments_count(client, admin_user):
    first = await client.post("/api/admin/unanswered/submit", json={"query": "ขอฟอร์มเบิกค่ารักษา"})
    assert first.status_code == 201

    second = await client.post("/api/admin/unanswered/submit", json={"query": "ขอฟอร์มเบิกค่ารักษา"})
    assert second.status_code == 201

    list_resp = await client.get("/api/admin/unanswered", headers=auth_header(admin_user.username))
    items = list_resp.json()
    assert len(items) == 1
    assert items[0]["count"] == 2


async def test_IT07_different_query_creates_separate_row(client, admin_user):
    await client.post("/api/admin/unanswered/submit", json={"query": "คำถาม A"})
    await client.post("/api/admin/unanswered/submit", json={"query": "คำถาม B"})

    list_resp = await client.get("/api/admin/unanswered", headers=auth_header(admin_user.username))
    assert len(list_resp.json()) == 2


async def test_IT07_admin_can_update_status_then_delete(client, admin_user):
    await client.post("/api/admin/unanswered/submit", json={"query": "ถามเรื่องที่ยังไม่มีคำตอบ"})
    list_resp = await client.get("/api/admin/unanswered", headers=auth_header(admin_user.username))
    query_id = list_resp.json()[0]["id"]

    update_resp = await client.put(
        f"/api/admin/unanswered/{query_id}",
        headers=auth_header(admin_user.username),
        json={"status": "Resolved"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["status"] == "Resolved"

    del_resp = await client.delete(f"/api/admin/unanswered/{query_id}", headers=auth_header(admin_user.username))
    assert del_resp.status_code == 204

    missing_update = await client.put(
        "/api/admin/unanswered/does-not-exist",
        headers=auth_header(admin_user.username),
        json={"status": "Resolved"},
    )
    assert missing_update.status_code == 404


async def test_IT07_submit_does_not_require_auth_but_update_delete_do(client):
    submit_resp = await client.post("/api/admin/unanswered/submit", json={"query": "คำถามสาธารณะ"})
    assert submit_resp.status_code == 201

    update_resp = await client.put("/api/admin/unanswered/whatever", json={"status": "Resolved"})
    assert update_resp.status_code in (401, 403)

    delete_resp = await client.delete("/api/admin/unanswered/whatever")
    assert delete_resp.status_code in (401, 403)
