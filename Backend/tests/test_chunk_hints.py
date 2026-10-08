"""
Tests: สอนบอทผ่านเอกสาร (chunk hints)
  - Admin.emb.apply_chunk_hints: คำถามตัวอย่างเข้า BM25/ChromaDB โดยเนื้อหา chunk ไม่เปลี่ยน
    (ใช้ดัชนีชั่วคราวใน tmp_path + โมเดลปลอม ไม่โหลด bge-m3 และไม่แตะ index_db จริง)
  - /api/admin/rag/*: ทดสอบค้นหา, ค้นหา chunk, บันทึก/ลบ hint (retriever ปลอม + mock การเขียนดัชนี)
"""
import pickle
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Admin import emb  # noqa: E402
from tests.conftest import auth_header  # noqa: E402
from app.models.models import SystemSettings  # noqa: E402
from app.services import chunk_hint_service as hint_svc  # noqa: E402
from app.services import rag_service  # noqa: E402

CHUNKS = [
    {"chunk_id": 1, "content": "นโยบายการสำรองข้อมูลกำหนดให้สำรองทุกวัน", "metadata": {"source": "backup.pdf", "page": 2, "type": "text"}},
    {"chunk_id": 2, "content": "ต้องทบทวนนโยบายเมื่อมีการเปลี่ยนแปลงโครงสร้างองค์กรหรือเกิดเหตุการณ์ร้ายแรง", "metadata": {"source": "mobile.pdf", "page": 5, "type": "text"}},
    {"chunk_id": 3, "content": "การเข้ารหัสข้อมูลต้องใช้มาตรฐาน AES", "metadata": {"source": "crypto.pdf", "page": 1, "type": "text"}},
]


class FakeModel:
    def __init__(self):
        self.calls = []

    def encode(self, texts, **kwargs):
        import numpy as np
        self.calls.append(list(texts))
        return np.array([[float(len(t)), 1.0, 0.0, 0.0] for t in texts])


# ─── Admin.emb.apply_chunk_hints ────────────────────────────────────────────────

@pytest.fixture
def temp_index(tmp_path):
    import chromadb
    from rank_bm25 import BM25Okapi
    from pythainlp.tokenize import word_tokenize

    index_dir = tmp_path / "index_db"
    index_dir.mkdir()
    with open(index_dir / "bm25.pkl", "wb") as f:
        pickle.dump({
            "bm25_index": BM25Okapi([word_tokenize(c["content"], keep_whitespace=False) for c in CHUNKS]),
            "chunks": CHUNKS,
        }, f)
    chroma_dir = tmp_path / "chroma"
    col = chromadb.PersistentClient(path=str(chroma_dir)).create_collection("tuh_collection")
    col.add(ids=["1", "2", "3"], embeddings=[[0.0, 0.0, 0.0, 1.0]] * 3,
            documents=[c["content"] for c in CHUNKS], metadatas=[c["metadata"] for c in CHUNKS])
    return index_dir, chroma_dir


def _load(index_dir):
    with open(index_dir / "bm25.pkl", "rb") as f:
        return pickle.load(f)


def _chroma(chroma_dir):
    import chromadb
    return chromadb.PersistentClient(path=str(chroma_dir)).get_collection("tuh_collection")


def test_apply_hints_boosts_bm25_without_changing_content(temp_index):
    from pythainlp.tokenize import word_tokenize
    index_dir, chroma_dir = temp_index
    model = FakeModel()
    key = emb.chunk_key(CHUNKS[1])

    result = emb.apply_chunk_hints({key: ["Trigger ทบทวนนโยบายคอมพิวเตอร์พกพา"]},
                                   index_dir=str(index_dir), chroma_dir=str(chroma_dir), model=model)
    assert result == {"matched": 1, "reembedded": 1}

    data = _load(index_dir)
    assert [c["content"] for c in data["chunks"]] == [c["content"] for c in CHUNKS]
    scores = data["bm25_index"].get_scores(word_tokenize("Trigger คอมพิวเตอร์พกพา", keep_whitespace=False))
    assert max(range(3), key=lambda i: scores[i]) == 1

    col = _chroma(chroma_dir)
    got = col.get(ids=["2"], include=["embeddings", "documents"])
    assert got["documents"][0] == CHUNKS[1]["content"]
    assert model.calls[0][0].startswith(CHUNKS[1]["content"]) and emb.HINTS_HEADER in model.calls[0][0]
    assert got["embeddings"][0][1] == pytest.approx(1.0)


def test_apply_hints_is_incremental_and_reversible(temp_index):
    index_dir, chroma_dir = temp_index
    key = emb.chunk_key(CHUNKS[1])
    hints = {key: ["คำถาม ก"]}
    emb.apply_chunk_hints(hints, index_dir=str(index_dir), chroma_dir=str(chroma_dir), model=FakeModel())

    again = FakeModel()
    assert emb.apply_chunk_hints(hints, index_dir=str(index_dir), chroma_dir=str(chroma_dir), model=again)["reembedded"] == 0
    assert again.calls == []

    restore = FakeModel()
    assert emb.apply_chunk_hints({}, index_dir=str(index_dir), chroma_dir=str(chroma_dir), model=restore)["reembedded"] == 1
    assert restore.calls == [[CHUNKS[1]["content"]]]
    assert _load(index_dir)["applied_hints"] == {}


def test_apply_hints_updates_loaded_retriever(temp_index):
    index_dir, chroma_dir = temp_index

    class R:
        is_loaded = True
        bm25 = None
        bm25_chunks = None
        model = FakeModel()

    r = R()
    emb.apply_chunk_hints({emb.chunk_key(CHUNKS[0]): ["สำรองข้อมูลบ่อยแค่ไหน"]}, retriever=r,
                          index_dir=str(index_dir), chroma_dir=str(chroma_dir))
    assert r.bm25 is not None and len(r.bm25_chunks) == 3
    assert r.model.calls  # ใช้โมเดลของ retriever ที่โหลดอยู่แล้ว ไม่โหลด bge-m3 ซ้ำ


# ─── /api/admin/rag/* ───────────────────────────────────────────────────────────

class FakeRetriever:
    is_loaded = True
    dense_enabled = True

    def __init__(self):
        self.bm25_chunks = [dict(c) for c in CHUNKS]

    def query(self, query_str, top_k=5, rrf_k=60):
        order = [2, 1, 3] if "ทบทวน" in query_str else [1, 3, 2]
        by_id = {c["chunk_id"]: c for c in self.bm25_chunks}
        return [{**by_id[cid], "hybrid_rank": i, "dense_rank": i, "dense_score": 0.5, "lexical_rank": i}
                for i, cid in enumerate(order[:top_k], start=1)]


@pytest.fixture
def fake_rag(monkeypatch):
    retriever = FakeRetriever()
    monkeypatch.setattr(rag_service, "_retriever", retriever)
    applied = []
    monkeypatch.setattr(hint_svc, "apply_hints_sync", lambda hints: applied.append(hints) or {})
    return retriever, applied


async def test_test_search_marks_chat_context(client, admin_user, db_session, fake_rag):
    db_session.add(SystemSettings(id="config", top_k=1))
    await db_session.commit()
    resp = await client.post("/api/admin/rag/test-search", json={"query": "ทบทวนนโยบาย"},
                             headers=auth_header(admin_user.username))
    assert resp.status_code == 200
    data = resp.json()
    assert data["top_k"] == 1
    assert [r["source"] for r in data["results"]] == ["mobile.pdf", "backup.pdf", "crypto.pdf"]
    assert [r["in_chat_context"] for r in data["results"]] == [True, False, False]
    assert data["results"][0]["chunk_hash"] == emb.chunk_hash(CHUNKS[1]["content"])


async def test_chunk_search_filters_by_keyword_and_source(client, admin_user, fake_rag):
    headers = auth_header(admin_user.username)
    resp = await client.post("/api/admin/rag/chunks/search", json={"keyword": "aes"}, headers=headers)
    assert [r["chunk_id"] for r in resp.json()["results"]] == [3]
    resp = await client.post("/api/admin/rag/chunks/search", json={"keyword": "นโยบาย", "source": "backup.pdf"}, headers=headers)
    assert [r["chunk_id"] for r in resp.json()["results"]] == [1]


async def test_save_hint_upserts_applies_and_verifies(client, admin_user, db_session, fake_rag):
    _, applied = fake_rag
    headers = auth_header(admin_user.username)
    ref = {"source": "mobile.pdf", "chunk_hash": emb.chunk_hash(CHUNKS[1]["content"])}

    resp = await client.put("/api/admin/rag/chunk-hints", headers=headers, json={
        **ref, "questions": [" Trigger ทบทวนนโยบาย ", "trigger ทบทวนนโยบาย", "ทบทวนเมื่อไหร่"],
        "verify_query": "ทบทวนนโยบายเมื่อไหร่",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["questions"] == ["Trigger ทบทวนนโยบาย", "ทบทวนเมื่อไหร่"]  # ตัดช่องว่าง + ตัดซ้ำ
    assert data["verification"]["rank"] == 1 and data["verification"]["in_chat_context"] is True
    assert applied[-1] == {(ref["source"], ref["chunk_hash"]): data["questions"]}

    resp = await client.put("/api/admin/rag/chunk-hints", headers=headers, json={**ref, "questions": ["แก้ใหม่"]})
    assert resp.json()["id"] == data["id"]  # upsert ไม่สร้างแถวซ้ำ

    listing = (await client.get("/api/admin/rag/chunk-hints", headers=headers)).json()
    assert len(listing) == 1 and listing[0]["questions"] == ["แก้ใหม่"] and listing[0]["active"] is True
    assert listing[0]["page"] == 5 and listing[0]["content_preview"] == CHUNKS[1]["content"]

    resp = await client.delete(f"/api/admin/rag/chunk-hints/{data['id']}", headers=headers)
    assert resp.status_code == 204
    assert applied[-1] == {}


async def test_save_hint_rejects_unknown_chunk_and_running_rebuild(client, admin_user, db_session, fake_rag):
    headers = auth_header(admin_user.username)
    resp = await client.put("/api/admin/rag/chunk-hints", headers=headers,
                            json={"source": "x.pdf", "chunk_hash": "0" * 64, "questions": ["ก"]})
    assert resp.status_code == 404

    db_session.add(SystemSettings(id="config", rebuild_status="processing"))
    await db_session.commit()
    resp = await client.put("/api/admin/rag/chunk-hints", headers=headers, json={
        "source": "mobile.pdf", "chunk_hash": emb.chunk_hash(CHUNKS[1]["content"]), "questions": ["ก"]})
    assert resp.status_code == 409


async def test_suggest_falls_back_to_original_query_without_api_key(client, admin_user, fake_rag, monkeypatch):
    monkeypatch.setattr(type(hint_svc.settings), "LLM_API_KEY", property(lambda self: ""))
    resp = await client.post("/api/admin/rag/chunk-hints/suggest", headers=auth_header(admin_user.username), json={
        "source": "mobile.pdf", "chunk_hash": emb.chunk_hash(CHUNKS[1]["content"]), "query": "ทบทวนนโยบายเมื่อไหร่"})
    assert resp.json() == {"questions": ["ทบทวนนโยบายเมื่อไหร่"]}


async def test_suggest_puts_original_query_first_and_dedupes(client, admin_user, fake_rag, monkeypatch):
    monkeypatch.setattr(type(hint_svc.settings), "LLM_API_KEY", property(lambda self: "test-key"))
    llm_text = '["เอาโน้ตบุ๊กกลับบ้านได้ไหม", "ยืมโน้ตบุ๊กไปใช้นอกโรงพยาบาลได้ไหม"]'
    monkeypatch.setattr(rag_service, "make_http_post",
                        lambda *a, **k: {"choices": [{"message": {"content": llm_text}}]})
    resp = await client.post("/api/admin/rag/chunk-hints/suggest", headers=auth_header(admin_user.username), json={
        "source": "mobile.pdf", "chunk_hash": emb.chunk_hash(CHUNKS[1]["content"]), "query": "เอาโน้ตบุ๊กกลับบ้านได้ไหม"})
    assert resp.json() == {"questions": ["เอาโน้ตบุ๊กกลับบ้านได้ไหม", "ยืมโน้ตบุ๊กไปใช้นอกโรงพยาบาลได้ไหม"]}


async def test_rag_endpoints_require_auth(client, fake_rag):
    assert (await client.post("/api/admin/rag/test-search", json={"query": "x"})).status_code in (401, 403)
    assert (await client.get("/api/admin/rag/chunk-hints")).status_code in (401, 403)


async def test_rag_returns_503_when_index_not_loaded(client, admin_user, monkeypatch):
    monkeypatch.setattr(rag_service, "_retriever", None)
    resp = await client.post("/api/admin/rag/test-search", json={"query": "x"}, headers=auth_header(admin_user.username))
    assert resp.status_code == 503
