"""
จำกัดความถี่คำขอต่อ IP (กันยิงถี่จนค่า LLM บานปลาย) + จำกัดการเดารหัสผ่านตอนล็อกอิน
เก็บตัวนับในหน่วยความจำ — backend รัน worker เดียว (ดู services/api/Dockerfile) รีสตาร์ทแล้วตัวนับเริ่มใหม่
"""
import math
import time
from collections import defaultdict, deque
from typing import Optional

from fastapi import Request, HTTPException, status

from app.core.config import settings

# ที่เก็บประวัติ Timestamp การส่งคำขอแยกตาม IP: { "192.168.1.1": deque([ts1, ts2, ...]) }
_hits: dict[str, deque] = defaultdict(deque)
_MAX_TRACKED_IPS = 10000


def _client_ip(request: Request) -> str:
    """
    IP ของ Client — ใช้ IP ของการเชื่อมต่อจริงเป็นค่าเริ่มต้น
    X-Forwarded-For เชื่อเฉพาะเมื่อตั้ง TRUST_PROXY_HEADERS=true (มี reverse proxy ของเราอยู่หน้า backend)
    (ถ้าเชื่อเสมอ client จะปลอม header ใหม่ทุกครั้งเพื่อหลบ limit ได้)
    ค่าที่ใช้คือตัวท้ายสุด ซึ่ง proxy ของเราเป็นคนเติม ตัวหน้าๆ client ปลอมมาเองได้
    """
    if settings.TRUST_PROXY_HEADERS:
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


def _drop_stale_ips(now: float, window: int) -> None:
    """ลบ IP ที่ไม่มีคำขอในหน้าต่างเวลาแล้ว (ไม่ให้ dict โตไม่สิ้นสุด)"""
    for ip in [ip for ip, hits in _hits.items() if not hits or now - hits[-1] > window]:
        del _hits[ip]


async def rate_limit_dependency(request: Request):
    """
    FastAPI Dependency: ตรวจสอบ Rate Limit ด้วย Sliding Window Algorithm
    - จำกัดจำนวนคำขอไม่เกิน RATE_LIMIT_REQUESTS ครั้ง ในช่วง RATE_LIMIT_WINDOW_SECONDS วินาที
    - หากเกินกำหนด จะส่ง HTTP 429 Too Many Requests กลับไปทันที
    """
    ip = _client_ip(request)
    now = time.monotonic()
    window = settings.RATE_LIMIT_WINDOW_SECONDS
    limit = settings.RATE_LIMIT_REQUESTS

    if len(_hits) > _MAX_TRACKED_IPS:
        _drop_stale_ips(now, window)
    # นับแยกต่อ endpoint — กดถูกใจ/ส่ง feedback ไม่กินโควตาถามแชทของ IP เดียวกัน
    hits = _hits[f"{ip} {request.url.path}"]

    # 1. ลบ Timestamp เก่าที่อยู่นอกหน้าต่างเวลาทิ้ง
    while hits and now - hits[0] > window:
        hits.popleft()

    # 2. ตรวจสอบว่าจำนวนคำขอในหน้าต่างเวลาปัจจุบันเกินเพดานหรือไม่
    if len(hits) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"ส่งคำขอถี่เกินไป กรุณารอสักครู่แล้วลองใหม่ (จำกัด {limit} ครั้ง / {window} วินาที)"
        )

    # 3. บันทึก Timestamp ของคำขอนี้เข้าคิว
    hits.append(now)


# ─── Login Brute-force Protection ──────────────────────────────────────────────

class LoginThrottle:
    """นับการล็อกอินผิดภายใน LOGIN_FAILURE_WINDOW_MINUTES — นับเฉพาะครั้งที่ผิด ล็อกอินสำเร็จแล้วล้างตัวนับ
    - ผิดครบ LOGIN_MAX_FAILURES_PER_IP_USER ครั้ง จาก IP เดียวกันกับ username เดียวกัน → ล็อกคู่นั้น
    - ผิดครบ LOGIN_MAX_FAILURES_PER_USER ครั้ง จากทุก IP รวมกัน → ล็อก username นั้น (กันสลับ IP เดา)
    ไม่ล็อกตาม IP อย่างเดียว เพราะหลัง Docker/NAT ผู้ใช้ทั้งองค์กรอาจเห็นเป็น IP เดียวกัน"""

    def __init__(self):
        self._failures: dict[str, deque] = defaultdict(deque)

    @staticmethod
    def _keys(ip: str, username: str):
        user = (username or "").strip().lower()
        return f"ipuser:{ip}:{user}", f"user:{user}"

    def _recent(self, key: str, now: float) -> deque:
        window = settings.LOGIN_FAILURE_WINDOW_MINUTES * 60
        q = self._failures[key]
        while q and now - q[0] > window:
            q.popleft()
        return q

    def retry_after(self, ip: str, username: str, now: Optional[float] = None) -> int:
        """วินาทีที่ต้องรอก่อนลองใหม่ได้ (0 = ล็อกอินได้)"""
        now = time.monotonic() if now is None else now
        window = settings.LOGIN_FAILURE_WINDOW_MINUTES * 60
        wait = 0.0
        pair_key, user_key = self._keys(ip, username)
        for key, limit in ((pair_key, settings.LOGIN_MAX_FAILURES_PER_IP_USER),
                           (user_key, settings.LOGIN_MAX_FAILURES_PER_USER)):
            q = self._recent(key, now)
            if len(q) >= limit:
                # ปลดล็อกเมื่อครั้งที่ผิดซึ่งทำให้ถึงเพดานหลุดออกจากหน้าต่างเวลา
                wait = max(wait, window - (now - q[-limit]))
        return math.ceil(wait)

    def record_failure(self, ip: str, username: str, now: Optional[float] = None) -> None:
        now = time.monotonic() if now is None else now
        for key in self._keys(ip, username):
            self._recent(key, now).append(now)

    def reset(self, ip: str, username: str) -> None:
        for key in self._keys(ip, username):
            self._failures.pop(key, None)


login_throttle = LoginThrottle()


def check_login_allowed(request: Request, username: str) -> str:
    """เรียกก่อนตรวจรหัสผ่าน — ถูกล็อกอยู่ = 429 (ไม่ตรวจรหัสเลย) คืน IP ไว้ใช้บันทึกผลต่อ"""
    ip = _client_ip(request)
    wait = login_throttle.retry_after(ip, username)
    if wait > 0:
        minutes = max(1, math.ceil(wait / 60))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"เข้าสู่ระบบผิดหลายครั้งเกินไป บัญชีนี้ถูกล็อกชั่วคราว กรุณาลองใหม่ในอีก {minutes} นาที",
            headers={"Retry-After": str(wait)},
        )
    return ip
