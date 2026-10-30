"""
ล็อกอิน/ออกจากระบบของแอดมิน + เปลี่ยนรหัสผ่านตัวเอง + ดูบันทึกการเข้าใช้งาน — /api/admin/*
(จัดการบัญชีของคนอื่นอยู่ที่ api/users.py)
"""
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import bearer_scheme, bump_token_version, get_current_user
from app.core.database import get_db
from app.core.rate_limit import check_login_allowed, login_throttle
from app.core.security import (
    create_access_token, hash_password, verify_access_token, verify_password, verify_user_password,
)
from app.core.token_revocation import revoke
from app.models.models import AdminAuditLog, User
from app.services.audit_service import set_audit
from app.services.department_scope import require_super_admin
from app.services.password_policy import password_problems, password_status
from app.utils.timeutil import thai_str

router = APIRouter(prefix="/api/admin", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    # บันทึกทุกครั้งที่พยายามล็อกอินลง audit log (ตั้งเป็น failed ไว้ก่อน สำเร็จค่อยเปลี่ยน) — ไม่เก็บรหัสผ่าน
    set_audit(request, action="login_failed", username=payload.username)
    try:
        ip = check_login_allowed(request, payload.username)
    except HTTPException:
        set_audit(request, detail={"reason": "too_many_failures"})
        raise
    user = (await db.execute(select(User).where(User.username == payload.username))).scalar_one_or_none()

    if not verify_user_password(payload.password, user):
        login_throttle.record_failure(ip, payload.username)
        set_audit(request, detail={"reason": "invalid_credentials"})
        raise HTTPException(status_code=401, detail="ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
    login_throttle.reset(ip, payload.username)

    if not user.is_active:
        set_audit(request, detail={"reason": "account_disabled"})
        raise HTTPException(status_code=400, detail="บัญชีนี้ถูกระงับการใช้งาน")
    set_audit(request, action="login_success")

    # tv = รุ่นของ token — เปลี่ยนรหัสผ่านแล้ว token รุ่นเก่าใช้ไม่ได้
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

    current_user.password_hash = hash_password(payload.new_password)
    current_user.password_changed_at = datetime.now(timezone.utc)
    bump_token_version(current_user)
    await db.commit()
    return {"success": True, "detail": "เปลี่ยนรหัสผ่านสำเร็จแล้ว กรุณาเข้าสู่ระบบใหม่ด้วยรหัสผ่านใหม่"}


@router.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    """ยกเลิก token ใบนี้ (ใช้ต่อไม่ได้แม้ยังไม่หมดอายุ) — เครื่องอื่นของแอดมินคนเดียวกันไม่ถูกเด้งออก
    AdminWeb เรียกทั้งตอนกดออกเองและตอนออกอัตโนมัติเมื่อไม่ได้ใช้งาน (?reason=idle)"""
    token_payload = verify_access_token(credentials.credentials)   # get_current_user ตรวจแล้วว่าถูกต้อง
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
        "timestamp": thai_str(r.timestamp) or "",
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
