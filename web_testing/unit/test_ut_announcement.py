"""
Unit Test — Announcement (UT-14)
อ้างอิง: แผนทดสอบเว็บ T3 — เรียก app.routers.public.is_announcement_active() ตรงๆ

is_announcement_active() แยกออกมาจาก compatibility_active_announcements() ใน public.py
(เดิม logic ฝังอยู่ในตัว route handler ตรงๆ เทสแบบ unit ไม่ได้) — พฤติกรรมเดิมทุกกรณี
ไม่ได้เปลี่ยน logic ระหว่างแยก
"""
import datetime

from app.routers.public import is_announcement_active


# ─── UT-14: คำนวณสถานะ "active" จากวันเริ่ม-สิ้นสุดเทียบวันปัจจุบัน (BVA) ─────

def test_UT14_within_date_range_is_active():
    now = datetime.datetime(2026, 9, 21, 10, 0)
    assert is_announcement_active("2026-09-01", "2026-09-30", now) is True


def test_UT14_before_start_date_is_not_active():
    now = datetime.datetime(2026, 9, 21, 10, 0)
    assert is_announcement_active("2026-10-01", "2026-10-31", now) is False


def test_UT14_expired_exactly_today_is_not_active_after_end_of_day():
    """ประกาศที่ end_date คือ "เมื่อวาน" เทียบกับวันนี้ ต้องไม่ active แล้ว"""
    now = datetime.datetime(2026, 9, 21, 10, 0)
    assert is_announcement_active("2026-08-01", "2026-09-20", now) is False


def test_UT14_end_date_is_today_is_still_active():
    """ประกาศที่ end_date ตรงกับวันนี้พอดี (วันที่ล้วนไม่มีเวลา) ต้องยัง active อยู่ทั้งวัน
    เพราะ end_date แบบวันที่ล้วนจะถูกเติม T23:59 ให้อัตโนมัติ"""
    now = datetime.datetime(2026, 9, 21, 23, 0)
    assert is_announcement_active("2026-09-01", "2026-09-21", now) is True


def test_UT14_none_dates_are_not_active():
    now = datetime.datetime(2026, 9, 21, 10, 0)
    assert is_announcement_active(None, None, now) is False


def test_UT14_datetime_format_with_time_component():
    """รองรับ format ที่มีเวลาระบุมาด้วย (ไม่ใช่แค่วันที่ล้วน) เช่นกำหนดให้แสดงถึง 12:00 เที่ยงตรง"""
    now_before_noon = datetime.datetime(2026, 9, 21, 11, 59)
    now_after_noon = datetime.datetime(2026, 9, 21, 12, 1)
    assert is_announcement_active("2026-09-21T00:00", "2026-09-21T12:00", now_before_noon) is True
    assert is_announcement_active("2026-09-21T00:00", "2026-09-21T12:00", now_after_noon) is False
