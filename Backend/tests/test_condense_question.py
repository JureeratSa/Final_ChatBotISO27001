"""
Unit tests: rag_service.condense_question
เติมหัวข้อให้คำถามต่อเนื่องสั้นๆ ("มีแนะนำมั้ย") จากประวัติแชทก่อนค้นเอกสาร — mock HTTP ทั้งหมด
"""
import pytest

from app.services import rag_service

CFG = {"gemini_api_key": "test-key", "model_name": "test-model"}
HISTORY = [
    {"sender": "user", "text": "ตั้งรหัสผ่านอย่างไร"},
    {"sender": "bot", "text": "ต้องยาวอย่างน้อย 8 ตัวอักษรครับ"},
]


def _fake_llm(reply=None, error=None, calls=None):
    def fake(url, payload, headers, timeout):
        if calls is not None:
            calls.append(payload)
        if error:
            raise error
        return {"choices": [{"message": {"content": reply}}]}
    return fake


@pytest.mark.asyncio
async def test_rewrites_ambiguous_follow_up(monkeypatch):
    calls = []
    monkeypatch.setattr(rag_service, "make_http_post", _fake_llm("มีคำแนะนำการตั้งรหัสผ่านมั้ย", calls=calls))
    out = await rag_service.condense_question("มีแนะนำมั้ย", HISTORY, CFG)
    assert out == "มีคำแนะนำการตั้งรหัสผ่านมั้ย"
    # ประวัติแชทต้องถูกส่งไปให้ LLM ใช้เติมบริบท
    assert "ตั้งรหัสผ่านอย่างไร" in calls[0]["messages"][1]["content"]


@pytest.mark.asyncio
async def test_no_history_skips_llm(monkeypatch):
    calls = []
    monkeypatch.setattr(rag_service, "make_http_post", _fake_llm("x", calls=calls))
    assert await rag_service.condense_question("นโยบายสำรองข้อมูล", [], CFG) == "นโยบายสำรองข้อมูล"
    assert calls == []


@pytest.mark.asyncio
async def test_llm_error_falls_back_to_original(monkeypatch):
    monkeypatch.setattr(rag_service, "make_http_post", _fake_llm(error=TimeoutError("slow")))
    assert await rag_service.condense_question("มีแนะนำมั้ย", HISTORY, CFG) == "มีแนะนำมั้ย"


@pytest.mark.asyncio
async def test_strips_quotes_and_keeps_first_line(monkeypatch):
    monkeypatch.setattr(rag_service, "make_http_post", _fake_llm('"มีคำแนะนำการตั้งรหัสผ่านมั้ย"\nคำอธิบายเพิ่ม'))
    assert await rag_service.condense_question("มีแนะนำมั้ย", HISTORY, CFG) == "มีคำแนะนำการตั้งรหัสผ่านมั้ย"


@pytest.mark.asyncio
async def test_empty_or_runaway_output_falls_back(monkeypatch):
    monkeypatch.setattr(rag_service, "make_http_post", _fake_llm(""))
    assert await rag_service.condense_question("มีแนะนำมั้ย", HISTORY, CFG) == "มีแนะนำมั้ย"
    monkeypatch.setattr(rag_service, "make_http_post", _fake_llm("ก" * 400))
    assert await rag_service.condense_question("มีแนะนำมั้ย", HISTORY, CFG) == "มีแนะนำมั้ย"
