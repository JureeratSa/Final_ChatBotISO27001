"""
เวลาที่ส่งไปแสดงต้องเป็นเวลาไทย (UTC+7) — ฐานข้อมูลเก็บ UTC แบบไม่มี timezone
เดิมส่งค่า UTC ไปตรงๆ หน้าแอดมินแสดงเวลาช้าไป 7 ชั่วโมง (และช่วงตี 0–7 ขึ้นวันผิด)
"""
from datetime import datetime, timezone

import pytest

from app.models.models import ChatHistory
from app.utils.timeutil import thai_day_range_utc, thai_str
from tests.conftest import auth_header

pytestmark = pytest.mark.asyncio


async def test_thai_str_converts_naive_utc():
    assert thai_str(datetime(2026, 10, 29, 6, 15, 18)) == "2026-10-29 13:15:18"
    assert thai_str(datetime(2026, 10, 29, 20, 0, 0)) == "2026-10-30 03:00:00"   # ข้ามวันตามเวลาไทย
    assert thai_str(None) is None


async def test_thai_day_range():
    start, end = thai_day_range_utc(datetime(2026, 10, 29, 20, 0, tzinfo=timezone.utc))  # = 30 ต.ค. 03:00 ไทย
    assert (start, end) == (datetime(2026, 10, 29, 17, 0), datetime(2026, 10, 30, 17, 0))


async def test_history_api_returns_thai_time(client, db_session, admin_user):
    db_session.add(ChatHistory(id="h-tz", query="q", answer="a", timestamp=datetime(2026, 10, 29, 6, 15, 18)))
    await db_session.commit()
    rows = (await client.get("/api/admin/history", headers=auth_header(admin_user.username))).json()
    assert [r["timestamp"] for r in rows if r["id"] == "h-tz"] == ["2026-10-29 13:15:18"]


async def test_user_created_at_has_timezone(client, admin_user):
    users = (await client.get("/api/auth/users", headers=auth_header(admin_user.username))).json()
    assert users[0]["created_at"].endswith(("Z", "+00:00"))
