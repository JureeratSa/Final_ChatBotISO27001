"""
Integration tests: document ownership guard (_check_doc_ownership) ใน
app/services/document_service.py (ใช้งานจริงผ่าน app/routers/admin_documents.py)

รวมถึง regression test สำหรับบั๊กที่เจอตอน code review (2026-08-28):
เอกสาร legacy/migrated ที่ uploaded_by = NULL ถูกบล็อกไม่ให้ non-admin แก้ไขได้เลย
ทั้งที่ AdminWeb/src/App.jsx แสดงเอกสารเหล่านี้เป็นแถวปกติที่กดใช้งานได้
(ดู Backend/app/services/document_service.py:_check_doc_ownership)
"""
import pytest

from tests.conftest import auth_header
import app.routers.admin_documents as admin_module
from app.models.models import Document

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _skip_real_index_rebuild(monkeypatch):
    """ตัด background rebuild (Admin.rebuild_db.rebuild()) ออก — หนักเกินไปสำหรับ unit test"""
    monkeypatch.setattr(admin_module, "_trigger_rebuild_background", lambda: None)


@pytest.fixture
async def legacy_document(db_session):
    """เอกสารที่ migrate มาจาก JSON เดิม — ไม่มี uploaded_by (ดู main.py:migrate_from_json)"""
    doc = Document(filename="legacy-welfare.pdf", display_name="สวัสดิการเดิม", status="Active", uploaded_by=None)
    db_session.add(doc)
    await db_session.commit()
    return doc


@pytest.fixture
async def owned_document(db_session, staff_user):
    doc = Document(
        filename="staff-doc.pdf",
        display_name="เอกสารของเจ้าหน้าที่ ก",
        status="Active",
        uploaded_by=staff_user.display_name,
    )
    db_session.add(doc)
    await db_session.commit()
    return doc


# ─── Positive cases (พฤติกรรมที่ถูกต้องอยู่แล้ว) ────────────────────────────────

async def test_admin_can_edit_any_document_regardless_of_owner(client, admin_user, owned_document):
    resp = await client.put(
        f"/api/admin/documents/{owned_document.filename}",
        json={"display_name": "แก้โดยแอดมิน"},
        headers=auth_header(admin_user.username),
    )
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "แก้โดยแอดมิน"


async def test_owner_can_edit_own_document(client, staff_user, owned_document):
    resp = await client.put(
        f"/api/admin/documents/{owned_document.filename}",
        json={"display_name": "แก้โดยเจ้าของ"},
        headers=auth_header(staff_user.username),
    )
    assert resp.status_code == 200


async def test_non_owner_staff_cannot_edit_someone_elses_document(client, other_staff_user, owned_document):
    resp = await client.put(
        f"/api/admin/documents/{owned_document.filename}",
        json={"display_name": "พยายามแก้ของคนอื่น"},
        headers=auth_header(other_staff_user.username),
    )
    assert resp.status_code == 403


# ─── Regression: NULL uploaded_by locks legacy docs from every non-admin ────────

@pytest.mark.xfail(
    reason=(
        "BUG (code review 2026-08-28): _check_doc_ownership ถือว่า uploaded_by=NULL "
        "เป็น 'เอกสารของคนอื่น' เสมอ ทำให้ non-admin แก้เอกสาร legacy ไม่ได้เลย "
        "แม้ UI จะแสดงเอกสารเหล่านี้เป็นแถวที่กดใช้งานได้ปกติ — ควรถือเป็นเอกสารกลาง "
        "ที่ staff ทุกคนแก้ได้ ไม่ใช่ 403"
    ),
    strict=True,
)
async def test_non_admin_can_edit_legacy_document_with_null_uploaded_by(client, staff_user, legacy_document):
    resp = await client.put(
        f"/api/admin/documents/{legacy_document.filename}",
        json={"display_name": "แก้เอกสาร legacy"},
        headers=auth_header(staff_user.username),
    )
    assert resp.status_code == 200


@pytest.mark.xfail(
    reason="เหมือนกับ PUT /documents/{filename} — toggle ก็โดนบล็อกเอกสาร legacy เช่นกัน",
    strict=True,
)
async def test_non_admin_can_toggle_legacy_document_with_null_uploaded_by(client, staff_user, legacy_document):
    resp = await client.post(
        "/api/admin/documents/toggle",
        json={"filename": legacy_document.filename, "active": False},
        headers=auth_header(staff_user.username),
    )
    assert resp.status_code == 200


async def test_edit_nonexistent_document_is_404(client, admin_user):
    resp = await client.put(
        "/api/admin/documents/does-not-exist.pdf",
        json={"display_name": "x"},
        headers=auth_header(admin_user.username),
    )
    assert resp.status_code == 404
