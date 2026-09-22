"""
Integration Test — Chat History Persistence via Background Task (IT-09)
save_history() ใน chat.py เปิด AsyncSessionLocal() ของตัวเองใหม่ (ไม่ใช้ session ที่มากับ
request ผ่าน Depends(get_db)) เพราะรันเป็น BackgroundTask หลัง response ถูกส่งไปแล้ว —
เทสที่มีอยู่เดิม (test_chat.py/test_rate_limit.py) เช็คแค่ HTTP response ไม่เคยพิสูจน์ว่าแถวจริง
ถูกเขียนลงตาราง history ผ่านกลไก AsyncSessionLocal ที่ conftest.py monkeypatch ไว้ — เคสนี้เช็ค
ตรงจุดนั้นโดยเฉพาะ (ยืนยันว่า session_maker/monkeypatch wiring ใช้ได้จริงกับ background task)
"""
import pytest
from sqlalchemy import select

from app.models.models import ChatHistory
from tests.conftest import auth_header

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    from app.core import rate_limit as rate_limit_module
    rate_limit_module._hits.clear()  # กันเทสอื่นก่อนหน้านี้ทิ้ง state ไว้ (module-level dict)


# ─── IT-09: แชทผ่าน custom FAQ -> ตรวจแถวจริงในตาราง history ────────────────────

async def test_IT09_chat_via_custom_faq_persists_history_row(client, admin_user, db_session):
    await client.post(
        "/api/admin/settings",
        headers=auth_header(admin_user.username),
        json={"custom_faqs": [{"question": "เวลาทำการ", "answer": "08:00-16:00 น."}]},
    )

    chat_resp = await client.post("/api/chat", json={"query": "เวลาทำการ"})
    assert chat_resp.status_code == 200
    history_id = chat_resp.json()["history_id"]

    result = await db_session.execute(select(ChatHistory).where(ChatHistory.id == history_id))
    row = result.scalar_one_or_none()
    assert row is not None
    assert row.query == "เวลาทำการ"
    assert row.answer == "08:00-16:00 น."
    assert row.api_model == "custom_faq"


async def test_IT09_chitchat_message_also_persists_history_row(client, db_session):
    chat_resp = await client.post("/api/chat", json={"query": "สวัสดีครับ"})
    assert chat_resp.status_code == 200
    history_id = chat_resp.json()["history_id"]

    result = await db_session.execute(select(ChatHistory).where(ChatHistory.id == history_id))
    row = result.scalar_one_or_none()
    assert row is not None
    assert row.query == "สวัสดีครับ"
