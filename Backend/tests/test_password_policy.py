"""
Tests: กฎรหัสผ่านแอดมิน + อายุรหัสผ่าน 90 วัน (app/services/password_policy.py)
- รหัสผ่านต้องยาว ≥ 8, มีตัวพิมพ์ใหญ่/เล็ก/ตัวเลข/สัญลักษณ์ และไม่ใช่รหัสเดาง่าย
- ครบ 90 วันแล้วใช้งานได้แค่การเปลี่ยนรหัสผ่าน (403 PASSWORD_EXPIRED) — เหลือ ≤ 7 วันแจ้งเตือนตอนล็อกอิน
- เปลี่ยนรหัสแล้ว token เดิมใช้ไม่ได้ ต้องล็อกอินใหม่
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.services.password_policy import password_problems, password_status
from tests.conftest import auth_header

pytestmark = pytest.mark.asyncio

STRONG = "Tuh#Chat2026q"


# ─── กฎรหัสผ่าน ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("password", [
    "Ab1!",            # สั้นเกิน
    "abcdefg1!",       # ไม่มีตัวพิมพ์ใหญ่
    "ABCDEFG1!",       # ไม่มีตัวพิมพ์เล็ก
    "Abcdefgh!",       # ไม่มีตัวเลข
    "Abcdefgh1",       # ไม่มีสัญลักษณ์
    "Password1!",      # คำเดาง่าย
    "P@ssw0rd!9",      # คำเดาง่ายแบบแทนตัวเลข
    "Xx123456!",       # ลำดับตัวเลข
    "Qwerty#2026",
    "Aaaa#Bb12",       # ตัวซ้ำติดกัน
])
async def test_weak_passwords_rejected(password):
    assert password_problems(password)


async def test_strong_password_accepted():
    assert password_problems(STRONG) == []


async def test_username_inside_password_rejected():
    assert password_problems("Staff01#Tuh9", "staff01")


# ─── อายุรหัสผ่าน ──────────────────────────────────────────────────────────────

async def test_password_status_windows():
    now = datetime(2026, 10, 29, tzinfo=timezone.utc)
    fresh = password_status(now - timedelta(days=10), now)
    assert (fresh["password_days_left"], fresh["password_expiring_soon"], fresh["password_expired"]) == (80, False, False)
    soon = password_status(now - timedelta(days=85), now)
    assert (soon["password_days_left"], soon["password_expiring_soon"], soon["password_expired"]) == (5, True, False)
    old = password_status(now - timedelta(days=91), now)
    assert old["password_expired"] is True
    assert password_status(None, now)["password_expired"] is True


async def _set_changed_at(db_session, user, days_ago):
    user.password_changed_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
    db_session.add(user)
    await db_session.commit()


async def test_login_reports_expiring_soon(client, db_session, staff_user):
    await _set_changed_at(db_session, staff_user, 85)
    data = (await client.post("/api/admin/login", json={"username": "staff01", "password": "Staff!2345"})).json()
    assert data["password_expiring_soon"] is True
    assert data["password_expired"] is False
    assert 1 <= data["password_days_left"] <= 7


async def test_expired_password_allows_only_password_change(client, db_session, staff_user):
    await _set_changed_at(db_session, staff_user, 95)
    login = (await client.post("/api/admin/login", json={"username": "staff01", "password": "Staff!2345"})).json()
    assert login["password_expired"] is True
    h = {"Authorization": f"Bearer {login['token']}"}

    blocked = await client.get("/api/admin/documents", headers=h)
    assert blocked.status_code == 403
    assert blocked.json()["detail"].startswith("PASSWORD_EXPIRED")

    changed = await client.post("/api/admin/password/update", json={"new_password": STRONG}, headers=h)
    assert changed.status_code == 200

    # token เดิมใช้ไม่ได้แล้ว ต้องล็อกอินใหม่ด้วยรหัสผ่านใหม่ แล้วใช้งานได้ตามสิทธิ์
    assert (await client.get("/api/admin/documents", headers=h)).status_code == 401
    relogin = (await client.post("/api/admin/login", json={"username": "staff01", "password": STRONG})).json()
    assert relogin["password_expired"] is False
    ok = await client.get("/api/admin/documents", headers={"Authorization": f"Bearer {relogin['token']}"})
    assert ok.status_code == 200


async def test_password_update_enforces_rules(client, staff_user):
    h = auth_header(staff_user.username)
    weak = await client.post("/api/admin/password/update", json={"new_password": "password123"}, headers=h)
    assert weak.status_code == 400
    same = await client.post("/api/admin/password/update", json={"new_password": "Staff!2345"}, headers=h)
    assert same.status_code == 400
    assert "รหัสผ่านเดิม" in same.json()["detail"]


async def test_super_admin_reset_rejects_weak_password(client, admin_user, staff_user):
    resp = await client.put(f"/api/auth/users/{staff_user.id}", json={"password": "12345678"},
                            headers=auth_header(admin_user.username))
    assert resp.status_code in (400, 422)
