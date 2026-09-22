"""
Integration Test — Announcements CRUD + Public Active List (IT-08)
ต่างจาก UT-14 (unit, เทสฟังก์ชัน is_announcement_active() ตรงๆ ด้วยข้อมูลจำลอง) ตรงที่เคสนี้
สร้างประกาศผ่าน endpoint จริงของแอดมิน (POST /api/admin/announcements) แล้วเช็คว่าไปโผล่ที่
endpoint สาธารณะ GET /api/announcements/active จริง พร้อมพิสูจน์ว่า sanitize_html() ถูกเรียก
ใช้งานจริงตอนสร้างประกาศ (เดิมมีแต่เทสระดับฟังก์ชันเฉยๆ ใน test_sanitize.py ไม่เคยพิสูจน์ว่า
endpoint นี้เรียกใช้จริง)
"""
import datetime

import pytest

from tests.conftest import auth_header

pytestmark = pytest.mark.asyncio


def _today_range():
    today = datetime.date.today()
    return (today - datetime.timedelta(days=1)).isoformat(), (today + datetime.timedelta(days=1)).isoformat()


# ─── IT-08: สร้างประกาศผ่าน endpoint จริง -> sanitize + โผล่ใน public active list ──

async def test_IT08_create_announcement_sanitizes_content_and_sets_creator(client, admin_user):
    start, end = _today_range()
    resp = await client.post(
        "/api/admin/announcements",
        headers=auth_header(admin_user.username),
        json={
            "title": "แจ้งปิดปรับปรุงระบบ",
            "content": "<p>งดให้บริการ</p><script>alert(1)</script>",
            "start_date": start,
            "end_date": end,
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "<script" not in body["content"]
    assert "งดให้บริการ" in body["content"]
    assert body["created_by"] == admin_user.display_name


async def test_IT08_created_announcement_appears_in_public_active_list(client, admin_user):
    start, end = _today_range()
    create_resp = await client.post(
        "/api/admin/announcements",
        headers=auth_header(admin_user.username),
        json={"title": "ประกาศทดสอบ", "content": "เนื้อหา", "start_date": start, "end_date": end},
    )
    assert create_resp.status_code == 201

    active_resp = await client.get("/api/announcements/active")
    titles = [a["title"] for a in active_resp.json()]
    assert "ประกาศทดสอบ" in titles


async def test_IT08_announcement_outside_date_range_not_in_public_active_list(client, admin_user):
    future_start = (datetime.date.today() + datetime.timedelta(days=10)).isoformat()
    future_end = (datetime.date.today() + datetime.timedelta(days=20)).isoformat()
    await client.post(
        "/api/admin/announcements",
        headers=auth_header(admin_user.username),
        json={"title": "ประกาศอนาคต", "content": "ยังไม่ถึงเวลา", "start_date": future_start, "end_date": future_end},
    )

    active_resp = await client.get("/api/announcements/active")
    titles = [a["title"] for a in active_resp.json()]
    assert "ประกาศอนาคต" not in titles


async def test_IT08_update_announcement_resanitizes_content(client, admin_user):
    start, end = _today_range()
    create_resp = await client.post(
        "/api/admin/announcements",
        headers=auth_header(admin_user.username),
        json={"title": "ประกาศแก้ไขได้", "content": "เดิม", "start_date": start, "end_date": end},
    )
    ann_id = create_resp.json()["id"]

    update_resp = await client.put(
        f"/api/admin/announcements/{ann_id}",
        headers=auth_header(admin_user.username),
        json={"content": '<img src=x onerror="alert(1)">แก้ไขแล้ว'},
    )
    assert update_resp.status_code == 200
    assert "onerror" not in update_resp.json()["content"]
    assert "แก้ไขแล้ว" in update_resp.json()["content"]


async def test_IT08_delete_announcement_removes_it_and_404s_for_unknown_id(client, admin_user):
    start, end = _today_range()
    create_resp = await client.post(
        "/api/admin/announcements",
        headers=auth_header(admin_user.username),
        json={"title": "ประกาศจะถูกลบ", "content": "x", "start_date": start, "end_date": end},
    )
    ann_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/admin/announcements/{ann_id}", headers=auth_header(admin_user.username))
    assert del_resp.status_code == 204

    missing_resp = await client.delete(f"/api/admin/announcements/{ann_id}", headers=auth_header(admin_user.username))
    assert missing_resp.status_code == 404
