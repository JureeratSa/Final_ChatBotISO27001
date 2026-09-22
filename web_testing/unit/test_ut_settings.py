"""
Unit Test — Settings (UT-13)
อ้างอิง: แผนทดสอบเว็บ T3 — เรียก app.schemas.schemas.SettingsUpdate ตรงๆ
ขอบเขตจริงที่ประกาศไว้ใน schema: temperature 0.0-2.0, max_tokens 1-8000, top_k 1-20
"""
import pytest
from pydantic import ValidationError

from app.schemas.schemas import SettingsUpdate


# ─── UT-13: ค่าพารามิเตอร์เทียบขอบเขตที่กำหนด (BVA) ──────────────────────────

def test_UT13_top_k_at_upper_bound_is_accepted():
    s = SettingsUpdate(top_k=20)
    assert s.top_k == 20


def test_UT13_top_k_over_upper_bound_is_rejected():
    with pytest.raises(ValidationError):
        SettingsUpdate(top_k=21)


def test_UT13_top_k_at_lower_bound_is_accepted():
    s = SettingsUpdate(top_k=1)
    assert s.top_k == 1


def test_UT13_top_k_below_lower_bound_is_rejected():
    with pytest.raises(ValidationError):
        SettingsUpdate(top_k=0)


def test_UT13_temperature_over_upper_bound_is_rejected():
    with pytest.raises(ValidationError):
        SettingsUpdate(temperature=2.1)


def test_UT13_max_tokens_over_upper_bound_is_rejected():
    with pytest.raises(ValidationError):
        SettingsUpdate(max_tokens=8001)
