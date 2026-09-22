"""
TUH Chatbot AI — Admin Router: Auth (login / password update)
แยกออกมาจาก Backend/app/routers/admin.py — Endpoint/logic เหมือนเดิมทุกตัวอักษร

หมายเหตุ: ชื่อ "Legacy" เดิมทำให้เข้าใจผิดว่าเป็นโค้ดเก่าที่ไม่ได้ใช้แล้ว แต่จริงๆ แล้ว
POST /login คือ endpoint ล็อกอินจริงที่ AdminWeb เรียกใช้อยู่ (ยืนยันจาก AdminWeb/src/App.jsx)
ห้ามรวมเข้ากับ /api/auth/login หรือเปลี่ยนพฤติกรรม
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.routers.auth import get_current_user
from app.models.models import User

router = APIRouter(prefix="/api/admin", tags=["admin"])


class LegacyLoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def legacy_admin_login(
    payload: LegacyLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.username == payload.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")

    if not user.is_active:
        raise HTTPException(status_code=400, detail="บัญชีนี้ถูกระงับการใช้งาน")

    # Generate JWT token
    token = create_access_token(data={"sub": user.username})

    return {
        "success": True,
        "token": token,
        "username": user.username,
        "role": user.role,
        "name": user.display_name
    }


class PasswordUpdatePayload(BaseModel):
    new_password: str


@router.post("/password/update")
async def update_password(
    payload: PasswordUpdatePayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """เปลี่ยนรหัสผ่านส่วนตัวของผู้ดูแลระบบที่กำลังล็อกอินอยู่"""
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=400, detail="รหัสผ่านต้องมีความยาวอย่างน้อย 8 ตัวอักษร")

    from app.core.security import hash_password
    current_user.password_hash = hash_password(payload.new_password)
    await db.commit()
    return {"success": True, "detail": "เปลี่ยนรหัสผ่านสำเร็จแล้ว"}
