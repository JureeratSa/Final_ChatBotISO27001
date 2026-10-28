"""
Integration tests: แยกสิทธิ์ AdminWeb ตามแผนก (app/services/department_scope.py)

- แอดมินแผนกเห็น/แก้ได้เฉพาะเอกสาร แบบฟอร์ม ประวัติคำตอบ ความพึงพอใจ และคำถามที่ตอบไม่ได้
  ของแผนกตัวเอง — เรียก API ตรงๆ ก็ไม่ได้ ไม่ใช่แค่ซ่อนปุ่มใน UI
- SuperAdmin เห็นทุกแผนก เลือกดูทีละแผนกได้ และเป็นคนเดียวที่ย้ายแผนก/แก้ส่วนกลางได้
fixture: staff_user = งานสารสนเทศ, other_staff_user = งานทรัพยากรบุคคล (ดู conftest.py)
"""
import json

import pytest

import app.routers.admin_documents as admin_documents_module
from app.core.config import settings
from app.models.models import ChatHistory, Document, Feedback, Form, UnansweredQuery
from app.schemas.schemas import UnansweredSubmit
from app.services.unanswered_service import record_unanswered_query
from tests.conftest import auth_header

pytestmark = pytest.mark.asyncio

IT = "งานสารสนเทศ"
HR = "งานทรัพยากรบุคคล"


@pytest.fixture(autouse=True)
def _skip_real_index_rebuild(monkeypatch):
    monkeypatch.setattr(admin_documents_module, "_trigger_rebuild_background", lambda: None)
    monkeypatch.setattr(admin_documents_module, "_delete_from_search_index", lambda *_: None)


@pytest.fixture
async def docs(db_session):
    rows = [
        Document(filename="it_wifi.pdf", display_name="wifi", status="Active", department=IT),
        Document(filename="hr_leave.pdf", display_name="ลา", status="Active", department=HR),
        Document(filename="legacy.pdf", display_name="เดิม", status="Active", department=None),
    ]
    db_session.add_all(rows)
    await db_session.commit()
    return rows


def _names(resp):
    return sorted(d["filename"] for d in resp.json())


# ─── Documents ────────────────────────────────────────────────────────────────

async def test_department_admin_lists_only_own_documents(client, staff_user, docs):
    resp = await client.get("/api/admin/documents", headers=auth_header(staff_user.username))
    assert resp.status_code == 200
    assert _names(resp) == ["it_wifi.pdf"]


async def test_department_admin_cannot_widen_scope_with_query_param(client, staff_user, docs):
    resp = await client.get(f"/api/admin/documents?department={HR}", headers=auth_header(staff_user.username))
    assert _names(resp) == ["it_wifi.pdf"]


async def test_super_admin_lists_all_and_can_filter(client, admin_user, docs):
    h = auth_header(admin_user.username)
    assert _names(await client.get("/api/admin/documents", headers=h)) == ["hr_leave.pdf", "it_wifi.pdf", "legacy.pdf"]
    assert _names(await client.get(f"/api/admin/documents?department={HR}", headers=h)) == ["hr_leave.pdf"]
    assert _names(await client.get("/api/admin/documents?department=__unassigned__", headers=h)) == ["legacy.pdf"]


async def test_department_admin_cannot_view_other_department_text(client, staff_user, docs):
    resp = await client.get(
        "/api/admin/documents/view_raw?filename=hr_leave.pdf", headers=auth_header(staff_user.username)
    )
    assert resp.status_code == 403


async def test_upload_sets_uploader_department(client, staff_user, tmp_path, monkeypatch):
    monkeypatch.setattr(admin_documents_module, "UPLOADS_DIR", tmp_path)
    from Admin import pdf_ocr
    monkeypatch.setattr(pdf_ocr, "extract_pages", lambda *a, **k: [])

    resp = await client.post(
        "/api/admin/documents/upload",
        content=b"%PDF-1.4 test",
        headers={**auth_header(staff_user.username), "content-type": "application/pdf", "x-file-name": "new.pdf"},
    )
    assert resp.status_code == 201
    assert resp.json()["department"] == IT


async def test_upload_cannot_overwrite_other_department_file(client, staff_user, docs, tmp_path, monkeypatch):
    monkeypatch.setattr(admin_documents_module, "UPLOADS_DIR", tmp_path)
    original = tmp_path / "hr_leave.pdf"
    original.write_bytes(b"original")

    resp = await client.post(
        "/api/admin/documents/upload",
        content=b"%PDF-1.4 overwrite",
        headers={**auth_header(staff_user.username), "content-type": "application/pdf", "x-file-name": "hr_leave.pdf"},
    )
    assert resp.status_code == 403
    assert original.read_bytes() == b"original"  # ต้องปฏิเสธก่อนเขียนไฟล์ทับ


async def test_only_super_admin_moves_document_department(client, admin_user, staff_user, docs):
    payload = {"filename": "legacy.pdf", "department": HR}
    denied = await client.post("/api/admin/documents/update_department", json=payload,
                               headers=auth_header(staff_user.username))
    assert denied.status_code == 403

    ok = await client.post("/api/admin/documents/update_department", json=payload,
                           headers=auth_header(admin_user.username))
    assert ok.status_code == 200
    resp = await client.get(f"/api/admin/documents?department={HR}", headers=auth_header(admin_user.username))
    assert _names(resp) == ["hr_leave.pdf", "legacy.pdf"]


# ─── History / Feedback / Stats ────────────────────────────────────────────────

@pytest.fixture
async def history(db_session, docs):
    rows = [
        ChatHistory(id="h-it", query="wifi", answer="a", cited_docs=json.dumps(["it_wifi.pdf"]),
                    referenced_docs=json.dumps(["it_wifi.pdf", "hr_leave.pdf"])),
        ChatHistory(id="h-hr", query="ลา", answer="b", cited_docs=json.dumps(["hr_leave.pdf"]),
                    referenced_docs=json.dumps(["hr_leave.pdf", "it_wifi.pdf"])),
        # แถวเก่าก่อนมี cited_docs — กรองด้วย referenced_docs แทน
        ChatHistory(id="h-old", query="เก่า", answer="c", cited_docs=None,
                    referenced_docs=json.dumps(["it_wifi.pdf"])),
        # "itXwifi.pdf" ต้องไม่ถูกจับด้วย "it_wifi.pdf" (_ เป็น wildcard ของ LIKE ถ้าไม่ escape)
        ChatHistory(id="h-like", query="x", answer="d", cited_docs=json.dumps(["itXwifi.pdf"]),
                    referenced_docs="[]"),
    ]
    db_session.add_all(rows)
    db_session.add_all([
        Feedback(id="f-it", rating="like", history_id="h-it"),
        Feedback(id="f-hr", rating="dislike", history_id="h-hr"),
        Feedback(id="f-none", rating="like", history_id=None),
    ])
    await db_session.commit()
    return rows


async def test_department_admin_sees_only_own_history(client, staff_user, history):
    resp = await client.get("/api/admin/history", headers=auth_header(staff_user.username))
    assert sorted(h["id"] for h in resp.json()) == ["h-it", "h-old"]


async def test_history_follows_document_when_department_changes(client, admin_user, other_staff_user, history):
    await client.post("/api/admin/documents/update_department",
                      json={"filename": "it_wifi.pdf", "department": HR},
                      headers=auth_header(admin_user.username))
    resp = await client.get("/api/admin/history", headers=auth_header(other_staff_user.username))
    assert sorted(h["id"] for h in resp.json()) == ["h-hr", "h-it", "h-old"]


async def test_feedback_scoped_through_history(client, staff_user, admin_user, history):
    staff = await client.get("/api/admin/feedback", headers=auth_header(staff_user.username))
    assert [f["id"] for f in staff.json()] == ["f-it"]
    everyone = await client.get("/api/admin/feedback", headers=auth_header(admin_user.username))
    assert len(everyone.json()) == 3

    denied = await client.delete("/api/admin/feedback/f-hr", headers=auth_header(staff_user.username))
    assert denied.status_code == 404


async def test_stats_scoped_to_department(client, staff_user, history):
    stats = (await client.get("/api/admin/stats", headers=auth_header(staff_user.username))).json()
    assert stats["total_queries"] == 2
    assert stats["total_likes"] == 1
    assert stats["total_dislikes"] == 0
    assert stats["total_documents"] == 1


# ─── Unanswered ───────────────────────────────────────────────────────────────

async def test_unanswered_department_guessed_from_top_document(db_session, docs):
    await record_unanswered_query(db_session, UnansweredSubmit(query="ลาคลอดกี่วัน"), ["hr_leave.pdf", "it_wifi.pdf"])
    await record_unanswered_query(db_session, UnansweredSubmit(query="ไม่เกี่ยวกับเอกสาร"), [])
    rows = {u.query: u.department for u in (await db_session.execute(
        UnansweredQuery.__table__.select())).all()}
    assert rows == {"ลาคลอดกี่วัน": HR, "ไม่เกี่ยวกับเอกสาร": None}


async def test_unanswered_scoped_and_guarded(client, staff_user, admin_user, db_session):
    db_session.add_all([
        UnansweredQuery(id="u-it", query="q1", department=IT),
        UnansweredQuery(id="u-hr", query="q2", department=HR),
        UnansweredQuery(id="u-none", query="q3", department=None),
    ])
    await db_session.commit()

    staff = await client.get("/api/admin/unanswered", headers=auth_header(staff_user.username))
    assert [u["id"] for u in staff.json()] == ["u-it"]

    denied = await client.put("/api/admin/unanswered/u-hr", json={"status": "Resolved"},
                              headers=auth_header(staff_user.username))
    assert denied.status_code == 403

    move_denied = await client.put("/api/admin/unanswered/u-none/department", json={"department": IT},
                                   headers=auth_header(staff_user.username))
    assert move_denied.status_code == 403
    moved = await client.put("/api/admin/unanswered/u-none/department", json={"department": IT},
                             headers=auth_header(admin_user.username))
    assert moved.json()["department"] == IT


# ─── Forms ────────────────────────────────────────────────────────────────────

def _use_tmp_uploads(monkeypatch, tmp_path):
    # UPLOADS_DIR เป็น property ของ Settings (คำนวณจากตำแหน่ง repo) จึงต้องแพตช์ที่ class
    monkeypatch.setattr(type(settings), "UPLOADS_DIR", property(lambda self: str(tmp_path)))


async def test_forms_scoped_and_guarded(client, staff_user, db_session, tmp_path, monkeypatch):
    _use_tmp_uploads(monkeypatch, tmp_path)
    db_session.add_all([
        Form(id="form-it", name="แบบฟอร์ม IT", department=IT),
        Form(id="form-hr", name="แบบฟอร์มลา", department=HR),
    ])
    await db_session.commit()
    h = auth_header(staff_user.username)

    listed = await client.get("/api/admin/forms", headers=h)
    assert [f["id"] for f in listed.json()] == ["form-it"]

    assert (await client.post("/api/admin/forms/delete", json={"id": "form-hr"}, headers=h)).status_code == 403

    # อัปโหลดชื่อซ้ำกับแบบฟอร์มของแผนกอื่น = พยายามทับของคนอื่น
    overwrite = await client.post(
        "/api/admin/forms/upload", content=b"%PDF-1.4",
        headers={**h, "x-form-name": "%E0%B9%81%E0%B8%9A%E0%B8%9A%E0%B8%9F%E0%B8%AD%E0%B8%A3%E0%B9%8C%E0%B8%A1%E0%B8%A5%E0%B8%B2",
                 "x-file-name": "leave.pdf"},
    )
    assert overwrite.status_code == 403
    assert not (tmp_path / "forms").exists() or not any((tmp_path / "forms").iterdir())


async def test_forms_require_login(client):
    assert (await client.get("/api/admin/forms")).status_code in (401, 403)


async def test_new_form_gets_uploader_department(client, staff_user, tmp_path, monkeypatch, db_session):
    _use_tmp_uploads(monkeypatch, tmp_path)
    resp = await client.post(
        "/api/admin/forms/upload", content=b"%PDF-1.4",
        headers={**auth_header(staff_user.username), "x-form-name": "wifi-request", "x-file-name": "wifi.pdf"},
    )
    assert resp.status_code == 200
    listed = await client.get("/api/admin/forms", headers=auth_header(staff_user.username))
    assert [(f["name"], f["department"]) for f in listed.json()] == [("wifi-request", IT)]


# ─── Central (SuperAdmin only) ────────────────────────────────────────────────

async def test_department_admin_cannot_manage_central_features(client, staff_user):
    h = auth_header(staff_user.username)
    assert (await client.post("/api/admin/announcements", json={"title": "x"}, headers=h)).status_code == 403
    assert (await client.post("/api/admin/announcements/create", json={"title": "x"}, headers=h)).status_code == 403
    assert (await client.post("/api/admin/rebuild", headers=h)).status_code == 403
    assert (await client.post("/api/admin/settings", json={"top_k": 3}, headers=h)).status_code == 403


async def test_department_admin_can_still_add_custom_faq(client, staff_user):
    resp = await client.post("/api/admin/custom_faqs", json={"question": "ลืมรหัส wifi", "answer": "โทร 8470"},
                             headers=auth_header(staff_user.username))
    assert resp.status_code == 200
    settings_resp = await client.get("/api/admin/settings")
    assert [f["question"] for f in settings_resp.json()["custom_faqs"]] == ["ลืมรหัส wifi"]


async def test_departments_list(client, admin_user, staff_user, other_staff_user):
    everyone = await client.get("/api/auth/departments", headers=auth_header(admin_user.username))
    assert everyone.json() == sorted([IT, HR])
    own = await client.get("/api/auth/departments", headers=auth_header(staff_user.username))
    assert own.json() == [IT]
