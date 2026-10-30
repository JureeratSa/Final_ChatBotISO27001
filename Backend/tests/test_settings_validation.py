"""
Integration tests: POST/PUT /api/admin/settings — input bounds
เดิม temperature/max_tokens/top_k ไม่มีขอบเขตเลย ตั้งค่าประหลาดๆ จาก UI ได้ (เช่น temperature=999,
top_k=100000) ซึ่งอาจทำให้ LLM ตอบเพี้ยนหรือ context ยาวเกิน token limit ของโมเดล
"""
import pytest

from tests.conftest import auth_header

pytestmark = pytest.mark.asyncio


async def test_update_settings_accepts_values_within_bounds(client, admin_user):
    resp = await client.post(
        "/api/admin/settings",
        json={"temperature": 0.7, "max_tokens": 1500, "top_k": 5},
        headers=auth_header(admin_user.username),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["temperature"] == 0.7
    assert body["max_tokens"] == 1500
    assert body["top_k"] == 5


@pytest.mark.parametrize("payload", [
    {"temperature": 999},
    {"temperature": -1},
    {"max_tokens": 0},
    {"max_tokens": 999999},
    {"top_k": 0},
    {"top_k": 100000},
])
async def test_update_settings_rejects_out_of_bound_values(client, admin_user, payload):
    resp = await client.post(
        "/api/admin/settings",
        json=payload,
        headers=auth_header(admin_user.username),
    )
    assert resp.status_code == 422


async def test_chat_rejects_query_over_max_length(client):
    resp = await client.post("/api/chat", json={"query": "ก" * 2001})
    assert resp.status_code == 422


# ─── LLM endpoint (GDCC LiteLLM) ───────────────────────────────────────────────

def test_llm_chat_url_is_built_from_litellm_url(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "LITELLM_URL", "https://llm.example/v1/")
    assert settings.LLM_CHAT_URL == "https://llm.example/v1/chat/completions"
    monkeypatch.setattr(settings, "LITELLM_URL", None)
    assert settings.LLM_CHAT_URL == ""


def test_llm_api_key_comes_from_litellm_key(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "LITELLM_API_KEY", "abc")
    assert settings.LLM_API_KEY == "abc"
    monkeypatch.setattr(settings, "LITELLM_API_KEY", None)
    assert settings.LLM_API_KEY == ""


async def test_update_settings_does_not_store_api_key_in_db(client, admin_user, db_session, monkeypatch):
    """API key อยู่ใน .env เท่านั้น — เดิมบันทึกหน้าตั้งค่าแล้ว key จริงถูกเขียนลงตาราง settings"""
    from sqlalchemy import select
    from app.core.config import settings
    from app.models.models import SystemSettings
    monkeypatch.setattr(settings, "LITELLM_API_KEY", "secret-key")
    db_session.add(SystemSettings(id="config", gemini_api_key="old-leaked-key"))
    await db_session.commit()

    resp = await client.post(
        "/api/admin/settings",
        json={"top_k": 5},
        headers=auth_header(admin_user.username),
    )
    assert resp.status_code == 200

    db_session.expire_all()
    cfg = (await db_session.execute(select(SystemSettings).where(SystemSettings.id == "config"))).scalar_one()
    assert cfg.gemini_api_key is None


async def test_get_settings_never_returns_real_api_key(client, admin_user, monkeypatch):
    """แม้เป็น System Administrator ก็ได้แค่ค่าที่ซ่อนไว้ — key จริงไม่ออกจาก backend"""
    from app.core.config import settings
    monkeypatch.setattr(settings, "LITELLM_API_KEY", "secret-key")

    # ไม่ล็อกอินเรียกไม่ได้แล้ว (security audit M1) — ล็อกอินแล้วก็ยังได้แค่ค่าที่ซ่อนไว้
    assert (await client.get("/api/admin/settings")).status_code in (401, 403)
    resp = await client.get("/api/admin/settings", headers=auth_header(admin_user.username))
    assert resp.status_code == 200
    assert resp.json()["gemini_api_key"] == "***masked***"
    assert "secret-key" not in resp.text
