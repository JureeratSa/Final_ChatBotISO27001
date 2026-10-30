"""
กฎรหัสผ่านแอดมิน + อายุรหัสผ่าน 90 วัน
ฝั่ง AdminWeb มีสำเนากฎ (apps/admin-web/src/utils/passwordPolicy.js) ไว้แสดงเช็กลิสต์ระหว่างพิมพ์
ตัวที่บังคับจริงคือไฟล์นี้ — แก้กฎต้องแก้ทั้งสองไฟล์
"""
import re
from datetime import datetime, timedelta, timezone
from typing import List, Optional

MIN_PASSWORD_LENGTH = 8
RECOMMENDED_PASSWORD_LENGTH = 12
PASSWORD_MAX_AGE_DAYS = 90
PASSWORD_WARN_DAYS = 7

# คำ/ลำดับที่เดาง่าย — เทียบแบบไม่สนตัวพิมพ์ และแปลงตัวเลขแทนตัวอักษร (p@ssw0rd → password) ก่อนเทียบ
WEAK_PATTERNS = (
    "password", "passw", "qwerty", "asdfgh", "zxcvbn", "admin", "letmein", "welcome",
    "iloveyou", "123456", "654321", "abcdef", "111111", "000000",
)
_LEET = str.maketrans({"@": "a", "4": "a", "0": "o", "1": "i", "!": "i", "3": "e", "$": "s", "5": "s", "7": "t"})


def password_problems(password: str, username: Optional[str] = None) -> List[str]:
    """คืนรายการข้อที่ยังไม่ผ่าน (ว่าง = ผ่านทุกข้อ)"""
    problems = []
    if len(password) < MIN_PASSWORD_LENGTH:
        problems.append(f"ต้องยาวอย่างน้อย {MIN_PASSWORD_LENGTH} ตัวอักษร")
    if not re.search(r"[A-Z]", password):
        problems.append("ต้องมีตัวพิมพ์ใหญ่ (A-Z)")
    if not re.search(r"[a-z]", password):
        problems.append("ต้องมีตัวพิมพ์เล็ก (a-z)")
    if not re.search(r"[0-9]", password):
        problems.append("ต้องมีตัวเลข (0-9)")
    if not re.search(r"[^A-Za-z0-9]", password):
        problems.append("ต้องมีสัญลักษณ์ เช่น ! @ # $ %")

    lowered = password.lower()
    normalized = lowered.translate(_LEET)
    weak = next((w for w in WEAK_PATTERNS if w in lowered or w in normalized), None)
    if weak:
        problems.append(f"ห้ามใช้รหัสที่เดาง่าย (พบ \"{weak}\")")
    elif re.search(r"(.)\1{3,}", lowered):
        problems.append("ห้ามใช้ตัวอักษรซ้ำกันติดกันหลายตัว เช่น aaaa")
    if username and len(username) >= 3 and username.lower() in lowered:
        problems.append("ห้ามมีชื่อผู้ใช้อยู่ในรหัสผ่าน")
    return problems


def validate_password(password: str, username: Optional[str] = None) -> str:
    problems = password_problems(password, username)
    if problems:
        raise ValueError("รหัสผ่านไม่ผ่านเกณฑ์: " + ", ".join(problems))
    return password


def _as_utc(dt: datetime) -> datetime:
    # MySQL/SQLite คืน DATETIME แบบไม่มี timezone — ระบบบันทึกเป็นเวลา UTC เสมอ
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def password_status(changed_at: Optional[datetime], now: Optional[datetime] = None) -> dict:
    """สถานะอายุรหัสผ่าน — ไม่มีวันที่เปลี่ยน (NULL) ถือว่าหมดอายุแล้ว ต้องตั้งใหม่"""
    now = now or datetime.now(timezone.utc)
    if changed_at is None:
        return {"password_expires_at": None, "password_days_left": 0,
                "password_expired": True, "password_expiring_soon": False}
    expires_at = _as_utc(changed_at) + timedelta(days=PASSWORD_MAX_AGE_DAYS)
    seconds_left = (expires_at - now).total_seconds()
    days_left = max(0, int(-(-seconds_left // 86400)))  # ปัดขึ้น: เหลือ 6.2 วัน = "อีก 7 วัน"
    expired = seconds_left <= 0
    return {
        "password_expires_at": expires_at.astimezone(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M"),
        "password_days_left": days_left,
        "password_expired": expired,
        "password_expiring_soon": not expired and days_left <= PASSWORD_WARN_DAYS,
    }


def token_issued_before_password_change(iat: Optional[int], changed_at: Optional[datetime]) -> bool:
    """token ที่ออกก่อนเปลี่ยนรหัสผ่านใช้ไม่ได้อีก (บังคับล็อกอินใหม่ทุกเครื่องหลังเปลี่ยนรหัส)
    token รุ่นเก่าที่ไม่มี iat ปล่อยผ่าน — หมดอายุเองภายใน 15 นาที"""
    if iat is None or changed_at is None:
        return False
    return int(iat) < int(_as_utc(changed_at).timestamp())
