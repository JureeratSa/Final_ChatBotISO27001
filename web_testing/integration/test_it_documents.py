"""
Integration Test — Documents (IT-01, IT-02)
อ้างอิง: web_testing/README.md T3 (ชั้น Integration) — ยิง endpoint จริงผ่าน httpx.AsyncClient
เข้า FastAPI app + SQLite in-memory (เหมือน Backend/tests/*)

IT-02 (ลบเอกสาร) — เดิมการลบเชื่อมกับ ChromaDB ผ่านการสั่ง rebuild ทั้ง collection ใหม่เท่านั้น
(อ่านสถานะจากไฟล์ JSON legacy ที่แยกจาก DB จริง) ได้รับอนุญาตให้แก้ไขแล้ว (2026-09-21) — เพิ่ม
Admin.emb.delete_document_from_index() ลบ chunk เฉพาะไฟล์ที่ถูกลบออกจาก BM25 + ChromaDB ทันที
โดยตรง (ดู docstring ของฟังก์ชันนั้นสำหรับเหตุผลเต็ม)

**คำเตือนสำคัญ**: เครื่องนี้มี ChromaDB/BM25 ของจริงอยู่ 2 ชุด (ชุดที่ตั้งใน
CHROMA_DB_DIR ของ Backend/.env ซึ่ง HybridRetriever ใช้จริง กับ "<repo>/index_db/"
ที่เป็น default เวลาไม่ระบุ index_dir) ทั้งสองมีข้อมูลจริงอยู่ — เทสในไฟล์นี้จึง "mock" ฟังก์ชัน
delete_document_from_index() ทิ้งไปเลยตอนเทสผ่าน HTTP endpoint (กัน background task ไปแตะข้อมูล
จริงโดยไม่ตั้งใจ) แล้วแยกไปเทส delete_document_from_index() ตรงๆ ด้วย index_dir/chroma_dir ที่ชี้
ไปที่ tmp_path เท่านั้น เพื่อพิสูจน์ว่าฟังก์ชันทำงานถูกต้องจริงโดยไม่แตะข้อมูลจริงเลย
"""
import pytest

import app.routers.admin_documents as admin_module
import Admin.emb as emb_module
from app.models.models import Document
from tests.conftest import auth_header

pytestmark = pytest.mark.asyncio


@pytest.fixture
def _spy_delete_from_index(monkeypatch):
    """แทนที่ Admin.emb.delete_document_from_index ด้วย spy (บันทึก filename ที่ถูกเรียก) —
    กันไม่ให้ background task ไปแตะ ChromaDB/BM25 ของจริงบนเครื่องนี้โดยไม่ตั้งใจระหว่างเทส HTTP
    endpoint (ดูเหตุผลเต็มด้านบนของไฟล์) ความถูกต้องของฟังก์ชันเองเทสแยกต่างหากใน
    test_IT02_delete_document_from_index_removes_matching_chunks_only ด้านล่าง (ไม่ autouse
    เพราะเทสนั้นต้องเรียกฟังก์ชันจริง ไม่ใช่ spy)"""
    calls = []

    def _spy(filename, index_dir=None, chroma_dir=None, retriever=None):
        calls.append(filename)
        return 0

    monkeypatch.setattr(emb_module, "delete_document_from_index", _spy)
    return calls


# ─── IT-01: อัปโหลดเอกสารสร้างแถวในตาราง documents ──────────────────────────────

async def test_IT01_upload_creates_document_row(client, admin_user, tmp_path, monkeypatch):
    monkeypatch.setattr(admin_module, "UPLOADS_DIR", tmp_path)

    resp = await client.post(
        "/api/admin/documents/upload",
        headers=auth_header(admin_user.username),
        files={"file": ("policy.pdf", b"%PDF-1.4 fake minimal content", "application/pdf")},
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["filename"] == "policy.pdf"
    assert body["status"] == "Step_Raw_Text"
    assert body["uploaded_by"] == admin_user.display_name
    assert (tmp_path / "policy.pdf").exists()
    assert (tmp_path / "policy.pdf.raw.txt").exists()


async def test_IT01_upload_rejects_non_pdf_filename(client, admin_user, tmp_path, monkeypatch):
    monkeypatch.setattr(admin_module, "UPLOADS_DIR", tmp_path)

    resp = await client.post(
        "/api/admin/documents/upload",
        headers=auth_header(admin_user.username),
        files={"file": ("policy.txt", b"not a pdf", "text/plain")},
    )
    assert resp.status_code == 400


async def test_IT01_upload_requires_auth(client, tmp_path, monkeypatch):
    monkeypatch.setattr(admin_module, "UPLOADS_DIR", tmp_path)
    resp = await client.post(
        "/api/admin/documents/upload",
        files={"file": ("policy.pdf", b"%PDF-1.4 x", "application/pdf")},
    )
    assert resp.status_code in (401, 403)


# ─── IT-02: ลบเอกสารเคลียร์ SQL + ไฟล์ + ลบออกจากดัชนีค้นหาจริง ──────────────────

async def test_IT02_delete_removes_sql_row_and_files_and_triggers_index_deletion(
    client, admin_user, db_session, tmp_path, monkeypatch, _spy_delete_from_index
):
    monkeypatch.setattr(admin_module, "UPLOADS_DIR", tmp_path)
    (tmp_path / "annual_report.pdf").write_bytes(b"%PDF-1.4 x")
    (tmp_path / "annual_report.pdf.raw.txt").write_text("raw")

    doc = Document(filename="annual_report.pdf", display_name="รายงานประจำปี", status="Active",
                    uploaded_by=admin_user.display_name)
    db_session.add(doc)
    await db_session.commit()

    resp = await client.delete("/api/admin/documents/annual_report.pdf", headers=auth_header(admin_user.username))
    assert resp.status_code == 204

    # ไฟล์ต้นฉบับ + ไฟล์ประกอบต้องถูกลบออกจากดิสก์
    assert not (tmp_path / "annual_report.pdf").exists()
    assert not (tmp_path / "annual_report.pdf.raw.txt").exists()

    # แถวในตาราง documents ต้องหายไป
    list_resp = await client.get("/api/admin/documents", headers=auth_header(admin_user.username))
    filenames = [d["filename"] for d in list_resp.json()]
    assert "annual_report.pdf" not in filenames

    # ต้องสั่งลบออกจากดัชนีค้นหาจริง (ผ่าน spy กันแตะข้อมูลจริงบนเครื่อง — ดูฟังก์ชันจริงด้านล่าง)
    assert _spy_delete_from_index == ["annual_report.pdf"]


async def test_IT02_delete_nonexistent_document_returns_404(client, admin_user):
    resp = await client.delete("/api/admin/documents/does-not-exist.pdf", headers=auth_header(admin_user.username))
    assert resp.status_code == 404


# เทสฟังก์ชันจริง Admin.emb.delete_document_from_index() (BM25+ChromaDB ของจริงแต่ชี้ tmp_path)
# แยกอยู่ที่ web_testing/integration/test_it_index_deletion.py เพื่อไม่ต้องผูกกับ asyncio/httpx
# ของไฟล์นี้ (ฟังก์ชันนั้น sync ล้วน ไม่เกี่ยวกับ FastAPI test client เลย)
