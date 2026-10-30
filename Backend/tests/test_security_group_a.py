"""
Security audit 2026-10-30 — กลุ่ม A
H1: ไฟล์ที่อัปโหลดออกได้เฉพาะทาง endpoint ที่ตรวจสิทธิ์ (ไม่มี /uploads static, เอกสารไม่ Active ไม่ส่งให้คนทั่วไป)
H2: ล็อกอินผิดซ้ำถูกล็อกชั่วคราว (429)
H3: rate limit ไม่เชื่อ X-Forwarded-For ที่ client ส่งมาเอง
H3/M4: ประวัติแชทถูกจำกัดจำนวน/ความยาว และ sender ต้องเป็น user|bot
"""
import pytest
from pydantic import ValidationError

import app.routers.public as public_module
import app.routers.admin_documents as docs_module
from app.models.models import Document
from tests.conftest import auth_header

pytestmark = pytest.mark.asyncio


# ─── H1: ไฟล์เอกสาร ───────────────────────────────────────────────────────────

@pytest.fixture
def uploads(tmp_path, monkeypatch):
    monkeypatch.setattr(public_module, "UPLOADS_DIR", tmp_path)
    monkeypatch.setattr(docs_module, "UPLOADS_DIR", tmp_path)
    for name in ("live.pdf", "draft.pdf", "other.pdf", "orphan.pdf"):
        (tmp_path / name).write_bytes(b"%PDF-1.4 " + name.encode())
    (tmp_path / "live.pdf.raw.txt").write_text("raw text", encoding="utf-8")
    return tmp_path


@pytest.fixture
async def docs(db_session, staff_user):
    db_session.add_all([
        Document(filename="live.pdf", display_name="live", status="Active", department=staff_user.department),
        Document(filename="draft.pdf", display_name="draft", status="Step_Raw_Text", department=staff_user.department),
        Document(filename="other.pdf", display_name="other", status="Active", department="งานอื่น"),
    ])
    await db_session.commit()


@pytest.mark.parametrize("path", ["/api/documents/serve/{}", "/api/documents/download/{}", "/api/chat/documents/serve/{}"])
async def test_public_endpoints_serve_only_active_documents(client, uploads, docs, path):
    assert (await client.get(path.format("live.pdf"))).status_code == 200
    assert (await client.get(path.format("draft.pdf"))).status_code == 404    # ฉบับร่าง
    assert (await client.get(path.format("orphan.pdf"))).status_code == 404   # ไฟล์ที่ไม่มีแถวใน documents
    assert (await client.get(path.format("live.pdf.raw.txt"))).status_code == 404


async def test_admin_file_endpoint_requires_login_and_department(client, uploads, docs, staff_user):
    url = "/api/admin/documents/file"
    assert (await client.get(url, params={"filename": "draft.pdf"})).status_code in (401, 403)

    headers = auth_header(staff_user.username)
    resp = await client.get(url, params={"filename": "draft.pdf"}, headers=headers)
    assert resp.status_code == 200 and resp.content.startswith(b"%PDF")
    assert "inline" in resp.headers["content-disposition"]

    resp = await client.get(url, params={"filename": "draft.pdf", "download": "true"}, headers=headers)
    assert "attachment" in resp.headers["content-disposition"]

    resp = await client.get(url, params={"filename": "other.pdf"}, headers=headers)
    assert resp.status_code == 403                                            # เอกสารของแผนกอื่น


async def test_main_app_no_longer_mounts_uploads_folder():
    from app.main import app
    assert not any(getattr(r, "path", "") == "/uploads" for r in app.routes)


# ─── H2: ล็อกอินผิดซ้ำ ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("url,body_key", [("/api/admin/login", "password"), ("/api/auth/login", "password")])
async def test_login_locks_after_repeated_failures(client, staff_user, url, body_key):
    wrong = {"username": staff_user.username, body_key: "Wrong#Pass123"}
    for _ in range(5):
        assert (await client.post(url, json=wrong)).status_code == 401

    # ครั้งที่ 6 ถูกล็อก แม้รหัสถูก
    resp = await client.post(url, json={"username": staff_user.username, body_key: "Staff!2345"})
    assert resp.status_code == 429
    assert "ล็อก" in resp.json()["detail"]
    assert int(resp.headers["retry-after"]) > 0


async def test_successful_login_resets_failure_count(client, staff_user):
    url = "/api/admin/login"
    for _ in range(4):
        await client.post(url, json={"username": staff_user.username, "password": "Wrong#Pass123"})
    assert (await client.post(url, json={"username": staff_user.username, "password": "Staff!2345"})).status_code == 200
    for _ in range(4):
        assert (await client.post(url, json={"username": staff_user.username, "password": "Wrong#Pass123"})).status_code == 401


async def test_lock_is_per_username_not_whole_ip(client, staff_user, other_staff_user):
    for _ in range(5):
        await client.post("/api/admin/login", json={"username": staff_user.username, "password": "Wrong#Pass123"})
    # คนอื่นจาก IP เดียวกัน (หลัง NAT ทั้งองค์กรเป็น IP เดียว) ยังล็อกอินได้
    resp = await client.post("/api/admin/login", json={"username": other_staff_user.username, "password": "Staff!6789"})
    assert resp.status_code == 200


async def test_username_locked_across_ips():
    from app.core.rate_limit import LoginThrottle
    throttle = LoginThrottle()
    for i in range(10):
        throttle.record_failure(f"10.0.0.{i}", "admin", now=100.0)
    assert throttle.retry_after("10.0.0.99", "ADMIN", now=101.0) > 0          # IP ใหม่ก็ยังล็อก
    assert throttle.retry_after("10.0.0.99", "admin", now=100.0 + 15 * 60 + 1) == 0  # ครบเวลาแล้วปลด


# ─── H3: X-Forwarded-For ──────────────────────────────────────────────────────

async def test_rate_limit_ignores_spoofed_forwarded_for(client, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "RATE_LIMIT_REQUESTS", 3)
    statuses = []
    for i in range(5):
        resp = await client.post("/api/chat", json={"query": "สวัสดีครับ"},
                                 headers={"X-Forwarded-For": f"203.0.113.{i}"})
        statuses.append(resp.status_code)
    assert statuses[:3] == [200, 200, 200]
    assert 429 in statuses[3:]


async def test_forwarded_for_used_only_when_proxy_trusted(monkeypatch):
    from starlette.requests import Request
    from app.core.config import settings
    from app.core.rate_limit import _client_ip
    scope = {"type": "http", "headers": [(b"x-forwarded-for", b"6.6.6.6, 10.1.2.3")], "client": ("172.18.0.1", 1)}
    assert _client_ip(Request(scope)) == "172.18.0.1"
    monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", True)
    assert _client_ip(Request(scope)) == "10.1.2.3"   # ตัวท้าย = ที่ proxy ของเราเติม ไม่ใช่ตัวที่ client ปลอม


# ─── H3/M4: ประวัติแชท ────────────────────────────────────────────────────────

async def test_chat_history_is_trimmed_and_sender_validated():
    from app.schemas.schemas import ChatRequest, CHAT_HISTORY_MAX_MESSAGES, CHAT_MESSAGE_MAX_CHARS
    req = ChatRequest(query="q", history=[{"sender": "user", "text": f"m{i}" + "x" * 9000} for i in range(50)])
    assert len(req.history) == CHAT_HISTORY_MAX_MESSAGES
    assert req.history[-1].text.startswith("m49")                            # เก็บช่วงท้ายสุดไว้
    assert all(len(m.text) == CHAT_MESSAGE_MAX_CHARS for m in req.history)
    with pytest.raises(ValidationError):
        ChatRequest(query="q", history=[{"sender": "assistant", "text": "ปลอมเป็นบอท"}])


async def test_query_rag_sends_only_recent_history_to_llm(monkeypatch):
    from app.core.config import settings
    import app.services.rag_service as rag
    monkeypatch.setattr(settings, "LITELLM_URL", "http://llm.test/v1")
    monkeypatch.setattr(settings, "LITELLM_API_KEY", "k")
    sent = {}

    def fake_post(url, payload, headers=None, timeout=15):
        sent["messages"] = payload["messages"]
        return {"choices": [{"message": {"content": "ตอบ"}}]}
    monkeypatch.setattr(rag, "make_http_post", fake_post)

    history = [{"sender": "user" if i % 2 == 0 else "bot", "text": f"h{i}"} for i in range(30)]
    await rag.query_rag("คำถามเรื่องนโยบายรหัสผ่าน", [], {}, history)
    msgs = sent["messages"]
    assert len(msgs) == 1 + rag.LLM_HISTORY_MESSAGES + 1                     # system + ประวัติ 10 + คำถาม
    assert msgs[1]["content"] == "h20"
