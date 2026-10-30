"""
Dependency ที่ endpoint ฝั่งแอดมินใช้ร่วมกัน — ตรวจ token แล้วคืนผู้ใช้ที่ล็อกอินอยู่

ใช้แบบนี้: current_user: User = Depends(get_current_user)
"""
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_access_token
from app.core.token_revocation import is_revoked
from app.models.models import User
from app.services.password_policy import password_status, token_issued_before_password_change

bearer_scheme = HTTPBearer()

# รหัสผ่านหมดอายุแล้วยังเรียกได้แค่ 2 endpoint นี้ (ต้องเปลี่ยนรหัสก่อนใช้อย่างอื่น)
ALLOWED_WHEN_PASSWORD_EXPIRED = {"/api/admin/password/update", "/api/admin/logout"}
PASSWORD_EXPIRED_DETAIL = "PASSWORD_EXPIRED: รหัสผ่านหมดอายุ (ครบ 90 วัน) กรุณาเปลี่ยนรหัสผ่านที่หน้าโปรไฟล์ก่อนใช้งาน"


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail,
                         headers={"WWW-Authenticate": "Bearer"})


def token_is_outdated(payload: dict, user: User) -> bool:
    """token ออกก่อนการเปลี่ยนรหัสผ่านครั้งล่าสุด (tv = token_version ตอนออก token)"""
    return (int(payload.get("tv") or 0) != (user.token_version or 0)
            or token_issued_before_password_change(payload.get("iat"), user.password_changed_at))


def bump_token_version(user: User) -> None:
    """เรียกทุกครั้งที่เปลี่ยนรหัสผ่าน — token ทุกใบที่ออกก่อนหน้าใช้ไม่ได้ทันที"""
    user.token_version = (user.token_version or 0) + 1


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = verify_access_token(credentials.credentials)
    except ValueError:
        raise _unauthorized("token ไม่ถูกต้องหรือหมดอายุ กรุณาเข้าสู่ระบบใหม่")
    if not payload.get("sub"):
        raise _unauthorized("token ไม่ถูกต้อง")
    if is_revoked(payload.get("jti")):
        raise _unauthorized("ออกจากระบบแล้ว กรุณาเข้าสู่ระบบใหม่")

    user = (await db.execute(
        select(User).where(User.username == payload["sub"], User.is_active == True)  # noqa: E712
    )).scalar_one_or_none()
    if not user:
        raise _unauthorized("ไม่พบบัญชีนี้หรือบัญชีถูกระงับ")
    if token_is_outdated(payload, user):
        raise _unauthorized("รหัสผ่านถูกเปลี่ยนแล้ว กรุณาเข้าสู่ระบบใหม่")
    if (password_status(user.password_changed_at)["password_expired"]
            and request.url.path not in ALLOWED_WHEN_PASSWORD_EXPIRED):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=PASSWORD_EXPIRED_DETAIL)
    return user
