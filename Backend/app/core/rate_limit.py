"""
TUH Chatbot AI — Rate Limiting (best-effort, in-memory)
จำกัดจำนวน request ต่อ IP สำหรับ endpoint สาธารณะที่แพง (เช่น /api/chat, /api/search)
ซึ่งไม่มีการจำกัดไว้เลยมาก่อน ทำให้ยิงรัวๆ ได้ไม่จำกัด เปลืองค่า LLM API และโหลด CPU ของ retriever

หมายเหตุ: เก็บ state เป็น dict ใน memory ของ process เดียว ถ้ารัน uvicorn หลาย worker
(--workers > 1) แต่ละ worker จะนับแยกกัน ลิมิตจริงจะสูงกว่าที่ตั้งไว้ตามจำนวน worker
ถ้าต้องการความแม่นยำระดับ production ควรย้ายไปใช้ Redis แทน แต่สำหรับสเกลปัจจุบัน (single worker
ตาม run_backend.py) เพียงพอที่จะกันการยิงรัวจาก IP เดียวได้
"""
import time
from collections import defaultdict, deque
from fastapi import Request, HTTPException, status

from app.core.config import settings

_hits: dict[str, deque] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def rate_limit_dependency(request: Request):
    """FastAPI dependency: raise 429 ถ้า IP นี้ยิงเกิน RATE_LIMIT_REQUESTS ครั้งใน RATE_LIMIT_WINDOW_SECONDS วินาที"""
    ip = _client_ip(request)
    now = time.monotonic()
    window = settings.RATE_LIMIT_WINDOW_SECONDS
    limit = settings.RATE_LIMIT_REQUESTS

    hits = _hits[ip]
    while hits and now - hits[0] > window:
        hits.popleft()

    if len(hits) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"ส่งคำขอถี่เกินไป กรุณารอสักครู่แล้วลองใหม่ (จำกัด {limit} ครั้ง / {window} วินาที)"
        )
    hits.append(now)
