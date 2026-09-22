"""
Integration Test — Auth Round Trip (IT-03)
ต่างจาก UT-03/UT-04/UT-05 (unit, เทสฟังก์ชัน security.py ตรงๆ) ตรงที่เคสนี้ยิงผ่าน HTTP จริง
ครบวงจร: POST /api/auth/login (ของจริง ไม่ใช่ create_access_token() ลัดแบบ auth_header())
แล้วเอา token ที่ได้ไปเรียก endpoint ของ "อีก router หนึ่ง" (admin.py) เพื่อพิสูจน์ว่า
get_current_user + verify_access_token ต่อกันถูกต้องข้าม router จริงในแอปเดียวกัน
"""
import pytest

pytestmark = pytest.mark.asyncio


# ─── IT-03: login จริง -> ใช้ token ไปเรียก endpoint router อื่น ──────────────────

async def test_IT03_login_issued_token_authorizes_admin_router(client, admin_user):
    login_resp = await client.post(
        "/api/auth/login",
        json={"username": "sysadmin", "password": "Adm1n!2345"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    assert token

    docs_resp = await client.get(
        "/api/admin/documents",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert docs_resp.status_code == 200
    assert docs_resp.json() == []


async def test_IT03_login_wrong_password_token_cannot_authorize_admin_router(client, admin_user):
    login_resp = await client.post(
        "/api/auth/login",
        json={"username": "sysadmin", "password": "WrongPassword!"},
    )
    assert login_resp.status_code == 401

    # ยังไม่มี token ให้ใช้เลย — ยืนยันว่า endpoint ที่ต้อง auth ปฏิเสธ request ที่ไม่มี token
    docs_resp = await client.get("/api/admin/documents")
    assert docs_resp.status_code in (401, 403)
