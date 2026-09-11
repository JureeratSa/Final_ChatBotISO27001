"""
Integration tests: app/routers/public.py
(health check, ดาวน์โหลดไฟล์, และ legacy compatibility endpoints ที่ UserWeb ใช้งานจริง —
เดิม endpoint พวกนี้ประกาศตรงบน `app` object ใน main.py เลย ไม่เคยมีเทสคลุมเพราะ test harness
mount เฉพาะ auth/chat/admin router เท่านั้น — ย้ายมาเป็น router แล้วเทสได้ตามปกติ)
"""
import pytest

from app.models.models import Announcement

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
