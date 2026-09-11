"""
Unit test: app/core/rate_limit.py
เดิม /api/chat ไม่มีการจำกัดจำนวน request เลย ยิงรัวจาก IP เดียวได้ไม่จำกัด
"""
import pytest

pytestmark = pytest.mark.asyncio


async def test_chat_endpoint_returns_429_after_limit_exceeded(client, monkeypatch):
    from app.core.config import settings
    from app.core import rate_limit as rate_limit_module

    monkeypatch.setattr(settings, "RATE_LIMIT_REQUESTS", 3)
    monkeypatch.setattr(settings, "RATE_LIMIT_WINDOW_SECONDS", 60)
    rate_limit_module._hits.clear()  # กันเทสอื่นก่อนหน้านี้ทิ้ง state ไว้ (module-level dict)

    statuses = []
    for _ in range(5):
        resp = await client.post("/api/chat", json={"query": "สวัสดีครับ"})
        statuses.append(resp.status_code)

    assert statuses[:3] == [200, 200, 200]
    assert 429 in statuses[3:]
