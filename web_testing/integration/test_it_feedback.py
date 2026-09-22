"""
Integration Test — Feedback (IT-06)
ยิง endpoint จริง 3 ตัวต่อเนื่องกัน (submit -> list -> delete) ผ่าน DB จริง (SQLite ทดสอบ)
เพื่อพิสูจน์ logic dedup-by-(query,answer) ที่ยังไม่เคยมีเทสคลุมเลย (admin.py:813-828)
"""
import pytest

from tests.conftest import auth_header

pytestmark = pytest.mark.asyncio


# ─── IT-06: ส่ง feedback ซ้ำ (query+answer เดิม) ต้องอัปเดตแถวเดิม ไม่สร้างซ้ำ ──────

async def test_IT06_duplicate_query_answer_feedback_updates_existing_row_not_duplicates(client, admin_user):
    first = await client.post(
        "/api/admin/feedback/submit",
        json={"msgId": "m1", "rating": "like", "query": "ลาป่วยยังไง", "answer": "ยื่นใบลาผ่านระบบ HR"},
    )
    assert first.status_code == 201

    second = await client.post(
        "/api/admin/feedback/submit",
        json={
            "msgId": "m2", "rating": "dislike", "stars": 2, "comment": "ตอบไม่ครบ",
            "query": "ลาป่วยยังไง", "answer": "ยื่นใบลาผ่านระบบ HR",
        },
    )
    assert second.status_code == 201

    list_resp = await client.get("/api/admin/feedback", headers=auth_header(admin_user.username))
    matching = [f for f in list_resp.json() if f["query"] == "ลาป่วยยังไง" and f["answer"] == "ยื่นใบลาผ่านระบบ HR"]
    assert len(matching) == 1
    assert matching[0]["rating"] == "dislike"
    assert matching[0]["stars"] == 2
    assert matching[0]["comment"] == "ตอบไม่ครบ"


async def test_IT06_feedback_without_prior_match_creates_new_row(client, admin_user):
    resp = await client.post(
        "/api/admin/feedback/submit",
        json={"msgId": "m3", "rating": "like"},
    )
    assert resp.status_code == 201

    list_resp = await client.get("/api/admin/feedback", headers=auth_header(admin_user.username))
    assert len(list_resp.json()) == 1
    assert list_resp.json()[0]["id"].startswith("fb-")


async def test_IT06_feedback_submit_does_not_require_auth(client):
    resp = await client.post("/api/admin/feedback/submit", json={"msgId": "m4", "rating": "like"})
    assert resp.status_code == 201


async def test_IT06_feedback_list_requires_auth(client):
    resp = await client.get("/api/admin/feedback")
    assert resp.status_code in (401, 403)


async def test_IT06_delete_feedback_removes_row_and_404s_for_unknown_id(client, admin_user):
    await client.post("/api/admin/feedback/submit", json={"msgId": "m5", "rating": "like"})
    list_resp = await client.get("/api/admin/feedback", headers=auth_header(admin_user.username))
    feedback_id = list_resp.json()[0]["id"]

    del_resp = await client.delete(f"/api/admin/feedback/{feedback_id}", headers=auth_header(admin_user.username))
    assert del_resp.status_code == 204

    after_resp = await client.get("/api/admin/feedback", headers=auth_header(admin_user.username))
    assert after_resp.json() == []

    missing_resp = await client.delete("/api/admin/feedback/does-not-exist", headers=auth_header(admin_user.username))
    assert missing_resp.status_code == 404
