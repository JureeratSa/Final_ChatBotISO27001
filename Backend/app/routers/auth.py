"""
TUH Chatbot AI — Auth Router
Endpoints: /api/auth/login, /api/auth/refresh, /api/auth/logout, /api/auth/me
ครอบคลุมการ Manage Admin Users (GET/POST/PUT/DELETE /api/auth/users)
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import (
    verify_password, hash_password, generate_token_pair,
    verify_access_token, verify_refresh_token, create_access_token,
    verify_legacy_password
)
from app.models.models import User
from app.schemas.schemas import (
    LoginRequest, TokenResponse, RefreshRequest, AccessTokenResponse,
    UserCreate, UserUpdate, UserResponse
)
from app.services.department_scope import SUPER_ADMIN_ROLE
from app.services.audit_service import set_audit


def _require_department(role: str, department) -> None:
    """แอดมินแผนกต้องมีแผนกเสมอ — ไม่มีแผนกจะมองไม่เห็นข้อมูลอะไรเลยในระบบ"""
    if role != SUPER_ADMIN_ROLE and not (department or "").strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="กรุณาระบุแผนก/หมวดงานของแอดมิน (แอดมินจะเห็นเฉพาะข้อมูลของแผนกนี้)"
        )

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer()


# ─── Helper: Get current user from token ──────────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Dependency: ตรวจสอบ JWT Access Token และดึง User จาก DB"""
    try:
        payload = verify_access_token(credentials.credentials)
        username: str = payload.get("sub")
        if not username:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )

    result = await db.execute(select(User).where(User.username == username, User.is_active == True))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


# ─── Login ────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Admin Login — คืน Access Token + Refresh Token"""
    set_audit(request, action="login_failed", username=body.username)
    result = await db.execute(
        select(User).where(User.username == body.username, User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        set_audit(request, detail={"reason": "invalid_credentials"})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง"
        )

    set_audit(request, action="login_success")
    tokens = generate_token_pair(user.username)
    return TokenResponse(
        **tokens,
        username=user.username,
        display_name=user.display_name,
        role=user.role,
        department=user.department
    )


# ─── Refresh Token ────────────────────────────────────────────────────────────

@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """ต่ออายุ Access Token โดยใช้ Refresh Token"""
    try:
        payload = verify_refresh_token(body.refresh_token)
        username = payload.get("sub")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    result = await db.execute(
        select(User).where(User.username == username, User.is_active == True)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    access_token = create_access_token({"sub": user.username})
    return AccessTokenResponse(access_token=access_token)


# ─── Current User Info ────────────────────────────────────────────────────────

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """ดึงข้อมูล Admin ที่ login อยู่"""
    return current_user


# ─── Admin User Management ────────────────────────────────────────────────────

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """ดูรายชื่อ Admin Users ทั้งหมด"""
    if current_user.role != "System Administrator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="คุณไม่มีสิทธิ์เข้าถึงหรือจัดการข้อมูลผู้ใช้งานระบบ"
        )
    result = await db.execute(select(User).order_by(User.created_at))
    return result.scalars().all()


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """สร้าง Admin User ใหม่"""
    if current_user.role != "System Administrator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="คุณไม่มีสิทธิ์เข้าถึงหรือจัดการข้อมูลผู้ใช้งานระบบ"
        )
    # ตรวจสอบว่า username ซ้ำหรือไม่
    result = await db.execute(select(User).where(User.username == body.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username นี้มีอยู่แล้วในระบบ")
    _require_department(body.role, body.department)

    new_user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        display_name=body.display_name,
        role=body.role,
        department=(body.department or "").strip() or None
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    set_audit(request, detail={"target_user": new_user.username, "role": new_user.role,
                               "department": new_user.department})
    return new_user


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    body: UserUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """แก้ไข Admin User"""
    if current_user.role != "System Administrator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="คุณไม่มีสิทธิ์เข้าถึงหรือจัดการข้อมูลผู้ใช้งานระบบ"
        )
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบผู้ใช้นี้")

    _require_department(
        body.role if body.role is not None else user.role,
        body.department if body.department is not None else user.department,
    )
    # บันทึกว่าเปลี่ยนสิทธิ์/สถานะอะไร (ค่าเดิม → ค่าใหม่) ลง audit log — รหัสผ่านบันทึกแค่ว่ามีการเปลี่ยน
    changes = {}
    for field in ("display_name", "role", "department", "is_active"):
        new_value = getattr(body, field)
        if new_value is not None and new_value != getattr(user, field):
            changes[field] = [getattr(user, field), new_value]
    if body.password is not None:
        changes["password"] = "changed"
    set_audit(request, detail={"target_user": user.username, "changes": changes})

    if body.display_name is not None:
        user.display_name = body.display_name
    if body.password is not None:
        user.password_hash = hash_password(body.password)
    if body.role is not None:
        user.role = body.role
    if body.department is not None:
        user.department = body.department.strip() or None
    if body.is_active is not None:
        user.is_active = body.is_active

    await db.commit()
    await db.refresh(user)
    return user


@router.get("/departments", response_model=List[str])
async def list_departments(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """รายชื่อแผนกที่มีอยู่ (จากบัญชีแอดมินแผนก) — ใช้เป็นตัวเลือกตอนกรอง/ย้ายแผนกใน AdminWeb"""
    if current_user.role != SUPER_ADMIN_ROLE:
        return [current_user.department] if current_user.department else []
    rows = await db.execute(
        select(User.department).where(User.role != SUPER_ADMIN_ROLE, User.department.is_not(None)).distinct()
    )
    return sorted(d for d in rows.scalars().all() if d and d.strip())


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """ลบ Admin User (ป้องกันลบตัวเอง)"""
    if current_user.role != "System Administrator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="คุณไม่มีสิทธิ์เข้าถึงหรือจัดการข้อมูลผู้ใช้งานระบบ"
        )
    if current_user.id == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ไม่สามารถลบบัญชีของตัวเองได้")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบผู้ใช้นี้")

    set_audit(request, detail={"target_user": user.username, "role": user.role, "department": user.department})
    await db.delete(user)
    await db.commit()
