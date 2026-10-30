"""
TUH Chatbot AI — ยกเลิก token รายใบตอน logout (security audit L4)
JWT เป็น stateless — เดิมกด logout แล้ว token ใบนั้นยังใช้ต่อได้จนหมดอายุ (สูงสุด 15 นาที)
ตอนนี้ logout = จด jti ของ token ใบนั้นไว้จนถึงเวลาหมดอายุของมัน

ยกเลิกเฉพาะใบที่กด logout — ไม่ใช้ token_version กับ logout เพราะ AdminWeb ออกให้อัตโนมัติเมื่อไม่มี
การใช้งาน 10 นาที ถ้าใช้ token_version แอดมินคนเดียวกันที่เปิดอีกเครื่องจะถูกเด้งออกไปด้วย
เก็บในหน่วยความจำของ process เดียว (backend รัน worker เดียว) — รีสตาร์ท backend แล้วรายการหาย
token ที่ logout ไปแล้วจะกลับมาใช้ได้อีกไม่เกินอายุที่เหลือ (≤ 15 นาที)
"""
import threading
import time

_revoked: dict[str, float] = {}   # jti -> เวลาหมดอายุ (epoch seconds)
_lock = threading.Lock()


def revoke(jti: str, expires_at: float) -> None:
    if not jti:
        return
    with _lock:
        now = time.time()
        for old in [k for k, exp in _revoked.items() if exp <= now]:
            del _revoked[old]
        _revoked[jti] = expires_at


def is_revoked(jti: str) -> bool:
    if not jti:
        return False
    with _lock:
        exp = _revoked.get(jti)
        return exp is not None and exp > time.time()
