"""
GET /api/admin/documents/index_status — สถานะ "ฐานข้อมูลพร้อมใช้งาน" จริงของเอกสาร

เดิมกดอนุมัติขั้นสุดท้ายแล้วตารางขึ้น "พร้อมใช้งาน" ทันที ทั้งที่ embedding ยังรันเบื้องหลังอยู่
ตอนนี้ indexed มาจาก chunk ใน retriever ที่ใช้ตอบจริง และ pending = เอกสารที่รอ rebuild รอบใหม่
"""
import pytest

from tests.conftest import auth_header
import app.routers.admin_documents as docs_module
import app.services.rebuild_service as rebuild_service
from app.models.models import Document

pytestmark = pytest.mark.asyncio


class _FakeRetriever:
    def __init__(self, sources):
        self.bm25_chunks = [{"chunk_id": i, "metadata": {"source": s}} for i, s in enumerate(sources)]


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    monkeypatch.setattr(docs_module, "_trigger_rebuild_background", lambda: None)
    monkeypatch.setattr(rebuild_service, "_pending", {})
    monkeypatch.setattr(rebuild_service, "_progress",
                        {"running": False, "queued": 0, "percent": 0, "stage": "", "error": None})
    import app.services.rag_service as rag_service
    monkeypatch.setattr(rag_service, "get_retriever", lambda: _FakeRetriever(["ready.pdf", "other_dept.pdf"]))


async def _add_docs(db_session, department):
    db_session.add_all([
        Document(filename="ready.pdf", display_name="ready", status="Active", department=department),
        Document(filename="new.pdf", display_name="new", status="Step_Chunk_Preview", department=department),
        Document(filename="other_dept.pdf", display_name="o", status="Active", department="งานอื่น"),
    ])
    await db_session.commit()


async def test_approve_final_step_marks_document_pending(client, staff_user, db_session, monkeypatch):
    await _add_docs(db_session, staff_user.department)
    monkeypatch.setattr(docs_module, "run_approval_pipeline", lambda *a: "Active")

    resp = await client.post("/api/admin/documents/approve", headers=auth_header(staff_user.username),
                             json={"filename": "new.pdf", "current_status": "Step_Chunk_Preview"})
    assert resp.status_code == 200

    body = (await client.get("/api/admin/documents/index_status", headers=auth_header(staff_user.username))).json()
    assert "new.pdf" in body["pending"]
    assert "new.pdf" not in body["indexed"]   # สถานะ Active แล้วแต่ยังไม่อยู่ในดัชนี = ยังไม่พร้อม
    assert "ready.pdf" in body["indexed"]


async def test_progress_is_reported(client, staff_user, db_session):
    await _add_docs(db_session, staff_user.department)
    rebuild_service.mark_pending("new.pdf")
    rebuild_service._set_progress(42, "กำลังทำ embedding: new.pdf", running=True)

    body = (await client.get("/api/admin/documents/index_status", headers=auth_header(staff_user.username))).json()
    assert body["running"] is True
    assert body["percent"] == 42


async def test_rebuild_clears_pending_documents_marked_before_it_started(monkeypatch):
    rebuild_service.mark_pending("new.pdf")
    import sys, types
    fake = types.ModuleType("Admin.rebuild_db")
    calls = []

    def fake_rebuild(documents=None, progress=None):
        progress(50, "กำลังทำ embedding")
        calls.append(rebuild_service._progress["percent"])
        return {}
    fake.rebuild = fake_rebuild
    monkeypatch.setitem(sys.modules, "Admin.rebuild_db", fake)
    monkeypatch.setattr(rebuild_service, "_sync_update_rebuild_status", lambda *a, **k: None)
    monkeypatch.setattr(rebuild_service, "_sync_load_documents", lambda: [])
    monkeypatch.setattr(rebuild_service, "_sync_save_durations", lambda d: None)
    import app.services.rag_service as rag_service
    monkeypatch.setattr(rag_service, "reload_retriever", lambda: None)
    # rebuild รอบนี้เริ่มหลัง mark — เลื่อนเวลา mark ให้อยู่ก่อนเริ่มแน่นอน
    rebuild_service._pending["new.pdf"] -= 1

    rebuild_service._trigger_rebuild_background()

    assert calls == [47]                        # 50% ของ rebuild() = 47% ของทั้งหมด (โหลด retriever คือ 95–100%)
    assert rebuild_service._pending == {}
    assert rebuild_service._progress["running"] is False
    assert rebuild_service._progress["percent"] == 100


async def test_department_admin_sees_only_own_department_files(client, staff_user, db_session):
    await _add_docs(db_session, staff_user.department)
    rebuild_service.mark_pending("other_dept.pdf")

    body = (await client.get("/api/admin/documents/index_status", headers=auth_header(staff_user.username))).json()
    assert "other_dept.pdf" not in body["indexed"]
    assert "other_dept.pdf" not in body["pending"]
