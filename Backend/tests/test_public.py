"""
Integration tests: app/routers/public.py
(health check, ดาวน์โหลดไฟล์, และ legacy compatibility endpoints ที่ UserWeb ใช้งานจริง —
เดิม endpoint พวกนี้ประกาศตรงบน `app` object ใน main.py เลย ไม่เคยมีเทสคลุมเพราะ test harness
mount เฉพาะ auth/chat/admin router เท่านั้น — ย้ายมาเป็น router แล้วเทสได้ตามปกติ)
"""
import pytest

import app.services.rag_service as rag_service_module
from app.models.models import Announcement, Document

pytestmark = pytest.mark.asyncio


async def test_health_check(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"


async def test_compatibility_search_chitchat(client):
    resp = await client.post("/api/search", json={"query": "สวัสดีครับ"})
    assert resp.status_code == 200
    assert "answer" in resp.json()


async def test_compatibility_search_empty_query(client):
    resp = await client.post("/api/search", json={"query": "   "})
    assert resp.status_code == 200
    assert resp.json()["answer"] == "กรุณาพิมพ์คำถาม"


# ─── Citations on /api/search (UserWeb เรียก endpoint นี้จริง — ต้องมี citations
# ให้ผู้ใช้กดเปิด PDF ไปหน้าที่ตรงได้ เหมือนที่ /api/chat มีอยู่แล้ว) ──────────────

class _StubRetriever:
    def query(self, query, top_k=3):
        return [
            {
                "chunk_id": 1,
                "content": "ติดต่อ ISO ที่เบอร์ 8470",
                "metadata": {"source": "iso27001.pdf", "page": 5},
            }
        ]


async def test_compatibility_search_returns_citations_for_rag_answer(client, db_session, monkeypatch):
    """เคสหลักที่ผู้ใช้รายงาน: ตอบจากเอกสารจริงแต่ไม่มีลิงก์อ้างอิงแนบมา — ต้องมี citations แล้ว
    แม้ LLM จะลืมใส่ tag [USE_RAG] ก็ตาม (used_rag=False) เพราะเราไม่ยึด tag นั้นอีกต่อไป"""
    monkeypatch.setattr(rag_service_module, "get_retriever", lambda: _StubRetriever())

    async def _fake_query_rag(query, results, config, history, forms=None):
        # จำลองเคส LLM ลืมใส่ [USE_RAG] ทั้งที่ตอบจาก context จริง
        return ("ติดต่อ ISO ได้ที่เบอร์ 8470 ครับ", False, "mocked-llm")

    monkeypatch.setattr(rag_service_module, "query_rag", _fake_query_rag)

    db_session.add(Document(filename="iso27001.pdf", display_name="คู่มือ ISO 27001"))
    await db_session.commit()

    resp = await client.post("/api/search", json={"query": "ISO 27001 ติดต่อใคร"})
    assert resp.status_code == 200
    body = resp.json()

    assert "citations" in body
    assert len(body["citations"]) == 1
    assert body["citations"][0]["source"] == "iso27001.pdf"
    assert body["citations"][0]["display_name"] == "คู่มือ ISO 27001"
    assert body["citations"][0]["pages"] == [5]
    assert body["citations"][0]["url"] == "/api/documents/serve/iso27001.pdf#page=5"


async def test_compatibility_search_omits_citations_when_answer_is_unanswered(client, db_session, monkeypatch):
    """ถ้าบอทตอบแบบ 'ไม่พบข้อมูล' ต้องไม่แนบ citations แม้ retriever จะคืนผลลัพธ์มาก็ตาม
    เพราะบอทไม่ได้ใช้ข้อมูลนั้นจริงในการตอบ"""
    monkeypatch.setattr(rag_service_module, "get_retriever", lambda: _StubRetriever())

    async def _fake_query_rag(query, results, config, history, forms=None):
        return ("ขออภัยครับ ไม่พบข้อมูลที่เกี่ยวข้องในระบบ", False, "mocked-llm")

    monkeypatch.setattr(rag_service_module, "query_rag", _fake_query_rag)

    resp = await client.post("/api/search", json={"query": "คำถามที่ไม่มีในระบบ"})
    assert resp.status_code == 200
    assert resp.json()["citations"] == []


async def test_compatibility_search_no_citations_when_no_rag_results(client):
    """คำทักทาย/หยาบคาย ไม่มี rag_results เลย — citations ต้องเป็น list ว่าง ไม่ error"""
    resp = await client.post("/api/search", json={"query": "สวัสดีครับ"})
    assert resp.status_code == 200
    assert resp.json()["citations"] == []


async def test_compatibility_ip_returns_something(client):
    resp = await client.get("/api/ip")
    assert resp.status_code == 200
    assert "ip" in resp.json()


async def test_compatibility_active_announcements_filters_by_date(client, db_session):
    db_session.add(Announcement(title="ประกาศเก่ามาก", start_date="2000-01-01", end_date="2000-01-02"))
    db_session.add(Announcement(title="ประกาศตลอดกาล", start_date="2000-01-01", end_date="2100-01-01"))
    await db_session.commit()

    resp = await client.get("/api/announcements/active")
    assert resp.status_code == 200
    titles = [a["title"] for a in resp.json()]
    assert "ประกาศตลอดกาล" in titles
    assert "ประกาศเก่ามาก" not in titles


async def test_serve_pdf_blocks_path_traversal(client, tmp_path, monkeypatch):
    import app.routers.public as public_module
    monkeypatch.setattr(public_module, "UPLOADS_DIR", tmp_path)

    resp = await client.get(r"/api/documents/serve/..\..\windows\win.ini")
    assert resp.status_code == 400


async def test_download_pdf_returns_existing_file_as_attachment(client, tmp_path, monkeypatch):
    import app.routers.public as public_module
    monkeypatch.setattr(public_module, "UPLOADS_DIR", tmp_path)
    (tmp_path / "welfare.pdf").write_bytes(b"%PDF-1.4 fake content")

    resp = await client.get("/api/documents/download/welfare.pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert "welfare.pdf" in resp.headers.get("content-disposition", "")


async def test_download_pdf_404_for_missing_file(client, tmp_path, monkeypatch):
    import app.routers.public as public_module
    monkeypatch.setattr(public_module, "UPLOADS_DIR", tmp_path)

    resp = await client.get("/api/documents/download/missing.pdf")
    assert resp.status_code == 404
