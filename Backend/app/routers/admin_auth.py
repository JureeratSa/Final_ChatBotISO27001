"""
TUH Chatbot AI — Admin Router: Auth (login / password update)
แยกออกมาจาก Backend/app/routers/admin.py

หมายเหตุ: ชื่อ "Legacy" เดิมทำให้เข้าใจผิดว่าเป็นโค้ดเก่าที่ไม่ได้ใช้แล้ว แต่จริงๆ แล้ว
POST /login คือ endpoint ล็อกอินจริงที่ AdminWeb เรียกใช้อยู่ (ยืนยันจาก AdminWeb/src/App.jsx)
ห้ามรวมเข้ากับ /api/auth/login หรือเปลี่ยนพฤติกรรม
"""
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.rate_limit import check_login_allowed, login_throttle
from fastapi.security import HTTPAuthorizationCredentials
from app.core.security import verify_password, verify_user_password, create_access_token, verify_access_token
from app.core.token_revocation import revoke
from app.routers.auth import bump_token_version, get_current_user, security as bearer_scheme
from app.models.models import User, AdminAuditLog
from app.services.audit_service import set_audit
from app.services.department_scope import require_super_admin
from app.services.password_policy import password_problems, password_status

router = APIRouter(prefix="/api/admin", tags=["admin"])


class LegacyLoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def legacy_admin_login(
    payload: LegacyLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    # บันทึกทุกความพยายามล็อกอิน (audit log) — ไม่เก็บรหัสผ่านที่พิมพ์มา
    set_audit(request, action="login_failed", username=payload.username)
    try:
        ip = check_login_allowed(request, payload.username)
    except HTTPException:
        set_audit(request, detail={"reason": "too_many_failures"})
        raise
    result = await db.execute(select(User).where(User.username == payload.username))
    user = result.scalar_one_or_none()

    if not verify_user_password(payload.password, user):
        login_throttle.record_failure(ip, payload.username)
        set_audit(request, detail={"reason": "invalid_credentials"})
        raise HTTPException(status_code=401, detail="ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
    login_throttle.reset(ip, payload.username)

    if not user.is_active:
        set_audit(request, detail={"reason": "account_disabled"})
        raise HTTPException(status_code=400, detail="บัญชีนี้ถูกระงับการใช้งาน")
    set_audit(request, action="login_success")

    # Generate JWT token — tv = รุ่นของ token (เปลี่ยนรหัสผ่านแล้ว token รุ่นเก่าใช้ไม่ได้)
    token = create_access_token(data={"sub": user.username, "tv": user.token_version or 0})

    return {
        "success": True,
        "token": token,
        "username": user.username,
        "role": user.role,
        "name": user.display_name,
        "department": user.department,
        **password_status(user.password_changed_at)
    }


class PasswordUpdatePayload(BaseModel):
    new_password: str


@router.post("/password/update")
async def update_password(
    payload: PasswordUpdatePayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """เปลี่ยนรหัสผ่านส่วนตัวของผู้ดูแลระบบที่กำลังล็อกอินอยู่ (ทำได้แม้รหัสผ่านหมดอายุ)
    สำเร็จแล้ว token เดิมทุกตัวใช้ไม่ได้ — AdminWeb พาไปล็อกอินใหม่ด้วยรหัสผ่านใหม่"""
    problems = password_problems(payload.new_password, current_user.username)
    if verify_password(payload.new_password, current_user.password_hash):
        problems.append("ต้องไม่ซ้ำกับรหัสผ่านเดิม")
    if problems:
        raise HTTPException(status_code=400, detail="รหัสผ่านไม่ผ่านเกณฑ์: " + ", ".join(problems))

    from datetime import datetime, timezone
    from app.core.security import hash_password
    current_user.password_hash = hash_password(payload.new_password)
    current_user.password_changed_at = datetime.now(timezone.utc)
    bump_token_version(current_user)
    await db.commit()
    return {"success": True, "detail": "เปลี่ยนรหัสผ่านสำเร็จแล้ว กรุณาเข้าสู่ระบบใหม่ด้วยรหัสผ่านใหม่"}


@router.post("/logout")
async def admin_logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    """บันทึกการออกจากระบบ + ยกเลิก token ใบที่ใช้ออก (ใช้ต่อไม่ได้แม้ยังไม่หมดอายุ — ดู core/token_revocation.py)
    ยกเลิกเฉพาะใบนี้ เครื่องอื่นของแอดมินคนเดียวกันไม่ถูกเด้งออก
    เรียกทั้งตอนกดออกเองและตอนระบบออกให้อัตโนมัติเมื่อไม่มีการใช้งาน (?reason=idle)"""
    token_payload = verify_access_token(credentials.credentials)  # ผ่าน get_current_user มาแล้ว = ถูกต้อง
    revoke(token_payload.get("jti"), float(token_payload.get("exp", 0)))
    reason = request.query_params.get("reason")
    set_audit(request, action="logout", username=current_user.username,
              detail={"reason": reason[:50]} if reason else None)
    return {"success": True}


@router.get("/audit-logs")
async def list_audit_logs(
    limit: int = 1000,
    action: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """บันทึกการเข้าใช้งานของแอดมิน (ใหม่ไปเก่า) — SuperAdmin เท่านั้น"""
    require_super_admin(current_user, "เฉพาะ SuperAdmin เท่านั้นที่ดูบันทึกการเข้าใช้งานได้")
    query = select(AdminAuditLog).order_by(AdminAuditLog.timestamp.desc(), AdminAuditLog.id.desc())
    if action:
        query = query.where(AdminAuditLog.action == action)
    rows = (await db.execute(query.limit(max(1, min(limit, 10000))))).scalars().all()
    return [{
        "id": r.id,
        "timestamp": r.timestamp.strftime("%Y-%m-%d %H:%M:%S") if r.timestamp else "",
        "username": r.username,
        "department": r.department,
        "action": r.action,
        "method": r.method,
        "path": r.path,
        "status_code": r.status_code,
        "ip_address": r.ip_address,
        "user_agent": r.user_agent,
        "detail": json.loads(r.detail) if r.detail else None,
    } for r in rows]
