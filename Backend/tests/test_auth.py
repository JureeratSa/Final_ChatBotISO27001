"""
Integration tests: POST/GET /api/auth/*
ครอบคลุม Login, Refresh, /me, และ RBAC ของ Admin User Management
"""
import pytest

from tests.conftest import auth_header

pytestmark = pytest.mark.asyncio


# ─── Login ──────────────────────────────────────────────────────────────────────

async def test_login_success_returns_token_pair(client, admin_user):
    resp = await client.post(
        "/api/auth/login", json={"username": "sysadmin", "password": "Adm1n!2345"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "sysadmin"
    assert body["role"] == "System Administrator"
    assert body["access_token"] and body["refresh_token"]
    assert body["token_type"] == "bearer"


async def test_login_wrong_password_rejected(client, admin_user):
    resp = await client.post(
        "/api/auth/login", json={"username": "sysadmin", "password": "wrong-password"}
    )
    assert resp.status_code == 401


async def test_login_unknown_username_rejected(client):
    resp = await client.post(
        "/api/auth/login", json={"username": "nobody", "password": "whatever"}
    )
    assert resp.status_code == 401


async def test_login_inactive_user_rejected(client, db_session, admin_user):
    admin_user.is_active = False
    await db_session.merge(admin_user)
    await db_session.commit()

    resp = await client.post(
        "/api/auth/login", json={"username": "sysadmin", "password": "Adm1n!2345"}
    )
    assert resp.status_code == 401


# ─── /me + token validation ─────────────────────────────────────────────────────

async def test_me_without_token_is_rejected(client):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401  # HTTPBearer: missing Authorization header


async def test_me_with_garbage_token_is_401(client):
    resp = await client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert resp.status_code == 401


async def test_me_with_valid_token_returns_current_user(client, staff_user):
    resp = await client.get("/api/auth/me", headers=auth_header("staff01"))
    assert resp.status_code == 200
    assert resp.json()["username"] == "staff01"
    assert resp.json()["role"] == "admin"


# ─── Refresh token flow ─────────────────────────────────────────────────────────

async def test_refresh_token_issues_new_access_token(client, admin_user):
    login_resp = await client.post(
        "/api/auth/login", json={"username": "sysadmin", "password": "Adm1n!2345"}
    )
    refresh_token = login_resp.json()["refresh_token"]

    resp = await client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert resp.json()["access_token"]


async def test_refresh_with_access_token_is_rejected(client, admin_user):
    """ต้องแยกชนิด token: เอา access token ไปสวมรอยเป็น refresh token ไม่ได้"""
    login_resp = await client.post(
        "/api/auth/login", json={"username": "sysadmin", "password": "Adm1n!2345"}
    )
    access_token = login_resp.json()["access_token"]

    resp = await client.post("/api/auth/refresh", json={"refresh_token": access_token})
    assert resp.status_code == 401


# ─── RBAC: /api/auth/users (System Administrator only) ─────────────────────────

async def test_non_admin_cannot_list_users(client, staff_user):
    resp = await client.get("/api/auth/users", headers=auth_header("staff01"))
    assert resp.status_code == 403


async def test_admin_can_list_users(client, admin_user, staff_user):
    resp = await client.get("/api/auth/users", headers=auth_header("sysadmin"))
    assert resp.status_code == 200
    usernames = {u["username"] for u in resp.json()}
    assert {"sysadmin", "staff01"} <= usernames


async def test_non_admin_cannot_create_user(client, staff_user):
    resp = await client.post(
        "/api/auth/users",
        json={"username": "newperson", "password": "Xx123456!", "display_name": "ใหม่", "role": "admin"},
        headers=auth_header("staff01"),
    )
    assert resp.status_code == 403


async def test_admin_can_create_user(client, admin_user):
    resp = await client.post(
        "/api/auth/users",
        json={"username": "newperson", "password": "Xx123456!", "display_name": "ใหม่", "role": "admin"},
        headers=auth_header("sysadmin"),
    )
    assert resp.status_code == 201
    assert resp.json()["username"] == "newperson"


async def test_admin_cannot_create_user_with_weak_password(client, admin_user):
    """
    Regression test: เดิมไม่มีการบังคับความยาวรหัสผ่านเลยตอนสร้าง user (ผ่าน field validator)
    ทำให้ตั้งรหัสผ่านสั้นๆ เดาง่ายได้ — ตอนนี้ต้องยาวอย่างน้อย 8 ตัวอักษร
    """
    resp = await client.post(
        "/api/auth/users",
        json={"username": "weakpw", "password": "1234", "display_name": "สั้น", "role": "admin"},
        headers=auth_header("sysadmin"),
    )
    assert resp.status_code == 422


async def test_admin_cannot_create_duplicate_username(client, admin_user, staff_user):
    resp = await client.post(
        "/api/auth/users",
        json={"username": "staff01", "password": "Xx123456!", "display_name": "ซ้ำ", "role": "admin"},
        headers=auth_header("sysadmin"),
    )
    assert resp.status_code == 400


async def test_admin_can_deactivate_user(client, admin_user, staff_user):
    resp = await client.put(
        f"/api/auth/users/{staff_user.id}",
        json={"is_active": False},
        headers=auth_header("sysadmin"),
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


async def test_admin_cannot_delete_own_account(client, admin_user):
    resp = await client.delete(f"/api/auth/users/{admin_user.id}", headers=auth_header("sysadmin"))
    assert resp.status_code == 400


async def test_admin_can_delete_other_user(client, admin_user, staff_user):
    resp = await client.delete(f"/api/auth/users/{staff_user.id}", headers=auth_header("sysadmin"))
    assert resp.status_code == 204


async def test_delete_nonexistent_user_is_404(client, admin_user):
    resp = await client.delete("/api/auth/users/999999", headers=auth_header("sysadmin"))
    assert resp.status_code == 404
