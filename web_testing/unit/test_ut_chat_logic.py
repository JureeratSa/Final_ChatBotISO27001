"""
Unit Test — Chat Logic (UT-10 ถึง UT-12)
อ้างอิง: แผนทดสอบเว็บ T3 — เรียก app.services.rag_service / app.schemas.schemas ตรงๆ
"""
import pytest
from pydantic import ValidationError

from app.services.rag_service import is_chit_chat, contains_profanity
from app.schemas.schemas import ChatRequest


# ─── UT-10: ตรวจจับคำถามประเภท chit-chat/ทักทาย (EP) ─────────────────────────

@pytest.mark.parametrize("text", ["สวัสดีครับ", "ขอบคุณครับ", "hello", "thx"])
def test_UT10_greeting_is_detected_as_chit_chat(text):
    assert is_chit_chat(text) is True


def test_UT10_real_question_is_not_chit_chat():
    assert is_chit_chat("ขอทำบัตรผู้ป่วยใหม่ต้องใช้เอกสารอะไรบ้าง") is False


# ─── UT-11: ตรวจจับคำหยาบ/ข้อความไม่เหมาะสม (EP) ──────────────────────────────

def test_UT11_rude_word_is_detected():
    assert contains_profanity("มึงโง่มาก") is True


def test_UT11_normal_question_is_not_flagged():
    assert contains_profanity("เวลาทำการคลินิกนอกเวลากี่โมง") is False


def test_UT11_exception_word_is_not_falsely_flagged():
    """'กู' อยู่ในรายการคำหยาบ แต่ 'กูเกิล' ต้องไม่โดนเหมาว่าหยาบ (exception list ใน rag_service.py)"""
    assert contains_profanity("ค้นหาใน Google แผนที่โรงพยาบาล") is False


# ─── UT-12: ความยาวคำถามเทียบค่าสูงสุดที่กำหนด (BVA — ขอบเขต max_length=2000) ─

def test_UT12_query_at_max_length_is_accepted():
    """ความยาวเท่ากับ limit พอดี (2000 ตัวอักษร) ต้องผ่าน"""
    req = ChatRequest(query="ก" * 2000)
    assert len(req.query) == 2000


def test_UT12_query_over_max_length_is_rejected():
    """ความยาวเกิน limit ไป 1 ตัวอักษร (2001) ต้องถูกปฏิเสธ"""
    with pytest.raises(ValidationError):
        ChatRequest(query="ก" * 2001)
