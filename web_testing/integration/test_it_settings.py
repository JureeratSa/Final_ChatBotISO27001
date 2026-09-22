"""
Integration Test — Settings Propagation & Key Masking (IT-04, IT-05)
ต่างจาก UT-13 (unit, เทสแค่ Pydantic bounds validation ของ SettingsUpdate เฉยๆ) ตรงที่เคสนี้
ยิง endpoint จริง 2 ครั้งต่อเนื่องกัน (settings -> chat) เพื่อพิสูจน์ว่าการตั้งค่าที่แอดมิน
บันทึกไว้จริงถูกนำไปใช้จริงตอนแชท ไม่ใช่แค่ validate แล้วเก็บเฉยๆ
"""
import pytest

from tests.conftest import auth_header

pytestmark = pytest.mark.asyncio


# ─── IT-04: ตั้งค่า custom_faqs ผ่าน /api/admin/settings แล้วมีผลจริงตอนแชท ──────

async def test_IT04_settings_update_propagates_to_chat_faq_matching(client, admin_user):
    from app.core import rate_limit as rate_limit_module
    rate_limit_module._hits.clear()  # กันเทสอื่นก่อนหน้านี้ทิ้ง state ไว้ (module-level dict)

    update_resp = await client.post(
        "/api/admin/settings",
        headers=auth_header(admin_user.username),
        json={
            "custom_faqs": [
                {"question": "โรงพยาบาลเปิดกี่โมง", "answer": "เปิดบริการ 08:00-16:00 น. ทุกวันทำการ"}
            ]
        },
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["custom_faqs"][0]["question"] == "โรงพยาบาลเปิดกี่โมง"

    chat_resp = await client.post("/api/chat", json={"query": "โรงพยาบาลเปิดกี่โมง"})
    assert chat_resp.status_code == 200
    body = chat_resp.json()
    assert body["answer"] == "เปิดบริการ 08:00-16:00 น. ทุกวันทำการ"
    assert body["used_rag"] is False


async def test_IT04_settings_update_cannot_override_model_name_or_api_key(client, admin_user, monkeypatch):
    from app.core.config import settings as app_settings
    monkeypatch.setattr(app_settings, "DEFAULT_LLM_MODEL", "gemini-2.0-flash-real")

    resp = await client.post(
        "/api/admin/settings",
        headers=auth_header(admin_user.username),
        json={"model_name": "some-other-model-client-tried-to-set"},
    )
    assert resp.status_code == 200
    # บังคับอ่านจาก settings/env เท่านั้น ไม่ให้ client เปลี่ยนจากหน้าเว็บได้ (admin.py:753)
    assert resp.json()["model_name"] == "gemini-2.0-flash-real"


async def test_IT04_settings_update_requires_system_administrator_role(client, staff_user):
    resp = await client.post(
        "/api/admin/settings",
        headers=auth_header(staff_user.username),
        json={"temperature": 0.9},
    )
    assert resp.status_code == 403


# ─── IT-05: GET /api/admin/settings ปิดบัง gemini_api_key ตามสิทธิ์ผู้เรียก ──────

async def test_IT05_settings_get_reveals_real_key_to_system_administrator(client, admin_user, monkeypatch):
    from app.core.config import settings as app_settings
    monkeypatch.setattr(app_settings, "GEMINI_API_KEY", "sk-real-secret-key")

    resp = await client.get("/api/admin/settings", headers=auth_header(admin_user.username))
    assert resp.status_code == 200
    assert resp.json()["gemini_api_key"] == "sk-real-secret-key"


async def test_IT05_settings_get_masks_key_for_non_system_administrator(client, staff_user, monkeypatch):
    from app.core.config import settings as app_settings
    monkeypatch.setattr(app_settings, "GEMINI_API_KEY", "sk-real-secret-key")

    resp = await client.get("/api/admin/settings", headers=auth_header(staff_user.username))
    assert resp.status_code == 200
    assert resp.json()["gemini_api_key"] == "***masked***"


async def test_IT05_settings_get_masks_key_for_unauthenticated_request(client, monkeypatch):
    from app.core.config import settings as app_settings
    monkeypatch.setattr(app_settings, "GEMINI_API_KEY", "sk-real-secret-key")

    resp = await client.get("/api/admin/settings")
    assert resp.status_code == 200
    assert resp.json()["gemini_api_key"] == "***masked***"
