"""
Tests: สอนคำค้นจากหน้าคำถามที่บอทตอบไม่ได้ (resolution_type=search_keywords)
  - PUT /api/admin/unanswered/{id} บันทึก/ตรวจ search_keywords
  - expand_retrieval_query: เติมคำค้นเฉพาะคำถามที่คล้ายคำถามที่สอนไว้ (โมเดลปลอม ไม่โหลด bge-m3)
  - analyze_query: prompt มีชื่อเอกสารในดัชนี ให้ AI เสนอคำแบบภาษาเอกสาร
"""
import numpy as np
import pytest

from tests.conftest import auth_header
from app.core.config import settings
from app.models.models import UnansweredQuery
from app.schemas.schemas import UnansweredSubmit
from app.services import rag_service, taught_keywords_service as tk
from app.services.unanswered_service import analyze_query, record_unanswered_query

pytestmark = pytest.mark.asyncio

TAUGHT = "เอาโน้ตบุ๊กของโรงพยาบาลกลับบ้านได้ไหม"


@pytest.fixture(autouse=True)
def _reset_cache():
    tk.invalidate_cache()
    tk._vectors.clear()
    yield
    tk.invalidate_cache()
    tk._vectors.clear()


async def _seed(db_session, **kw):
    db_session.add(UnansweredQuery(id="unans-1", query=TAUGHT, count=1, status=kw.pop("status", "Pending"), **kw))
    await db_session.commit()


# ─── บันทึกคำค้น ────────────────────────────────────────────────────────────────

async def test_save_search_keywords(client, admin_user, db_session):
    await _seed(db_session)
    resp = await client.put("/api/admin/unanswered/unans-1", headers=auth_header(admin_user.username), json={
        "status": "Resolved", "resolution_type": "search_keywords",
        "search_keywords": [" คอมพิวเตอร์แบบพกพา ", "คอมพิวเตอร์แบบพกพา", "ทรัพย์สินของ รพธ."],
    })
    assert resp.status_code == 200
    assert resp.json()["search_keywords"] == ["คอมพิวเตอร์แบบพกพา", "ทรัพย์สินของ รพธ."]


@pytest.mark.parametrize("payload", [
    {"status": "Resolved", "resolution_type": "search_keywords"},
    {"status": "Resolved", "resolution_type": "search_keywords", "search_keywords": ["  "]},
    {"status": "Resolved", "resolution_type": "custom_faq", "search_keywords": ["ก"]},
    {"status": "Resolved", "resolution_type": "search_keywords", "search_keywords": ["x" * 101]},
    {"status": "Resolved", "resolution_type": "search_keywords", "search_keywords": [f"k{i}" for i in range(11)]},
])
async def test_invalid_keyword_payloads(client, admin_user, db_session, payload):
    await _seed(db_session)
    resp = await client.put("/api/admin/unanswered/unans-1", headers=auth_header(admin_user.username), json=payload)
    assert resp.status_code == 422


async def test_reopen_keeps_keywords_for_editing(db_session, session_maker):
    await _seed(db_session, status="Resolved", resolution_type="search_keywords", search_keywords='["คอมพิวเตอร์แบบพกพา"]')
    async with session_maker() as s:
        await record_unanswered_query(s, UnansweredSubmit(query=TAUGHT))
    async with session_maker() as s:
        item = await s.get(UnansweredQuery, "unans-1")
    assert item.status == "Pending" and item.resolution_type is None
    assert item.search_keywords == '["คอมพิวเตอร์แบบพกพา"]'


# ─── เติมคำค้นตอนค้นเอกสาร ─────────────────────────────────────────────────────

class FakeModel:
    """เวกเตอร์ 2 มิติ: คำถามที่มี 'โน้ตบุ๊ก' ชี้ทิศเดียวกับคำถามที่สอน (similarity สูง) นอกนั้นตั้งฉาก"""
    def __init__(self):
        self.encoded = []

    def encode(self, texts, **kwargs):
        self.encoded.extend(texts)
        return np.array([[1.0, 0.0] if "โน้ตบุ๊ก" in t else [0.0, 1.0] for t in texts])


class FakeRetriever:
    dense_enabled = True

    def __init__(self):
        self.model = FakeModel()


async def test_expands_similar_question_only(db_session):
    await _seed(db_session, status="Resolved", resolution_type="search_keywords",
                search_keywords='["คอมพิวเตอร์แบบพกพา", "ทรัพย์สินของ รพธ."]')
    r = FakeRetriever()
    assert await tk.expand_retrieval_query(db_session, r, "ยืมโน้ตบุ๊กไปใช้ที่บ้านได้มั้ย") == \
        "ยืมโน้ตบุ๊กไปใช้ที่บ้านได้มั้ย คอมพิวเตอร์แบบพกพา ทรัพย์สินของ รพธ."
    assert await tk.expand_retrieval_query(db_session, r, "รหัสผ่านต้องเปลี่ยนบ่อยแค่ไหน") == "รหัสผ่านต้องเปลี่ยนบ่อยแค่ไหน"
    assert r.model.encoded.count(TAUGHT) == 1  # embedding ของคำถามที่สอนคำนวณครั้งเดียว


@pytest.mark.parametrize("seed", [
    {"status": "Pending", "search_keywords": '["คอมพิวเตอร์แบบพกพา"]'},
    {"status": "Resolved", "resolution_type": "custom_faq", "search_keywords": '["คอมพิวเตอร์แบบพกพา"]'},
    {"status": "Ignored", "ignore_reason": "spam"},
])
async def test_inactive_items_do_not_expand(db_session, seed):
    await _seed(db_session, **seed)
    assert await tk.expand_retrieval_query(db_session, FakeRetriever(), "โน้ตบุ๊กกลับบ้าน") == "โน้ตบุ๊กกลับบ้าน"


async def test_no_expansion_without_dense_model(db_session):
    await _seed(db_session, status="Resolved", resolution_type="search_keywords", search_keywords='["ก"]')
    r = FakeRetriever()
    r.dense_enabled = False
    assert await tk.expand_retrieval_query(db_session, r, "โน้ตบุ๊ก") == "โน้ตบุ๊ก"


async def test_admin_update_takes_effect_immediately(client, admin_user, db_session):
    await _seed(db_session)
    r = FakeRetriever()
    assert await tk.expand_retrieval_query(db_session, r, "โน้ตบุ๊ก") == "โน้ตบุ๊ก"  # cache ว่าง
    await client.put("/api/admin/unanswered/unans-1", headers=auth_header(admin_user.username), json={
        "status": "Resolved", "resolution_type": "search_keywords", "search_keywords": ["คอมพิวเตอร์แบบพกพา"]})
    assert await tk.expand_retrieval_query(db_session, r, "โน้ตบุ๊ก") == "โน้ตบุ๊ก คอมพิวเตอร์แบบพกพา"


# ─── AI เสนอคำค้นภาษาเอกสาร ─────────────────────────────────────────────────────

async def test_analyze_prompt_lists_document_titles(monkeypatch):
    class R:
        bm25_chunks = [
            {"content": "เรื่อง : นโยบายคอมพิวเตอร์แบบพกพา (Mobile device)  วันที่ประกาศใช้", "metadata": {"source": "mobile.pdf"}},
            {"content": "ไม่มีหัวเรื่อง", "metadata": {"source": "backup policy.pdf"}},
        ]
    monkeypatch.setattr(rag_service, "_retriever", R())
    monkeypatch.setattr(type(settings), "LLM_API_KEY", property(lambda self: "k"))
    sent = {}

    def fake_post(url, payload, headers, timeout):
        sent["prompt"] = payload["messages"][0]["content"]
        return {"choices": [{"message": {"content": '{"is_valid_query": true, "suggested_keywords": ["คอมพิวเตอร์แบบพกพา"]}'}}]}

    monkeypatch.setattr(rag_service, "make_http_post", fake_post)
    result = await analyze_query(TAUGHT)
    assert result["suggested_keywords"] == ["คอมพิวเตอร์แบบพกพา"]
    assert "- นโยบายคอมพิวเตอร์แบบพกพา (Mobile device)" in sent["prompt"]
    assert "- backup policy" in sent["prompt"]
