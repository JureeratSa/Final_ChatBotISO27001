"""
Security audit 2026-10-30 — กลุ่ม C (Medium)
M1 settings ต้องล็อกอิน · M2/M3 อัปโหลดเฉพาะ PDF จริงและจำกัดขนาด · M5 จำกัด endpoint สาธารณะ
M6 แอดมินแผนกสอน FAQ ได้เฉพาะคำถามที่ตอบไม่ได้ของแผนกตัวเอง · M7 ลบเอกสารแล้วไม่เหลือ cache
M9 token ออก/ตรวจด้วย PyJWT
"""
import json

import pytest

import app.routers.admin_documents as docs_module
from app.core.config import settings
from app.models.models import UnansweredQuery
from tests.conftest import auth_header

pytestmark = pytest.mark.asyncio

PDF = b"%PDF-1.4 test"


@pytest.fixture
def tmp_uploads(tmp_path, monkeypatch):
    monkeypatch.setattr(type(settings), "UPLOADS_DIR", property(lambda self: str(tmp_path)))
    monkeypatch.setattr(docs_module, "UPLOADS_DIR", tmp_path)
    monkeypatch.setattr(docs_module, "_trigger_rebuild_background", lambda: None)
    return tmp_path


# ─── M1 ────────────────────────────────────────────────────────────────────────

async def test_admin_settings_requires_login_public_settings_minimal(client, staff_user):
    assert (await client.get("/api/admin/settings")).status_code in (401, 403)
    assert (await client.get("/api/admin/settings", headers=auth_header(staff_user.username))).status_code == 200
    public = (await client.get("/api/chat/settings")).json()
    assert set(public) == {"welcome_message", "chat_greeting", "predefined_faqs"}


# ─── M2 / M3 ───────────────────────────────────────────────────────────────────

async def test_form_upload_accepts_only_real_pdf_and_stores_relative_link(client, staff_user, tmp_uploads):
    h = {**auth_header(staff_user.username), "x-form-name": "f1"}
    assert (await client.post("/api/admin/forms/upload", content=b"<script>x</script>",
                              headers={**h, "x-file-name": "evil.html"})).status_code == 400
    assert (await client.post("/api/admin/forms/upload", content=b"<html>not pdf</html>",
                              headers={**h, "x-file-name": "fake.pdf"})).status_code == 400
    ok = await client.post("/api/admin/forms/upload", content=PDF,
                           headers={**h, "x-file-name": "real.pdf", "host": "evil.example"})
    assert ok.status_code == 200
    form = (await client.get("/api/admin/forms", headers=auth_header(staff_user.username))).json()[0]
    assert form["download_link"].startswith("/api/forms/download/")      # ไม่ผูกกับ Host header


async def test_form_upload_size_limit(client, staff_user, tmp_uploads, monkeypatch):
    monkeypatch.setattr(settings, "MAX_FORM_UPLOAD_MB", 1)
    resp = await client.post("/api/admin/forms/upload", content=PDF + b"0" * (1024 * 1024 + 1),
                             headers={**auth_header(staff_user.username), "x-form-name": "big", "x-file-name": "big.pdf"})
    assert resp.status_code == 413


async def test_document_upload_rejects_non_pdf_and_oversize(client, staff_user, tmp_uploads, monkeypatch):
    h = {**auth_header(staff_user.username), "content-type": "application/pdf"}
    resp = await client.post("/api/admin/documents/upload", content=b"MZ\x90 not a pdf",
                             headers={**h, "x-file-name": "virus.pdf"})
    assert resp.status_code == 400
    monkeypatch.setattr(settings, "MAX_DOCUMENT_UPLOAD_MB", 1)
    resp = await client.post("/api/admin/documents/upload", content=PDF + b"0" * (1024 * 1024 + 1),
                             headers={**h, "x-file-name": "big.pdf"})
    assert resp.status_code == 413
    resp = await client.post("/api/admin/documents/upload", files={"file": ("doc.pdf", b"not pdf", "application/pdf")},
                             headers=auth_header(staff_user.username))
    assert resp.status_code == 400


# ─── M5 ────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("payload", [
    {"msgId": "m1", "rating": "<script>"},
    {"msgId": "m1", "rating": "like", "stars": 99},
    {"msgId": "m1", "rating": "like", "comment": "x" * 2001},
    {"msgId": "", "rating": "like"},
])
async def test_feedback_submit_validation(client, payload):
    assert (await client.post("/api/admin/feedback/submit", json=payload)).status_code == 422


async def test_feedback_submit_rate_limited_separately_from_chat(client, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_REQUESTS", 2)
    for i in range(2):
        assert (await client.post("/api/admin/feedback/submit", json={"msgId": f"m{i}", "rating": "like"})).status_code == 201
    assert (await client.post("/api/admin/feedback/submit", json={"msgId": "m9", "rating": "like"})).status_code == 429
    # โควตาของแชทยังอยู่ครบ
    assert (await client.post("/api/chat", json={"query": "สวัสดีครับ"})).status_code == 200


async def test_unanswered_submit_length_limit(client):
    assert (await client.post("/api/admin/unanswered/submit", json={"query": "x" * 2001})).status_code == 422


# ─── M6 ────────────────────────────────────────────────────────────────────────

async def test_department_admin_faq_only_for_own_unanswered(client, db_session, staff_user, admin_user):
    db_session.add_all([
        UnansweredQuery(id="u1", query="ลืมรหัสผ่าน wifi ทำยังไง", department=staff_user.department),
        UnansweredQuery(id="u2", query="ลาคลอดได้กี่วัน", department="งานอื่น"),
    ])
    await db_session.commit()
    h = auth_header(staff_user.username)
    ok = await client.post("/api/admin/custom_faqs", json={"question": " ลืมรหัสผ่าน WIFI ทำยังไง ", "answer": "ติดต่อ 8471"}, headers=h)
    assert ok.status_code == 200
    other_dept = await client.post("/api/admin/custom_faqs", json={"question": "ลาคลอดได้กี่วัน", "answer": "x"}, headers=h)
    assert other_dept.status_code == 403
    arbitrary = await client.post("/api/admin/custom_faqs", json={"question": "เงินเดือนออกวันไหน", "answer": "x"}, headers=h)
    assert arbitrary.status_code == 403
    superadmin = await client.post("/api/admin/custom_faqs", json={"question": "เงินเดือนออกวันไหน", "answer": "x"},
                                   headers=auth_header(admin_user.username))
    assert superadmin.status_code == 200


# ─── M7 ────────────────────────────────────────────────────────────────────────

async def test_delete_leftovers_removes_cache_and_sample_chunks(tmp_path, monkeypatch):
    from app.services.rebuild_service import cache_file_prefix, delete_document_leftovers
    monkeypatch.setattr(type(settings), "UPLOADS_DIR", property(lambda self: str(tmp_path / "uploads")))
    monkeypatch.setattr(type(settings), "ADMIN_DIR", property(lambda self: str(tmp_path / "Admin")))
    cache = tmp_path / "uploads" / "cache"
    cache.mkdir(parents=True)
    gone = cache / f"{cache_file_prefix('นโยบาย ก.pdf')}local_chroma.json"
    kept = cache / f"{cache_file_prefix('อื่น.pdf')}local_chroma.json"
    gone.write_text("{}", encoding="utf-8")
    kept.write_text("{}", encoding="utf-8")
    (tmp_path / "sample_chunks.json").write_text(json.dumps([
        {"chunk_id": 1, "metadata": {"source": "นโยบาย ก.pdf"}},
        {"chunk_id": 2, "metadata": {"source": "อื่น.pdf"}},
    ], ensure_ascii=False), encoding="utf-8")

    delete_document_leftovers("นโยบาย ก.pdf")
    assert not gone.exists() and kept.exists()
    left = json.loads((tmp_path / "sample_chunks.json").read_text(encoding="utf-8"))
    assert [c["chunk_id"] for c in left] == [2]


# ─── M9 ────────────────────────────────────────────────────────────────────────

async def test_pyjwt_tokens_round_trip_and_reject_tampering():
    import jwt
    from app.core.security import create_access_token, verify_access_token
    token = create_access_token({"sub": "u1", "tv": 3})
    payload = verify_access_token(token)
    assert payload["sub"] == "u1" and payload["tv"] == 3 and payload["jti"]
    forged = jwt.encode({**payload, "sub": "admin"}, "wrong-secret", algorithm="HS256")
    with pytest.raises(ValueError):
        verify_access_token(forged)
    unsigned = jwt.encode({**payload, "sub": "admin"}, None, algorithm="none")
    with pytest.raises(ValueError):
        verify_access_token(unsigned)
