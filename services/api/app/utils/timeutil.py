"""
แปลงเวลาเป็นเวลาไทย (UTC+7) ตอนส่งออกไปแสดงผล
ฐานข้อมูลเก็บเวลาเป็น UTC และคืนค่ากลับมาแบบไม่มี timezone — ต้องแปลงก่อนแสดง ไม่งั้นช้าไป 7 ชั่วโมง
"""
from datetime import datetime, time, timedelta, timezone
from typing import Optional, Tuple

THAI_TZ = timezone(timedelta(hours=7))
DISPLAY_FORMAT = "%Y-%m-%d %H:%M:%S"


def as_utc(dt: datetime) -> datetime:
    """ค่าที่ไม่มี timezone (มาจาก MySQL/SQLite) ถือเป็น UTC เสมอ"""
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def to_thai(dt: Optional[datetime]) -> Optional[datetime]:
    return as_utc(dt).astimezone(THAI_TZ) if dt else None


def thai_str(dt: Optional[datetime], fmt: str = DISPLAY_FORMAT) -> Optional[str]:
    """"YYYY-MM-DD HH:MM:SS" ตามเวลาไทย — AdminWeb อ่านสตริงนี้เป็นเวลาท้องถิ่นของเครื่องผู้ใช้ (ไทย) ตรงๆ"""
    return to_thai(dt).strftime(fmt) if dt else None


def thai_day_range_utc(day: Optional[datetime] = None) -> Tuple[datetime, datetime]:
    """ช่วงเวลาของ "วันนี้ตามเวลาไทย" เป็น UTC แบบไม่มี timezone (ใช้เทียบกับคอลัมน์ในฐานข้อมูล)"""
    thai_now = (day or datetime.now(timezone.utc)).astimezone(THAI_TZ)
    start = datetime.combine(thai_now.date(), time.min, tzinfo=THAI_TZ).astimezone(timezone.utc)
    return start.replace(tzinfo=None), (start + timedelta(days=1)).replace(tzinfo=None)
