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
