"""
Integration tests: document ownership guard (_check_doc_ownership) ใน
app/services/document_service.py (ใช้งานจริงผ่าน app/routers/admin_documents.py)

เอกสารเป็นของ "แผนก" (documents.department) ไม่ใช่ของคนที่อัปโหลด — แอดมินทุกคนในแผนก
แก้ได้, แผนกอื่นแก้ไม่ได้, เอกสารที่ยังไม่ระบุแผนก (NULL) แก้ได้แค่ SuperAdmin
(เดิมเทียบ uploaded_by กับชื่อผู้ใช้ — เทส xfail เรื่องเอกสาร legacy ที่ uploaded_by=NULL
ถูกแทนด้วยกฎใหม่นี้ ดู app/services/department_scope.py)
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
    doc = Document(filename="legacy-welfare.pdf", display_name="สวัสดิการเดิม", status="Active",
                   uploaded_by=None, department=None)
    db_session.add(doc)
    await db_session.commit()
    return doc


@pytest.fixture
async def owned_document(db_session, staff_user):
    doc = Document(
        filename="staff-doc.pdf",
        display_name="เอกสารของเจ้าหน้าที่ ก",
        status="Active",
        uploaded_by="คนอื่นในแผนกเดียวกัน",
        department=staff_user.department,
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


async def test_same_department_admin_can_edit_document(client, staff_user, owned_document):
    resp = await client.put(
        f"/api/admin/documents/{owned_document.filename}",
        json={"display_name": "แก้โดยเจ้าของ"},
        headers=auth_header(staff_user.username),
    )
    assert resp.status_code == 200


async def test_other_department_admin_cannot_edit_document(client, other_staff_user, owned_document):
    resp = await client.put(
        f"/api/admin/documents/{owned_document.filename}",
        json={"display_name": "พยายามแก้ของคนอื่น"},
        headers=auth_header(other_staff_user.username),
    )
    assert resp.status_code == 403


# ─── เอกสารที่ยังไม่ระบุแผนก ─────────────────────────────────────────────────────

async def test_department_admin_cannot_edit_unassigned_document(client, staff_user, legacy_document):
    resp = await client.put(
        f"/api/admin/documents/{legacy_document.filename}",
        json={"display_name": "แก้เอกสาร legacy"},
        headers=auth_header(staff_user.username),
    )
    assert resp.status_code == 403


async def test_super_admin_can_toggle_unassigned_document(client, admin_user, legacy_document):
    resp = await client.post(
        "/api/admin/documents/toggle",
        json={"filename": legacy_document.filename, "active": False},
        headers=auth_header(admin_user.username),
    )
    assert resp.status_code == 200


async def test_edit_nonexistent_document_is_404(client, admin_user):
    resp = await client.put(
        "/api/admin/documents/does-not-exist.pdf",
        json={"display_name": "x"},
        headers=auth_header(admin_user.username),
    )
    assert resp.status_code == 404
