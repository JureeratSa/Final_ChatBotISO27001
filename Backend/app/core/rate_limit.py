"""
TUH Chatbot AI — Rate Limiting (In-Memory Sliding Window)
ป้องกันการโจมตีแบบ DoS/Brute-force และจำกัดความถี่การยิงคำขอต่อ IP สำหรับ Endpoint สาธารณะ
(เช่น /api/chat, /api/search) เพื่อป้องกันค่าใช้จ่าย LLM API บานปลาย
"""
import time
from collections import defaultdict, deque
from fastapi import Request, HTTPException, status

from app.core.config import settings

# ที่เก็บประวัติ Timestamp การส่งคำขอแยกตาม IP: { "192.168.1.1": deque([ts1, ts2, ...]) }
_hits: dict[str, deque] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    """
    ดึง IP Address จริงของ Client
    - ตรวจสอบ Header 'X-Forwarded-For' ก่อน (กรณีอยู่หลัง Reverse Proxy / Nginx / Load Balancer)
    - หากไม่มี จะใช้ request.client.host
    """
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


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

    hits = _hits[ip]
    
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

