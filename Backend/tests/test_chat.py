"""
Integration tests: POST /api/chat, GET /api/chat/settings, GET /api/chat/documents/serve/{filename}
Mock เฉพาะจุดที่ต้องออกอินเทอร์เน็ตจริง (RAG retriever / LLM call ผ่าน query_rag)
เพื่อให้เทสรันได้แบบ deterministic โดยไม่ต้องมี API key หรือ index_db จริง
"""
import json

import pytest
from sqlalchemy import select

import app.routers.chat as chat_module
from app.models.models import SystemSettings, UnansweredQuery, Form as FormModel, Document

pytestmark = pytest.mark.asyncio


# ─── Basic validation ───────────────────────────────────────────────────────────

async def test_chat_rejects_empty_query(client):
    resp = await client.post("/api/chat", json={"query": "   "})
    assert resp.status_code == 400


# ─── Non-RAG shortcuts (ไม่แตะเครือข่าย) ────────────────────────────────────────

async def test_chat_greets_back_on_chitchat(client):
    resp = await client.post("/api/chat", json={"query": "สวัสดีครับ"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["used_rag"] is False
    assert body["model"] == "chit_chat"


async def test_chat_declines_profanity(client):
    resp = await client.post("/api/chat", json={"query": "มึงโง่มาก"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["used_rag"] is False
    assert body["model"] == "profanity_filter"


async def test_profanity_filtered_query_is_not_logged_as_unanswered(client, db_session):
    """
    Regression test: เดิม is_unanswered เดาจาก keyword "ขออภัย"/"ไม่สามารถตอบได้" ในคำตอบ
    ซึ่งชนกับข้อความปฏิเสธคำหยาบคาย ("ขออภัยครับ ไม่สามารถตอบคำถามที่ใช้ภาษาไม่สุภาพได้")
    ทำให้คำถามหยาบคายทุกคำถูกบันทึกลง unanswered log ผิดๆ ทั้งที่ระบบทำงานถูกต้องแล้ว
    """
    resp = await client.post("/api/chat", json={"query": "มึงโง่มาก"})
    assert resp.status_code == 200

    result = await db_session.execute(
        select(UnansweredQuery).where(UnansweredQuery.query == "มึงโง่มาก")
    )
    assert result.scalar_one_or_none() is None


async def test_chat_custom_faq_short_circuits_rag(client, db_session):
    faqs = [{"question": "เวลาทำการ", "answer": "โรงพยาบาลเปิดทุกวัน 24 ชั่วโมงครับ"}]
    db_session.add(SystemSettings(id="config", custom_faqs=json.dumps(faqs, ensure_ascii=False)))
    await db_session.commit()

    resp = await client.post("/api/chat", json={"query": "เวลาทำการเปิดกี่โมง"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["model"] == "custom_faq"
    assert body["used_rag"] is False
    assert body["answer"] == "โรงพยาบาลเปิดทุกวัน 24 ชั่วโมงครับ"


# ─── RAG path (mocked retriever + query_rag) ────────────────────────────────────

class _StubRetriever:
    def query(self, query, top_k=3):
        return [
            {
                "chunk_id": 1,
                "content": "สิทธิลาคลอดสามารถลาได้ 98 วัน",
                "metadata": {"source": "welfare.pdf", "page": 3},
            }
        ]


async def test_chat_rag_path_returns_citations_and_form_links(client, db_session, monkeypatch):
    monkeypatch.setattr(chat_module, "get_retriever", lambda: _StubRetriever())

    async def _fake_query_rag(query, results, config, history, forms=None):
        return ("สิทธิลาคลอด 98 วัน ดูแบบฟอร์มลาคลอด", True, "mocked-llm")

    monkeypatch.setattr(chat_module, "query_rag", _fake_query_rag)

    db_session.add(FormModel(id="form-1", name="แบบฟอร์มลาคลอด", download_link="/forms/leave.pdf"))
    db_session.add(Document(filename="welfare.pdf", display_name="คู่มือสวัสดิการ"))
    await db_session.commit()

    resp = await client.post("/api/chat", json={"query": "สิทธิลาคลอดกี่วัน"})
    assert resp.status_code == 200
    body = resp.json()

    assert body["used_rag"] is True
    assert body["model"] == "mocked-llm"
    assert len(body["citations"]) == 1
    assert body["citations"][0]["source"] == "welfare.pdf"
    assert body["citations"][0]["display_name"] == "คู่มือสวัสดิการ"
    assert body["citations"][0]["pages"] == [3]
    assert len(body["form_links"]) == 1
    assert body["form_links"][0]["name"] == "แบบฟอร์มลาคลอด"


async def test_chat_logs_unanswered_query_when_answer_says_no_data(client, db_session, monkeypatch):
    monkeypatch.setattr(chat_module, "get_retriever", lambda: None)

    async def _fake_query_rag(query, results, config, history, forms=None):
        return ("ขออภัยครับ ไม่พบข้อมูลที่เกี่ยวข้องในระบบ", False, "mocked-llm")

    monkeypatch.setattr(chat_module, "query_rag", _fake_query_rag)

    resp = await client.post("/api/chat", json={"query": "คำถามที่ไม่มีในระบบแน่ๆ"})
    assert resp.status_code == 200

    result = await db_session.execute(
        select(UnansweredQuery).where(UnansweredQuery.query == "คำถามที่ไม่มีในระบบแน่ๆ")
    )
    row = result.scalar_one_or_none()
    assert row is not None
    assert row.count == 1


# ─── Public settings ─────────────────────────────────────────────────────────────

async def test_public_settings_defaults_when_no_config_row(client):
    resp = await client.get("/api/chat/settings")
    assert resp.status_code == 200
    body = resp.json()
    assert body["welcome_message"] is None
    assert body["predefined_faqs"] == []


async def test_public_settings_returns_stored_values(client, db_session):
    db_session.add(SystemSettings(id="config", welcome_message="ยินดีต้อนรับ"))
    await db_session.commit()

    resp = await client.get("/api/chat/settings")
    assert resp.status_code == 200
    assert resp.json()["welcome_message"] == "ยินดีต้อนรับ"


# ─── Serve PDF — Path Traversal protection (CWE-22) ─────────────────────────────

async def test_serve_pdf_blocks_traversal_filename(client, tmp_path, monkeypatch):
    monkeypatch.setattr(chat_module, "UPLOADS_DIR", tmp_path)

    resp = await client.get(r"/api/chat/documents/serve/..\..\windows\win.ini")
    assert resp.status_code == 400


async def test_serve_pdf_returns_404_for_missing_file(client, tmp_path, monkeypatch):
    monkeypatch.setattr(chat_module, "UPLOADS_DIR", tmp_path)

    resp = await client.get("/api/chat/documents/serve/missing.pdf")
    assert resp.status_code == 404


async def test_serve_pdf_returns_existing_file(client, tmp_path, monkeypatch):
    monkeypatch.setattr(chat_module, "UPLOADS_DIR", tmp_path)
    (tmp_path / "welfare.pdf").write_bytes(b"%PDF-1.4 fake content")

    resp = await client.get("/api/chat/documents/serve/welfare.pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
