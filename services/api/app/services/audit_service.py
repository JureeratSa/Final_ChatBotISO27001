"""
บันทึกการใช้งานของแอดมิน (audit log)

บันทึกการเข้าสู่ระบบ / ออกจากระบบ และทุกคำขอที่แก้ไขข้อมูล (POST/PUT/PATCH/DELETE) ของ AdminWeb
ลงตาราง admin_audit_logs เพื่อการตรวจสอบย้อนหลังและความมั่นคงปลอดภัย

- AuditLogMiddleware เป็นจุดเขียน log จุดเดียว: เขียนหลัง endpoint ทำงานเสร็จ (รู้ status code แล้ว)
- endpoint ที่ต้องการเพิ่มข้อมูล (ล็อกอิน, เปลี่ยนสิทธิ์ผู้ใช้) เรียก set_audit() ใส่ไว้ใน request.state
  ไม่ต้องเขียน DB เอง
- ไม่เก็บ request body เด็ดขาด (มีรหัสผ่าน/เนื้อหาเอกสาร) — เก็บแค่ method, path, ผลลัพธ์, IP, User-Agent
- บันทึกไม่สำเร็จต้องไม่ทำให้คำขอของแอดมินล้มตาม (log error แล้วปล่อยผ่าน)
"""
import json
import logging
from contextvars import ContextVar
from typing import Any, Dict, Optional

from fastapi import Request
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.security import verify_access_token
from app.models.models import AdminAuditLog, User

logger = logging.getLogger(__name__)

_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_AUDITED_PREFIXES = ("/api/admin/", "/api/auth/")
# ผู้ใช้แชทบอทส่ง feedback — ไม่ใช่การกระทำของแอดมิน
_SKIPPED_PATHS = {"/api/admin/feedback/submit"}

# dict ของคำขอปัจจุบัน (middleware สร้างใหม่ทุกคำขอ) — endpoint/service เติมข้อมูลผ่าน add_audit_detail()
# ได้โดยไม่ต้องรับ Request เป็นพารามิเตอร์ (middleware กับ endpoint ถือ dict ตัวเดียวกัน)
_current_audit: ContextVar[Optional[dict]] = ContextVar("current_audit", default=None)


def set_audit(request: Request, *, action: Optional[str] = None, username: Optional[str] = None,
              detail: Optional[Dict[str, Any]] = None) -> None:
    """ให้ endpoint ระบุประเภทเหตุการณ์/ผู้ใช้/รายละเอียดเพิ่มเติม — middleware เป็นคนเขียนลง DB"""
    audit = getattr(request.state, "audit", None)
    if audit is None:
        audit = {}
        request.state.audit = audit
    if action:
        audit["action"] = action
    if username:
        audit["username"] = username
    if detail:
        audit.setdefault("detail", {}).update(detail)


def add_audit_detail(**detail: Any) -> None:
    """เติมข้อมูลระบุรายการที่ถูกเพิ่ม/ลบ/แก้ (ชื่อไฟล์, หัวข้อประกาศ ฯลฯ) ลง log ของคำขอนี้
    ห้ามใส่รหัสผ่าน/เนื้อหาเอกสาร — ค่า None ถูกข้าม, นอกคำขอ HTTP (เช่นเทสที่เรียก service ตรง) ไม่ทำอะไร"""
    audit = _current_audit.get()
    if audit is None:
        return
    audit.setdefault("detail", {}).update({k: v for k, v in detail.items() if v is not None})


def _client_ip(request: Request) -> Optional[str]:
    # กติกาเดียวกับ rate limit: เชื่อ X-Forwarded-For เฉพาะเมื่ออยู่หลัง reverse proxy ของเรา (TRUST_PROXY_HEADERS)
    from app.core.rate_limit import _client_ip as request_client_ip
    ip = request_client_ip(request)
    return None if ip == "unknown" else ip


def _token_username(request: Request) -> Optional[str]:
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        return None
    try:
        return verify_access_token(auth[7:].strip()).get("sub")
    except ValueError:
        return None


def _should_audit(request: Request) -> bool:
    # ล็อกอิน/ออกจากระบบระบุ action เอง — คำขออ่านข้อมูล (GET) ที่แค่เติม detail ไม่นับ
    if (getattr(request.state, "audit", None) or {}).get("action"):
        return True
    path = request.url.path
    return (
        request.method in _WRITE_METHODS
        and path.startswith(_AUDITED_PREFIXES)
        and path not in _SKIPPED_PATHS
    )


async def write_audit_log(request: Request, status_code: int) -> None:
    from app.core.database import AsyncSessionLocal  # อ่านตอนเรียก เพื่อให้เทสสลับไป SQLite ได้

    audit = getattr(request.state, "audit", None) or {}
    username = audit.get("username") or _token_username(request)
    detail = dict(audit.get("detail") or {})
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        detail["x_forwarded_for"] = forwarded[:200]
    if request.url.query:
        detail["query"] = request.url.query[:500]

    async with AsyncSessionLocal() as session:
        user = None
        if username:
            user = (await session.execute(select(User).where(User.username == username))).scalar_one_or_none()
        session.add(AdminAuditLog(
            user_id=user.id if user else None,
            username=(username or None) and username[:100],
            department=user.department if user else None,
            action=audit.get("action") or "change",
            method=request.method,
            path=request.url.path[:500],
            status_code=status_code,
            ip_address=_client_ip(request),
            user_agent=(request.headers.get("user-agent") or "")[:500] or None,
            detail=json.dumps(detail, ensure_ascii=False) if detail else None,
        ))
        await session.commit()


class AuditLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        audit: dict = {}
        request.state.audit = audit
        token = _current_audit.set(audit)
        try:
            response = await call_next(request)
        finally:
            _current_audit.reset(token)
        if _should_audit(request):
            try:
                await write_audit_log(request, response.status_code)
            except Exception as e:  # log ล้มต้องไม่ทำให้คำขอของแอดมินล้มตาม
                logger.error("[Audit Log Error] %s %s: %s", request.method, request.url.path, e)
        return response
