"""
ยกเลิก token รายใบตอน logout — จด jti ของ token ไว้จนถึงเวลาที่มันหมดอายุเอง

ยกเลิกเฉพาะใบที่กด logout (ไม่ใช้ token_version) เพราะ AdminWeb ออกให้อัตโนมัติเมื่อไม่ได้ใช้งาน
ถ้ายกเลิกทุกใบ เครื่องอื่นของแอดมินคนเดียวกันจะเด้งออกไปด้วย
เก็บในหน่วยความจำ — รีสตาร์ท backend แล้วรายการหาย (token ที่ค้างอยู่หมดอายุเองภายใน 15 นาที)
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
