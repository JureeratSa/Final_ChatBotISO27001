"""
Tests: Admin.rebuild_db.rebuild(documents=...) ใช้สถานะ/หน้าที่ละเว้นจาก TiDB
เดิมอ่าน db_documents.json (เลิกใช้แล้ว ว่างเปล่า) → นำเข้า PDF ทุกไฟล์ รวมที่ปิดใช้งาน และไม่ละเว้นหน้า

รัน rebuild() จริงกับ PDF ชั่วคราวใน tmp_path — แทนโมเดล bge-m3 ด้วยตัวปลอม และชี้ ChromaDB/BM25
ไปที่ tmp_path ทั้งหมด จึงไม่โหลดโมเดลและไม่แตะดัชนีจริง
"""
import pickle

import fitz
import numpy as np
import pytest

from Admin import rebuild_db
from app.services import rebuild_service


class FakeSentenceTransformer:
    def __init__(self, *args, **kwargs):
        pass

    def encode(self, texts, **kwargs):
        return np.ones((len(texts), 4), dtype=np.float32)


def _make_pdf(path, pages):
    doc = fitz.open()
    for text in pages:
        doc.new_page().insert_text((72, 72), text)
    doc.save(str(path))
    doc.close()


@pytest.fixture
def fake_repo(tmp_path, monkeypatch):
    (tmp_path / "uploads").mkdir()
    _make_pdf(tmp_path / "uploads" / "active.pdf", ["COVER PAGE alpha", "POLICY CONTENT bravo", "SIGNATURE PAGE charlie"])
    _make_pdf(tmp_path / "uploads" / "inactive.pdf", ["DISABLED DOCUMENT delta"])
    _make_pdf(tmp_path / "uploads" / "pending.pdf", ["NOT YET APPROVED echo"])
    monkeypatch.setattr(rebuild_db, "root_dir", str(tmp_path))
    monkeypatch.setenv("CHROMA_DB_DIR", str(tmp_path / "chroma"))
    import sentence_transformers
    monkeypatch.setattr(sentence_transformers, "SentenceTransformer", FakeSentenceTransformer)
    return tmp_path


def _indexed_chunks(root):
    with open(root / "index_db" / "bm25.pkl", "rb") as f:
        return pickle.load(f)["chunks"]


def test_rebuild_uses_only_active_documents_and_skips_excluded_pages(fake_repo):
    durations = rebuild_db.rebuild(documents=[
        {"filename": "active.pdf", "status": "Active", "exclude_pages": [1, 3]},
        {"filename": "inactive.pdf", "status": "Inactive", "exclude_pages": []},
        {"filename": "pending.pdf", "status": "Step_Raw_Text", "exclude_pages": []},
    ])
    chunks = _indexed_chunks(fake_repo)
    text = " ".join(c["content"] for c in chunks)

    assert {c["metadata"]["source"] for c in chunks} == {"active.pdf"}
    assert "POLICY CONTENT" in text
    assert "COVER PAGE" not in text and "SIGNATURE PAGE" not in text
    assert set(durations) == {"active.pdf"}


def test_changing_exclude_pages_invalidates_cache(fake_repo):
    docs = [{"filename": "active.pdf", "status": "Active", "exclude_pages": []}]
    rebuild_db.rebuild(documents=docs)
    assert "COVER PAGE" in " ".join(c["content"] for c in _indexed_chunks(fake_repo))

    docs[0]["exclude_pages"] = [1]
    rebuild_db.rebuild(documents=docs)
    assert "COVER PAGE" not in " ".join(c["content"] for c in _indexed_chunks(fake_repo))


def test_backend_passes_db_documents_and_saves_durations(monkeypatch):
    docs = [{"filename": "a.pdf", "status": "Active", "exclude_pages": [1]}]
    calls = {}
    monkeypatch.setattr(rebuild_service, "_sync_load_documents", lambda: docs)
    monkeypatch.setattr(rebuild_service, "_sync_save_durations", lambda d: calls.setdefault("saved", d))
    monkeypatch.setattr(rebuild_service, "_sync_update_rebuild_status", lambda *a, **k: calls.setdefault("status", []).append(a[0]))
    monkeypatch.setattr(rebuild_db, "rebuild", lambda documents=None: calls.setdefault("docs", documents) and {"a.pdf": {"chunking_duration": 1.0}})
    import app.services.rag_service as rag_service
    monkeypatch.setattr(rag_service, "reload_retriever", lambda: True)

    rebuild_service._trigger_rebuild_background()

    assert calls["docs"] == docs
    assert calls["saved"] == {"a.pdf": {"chunking_duration": 1.0}}
    assert calls["status"][-1] == "success"
