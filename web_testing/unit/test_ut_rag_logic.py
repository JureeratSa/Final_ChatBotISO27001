"""
Unit Test — RAG Logic (UT-09)
อ้างอิง: แผนทดสอบเว็บ T3 — เรียก Admin.emb.weighted_rrf_score() ตรงๆ

weighted_rrf_score() แยกออกมาจาก merge_results() closure ภายใน HybridRetriever.query()
(Admin/emb.py) — เดิมสูตรฝังอยู่ในบรรทัดเดียวข้างในลูป เทสแบบ unit ไม่ได้ ได้รับอนุญาต
ให้แยกออกมาแล้ว (2026-09-21) สูตร/พฤติกรรมเดิมทุกกรณี ไม่ได้แก้ logic การคำนวณ
"""
import pytest

from Admin.emb import weighted_rrf_score


# ─── UT-09: คำนวณคะแนน Weighted RRF (dense weight=0.4, lexical weight=0.6, rrf_k=60) ──

def test_UT09_dense_side_score_at_rank_1():
    """คะแนนฝั่ง dense (ChromaDB) อันดับ 1 ด้วยน้ำหนักจริงที่ใช้ในระบบ (0.4)"""
    assert weighted_rrf_score(rank=1, weight=0.4, rrf_k=60) == pytest.approx(0.4 * (1.0 / 61))


def test_UT09_lexical_side_score_at_rank_1():
    """คะแนนฝั่ง lexical (BM25) อันดับ 1 ด้วยน้ำหนักจริงที่ใช้ในระบบ (0.6)"""
    assert weighted_rrf_score(rank=1, weight=0.6, rrf_k=60) == pytest.approx(0.6 * (1.0 / 61))


def test_UT09_same_chunk_ranked_1_in_both_lists_sums_to_plain_rrf():
    """chunk เดียวกันติดอันดับ 1 ทั้งสองฝั่ง — ผลรวมของสองคะแนนถ่วงน้ำหนัก (0.4+0.6=1.0)
    ต้องเท่ากับ RRF ธรรมดาที่ไม่ถ่วงน้ำหนักพอดี เพราะน้ำหนักรวมกันได้ 1.0"""
    total = weighted_rrf_score(1, 0.4, 60) + weighted_rrf_score(1, 0.6, 60)
    assert total == pytest.approx(1.0 * (1.0 / 61))


def test_UT09_lower_rank_number_always_scores_higher():
    """BVA — อันดับที่ดีกว่า (เลขน้อยกว่า) ต้องได้คะแนนมากกว่าเสมอ เมื่อน้ำหนักและ rrf_k เท่ากัน"""
    assert weighted_rrf_score(1, 0.4, 60) > weighted_rrf_score(2, 0.4, 60)
    assert weighted_rrf_score(2, 0.4, 60) > weighted_rrf_score(3, 0.4, 60)


def test_UT09_default_rrf_k_matches_hybrid_retriever_default():
    """rrf_k default ของฟังก์ชัน (60) ต้องตรงกับ default ของ HybridRetriever.query(rrf_k=60)"""
    assert weighted_rrf_score(rank=1, weight=0.4) == pytest.approx(0.4 / 61)


def test_UT09_zero_weight_yields_zero_score():
    """EG — น้ำหนักเป็น 0 (ฝั่งที่ไม่ได้ใช้ เช่น dense ตอนปิด dense_enabled) ต้องได้คะแนน 0 เสมอ"""
    assert weighted_rrf_score(rank=1, weight=0.0, rrf_k=60) == 0.0
