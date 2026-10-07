"""
Unit tests: rag_service.split_used_sources
แนบ citation เฉพาะชิ้นที่ LLM บอกว่าใช้ตอบจริง (tag [SOURCES: ...]) และตัด tag ออกจากคำตอบ
"""
from app.services.rag_service import split_used_sources

RESULTS = [{"chunk_id": 243}, {"chunk_id": 125}, {"chunk_id": 80}]


def test_keeps_only_cited_chunks_and_strips_tag():
    answer, used = split_used_sources("ตั้งรหัสผ่านอย่างน้อย 8 ตัวครับ\n[SOURCES: 2,3]", RESULTS)
    assert answer == "ตั้งรหัสผ่านอย่างน้อย 8 ตัวครับ"
    assert [r["chunk_id"] for r in used] == [125, 80]


def test_tolerates_spacing_and_case():
    _, used = split_used_sources("คำตอบ [ sources : 1 ]", RESULTS)
    assert [r["chunk_id"] for r in used] == [243]


def test_none_means_no_citation():
    answer, used = split_used_sources("ขาหมูพร้อมตอบคำถามครับ\n[SOURCES: none]", RESULTS)
    assert answer == "ขาหมูพร้อมตอบคำถามครับ"
    assert used == []


def test_missing_tag_keeps_old_behaviour():
    answer, used = split_used_sources("คำตอบที่ไม่มี tag", RESULTS)
    assert answer == "คำตอบที่ไม่มี tag"
    assert used == RESULTS


def test_out_of_range_numbers_fall_back_to_all():
    _, used = split_used_sources("คำตอบ\n[SOURCES: 7]", RESULTS)
    assert used == RESULTS
