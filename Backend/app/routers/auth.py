"""
TUH Chatbot AI — Auth Router
Endpoints: /api/auth/login, /api/auth/refresh, /api/auth/logout, /api/auth/me
ครอบคลุมการ Manage Admin Users (GET/POST/PUT/DELETE /api/auth/users)
"""
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import null, select

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
from app.services.password_policy import (
    password_status, token_issued_before_password_change, validate_password
)
from app.services.user_import import build_template, generate_password, parse_rows

# คำขอที่แอดมินรหัสผ่านหมดอายุยังทำได้ — นอกนั้นต้องเปลี่ยนรหัสผ่านก่อน
_ALLOWED_WHEN_PASSWORD_EXPIRED = {"/api/admin/password/update", "/api/admin/logout"}
PASSWORD_EXPIRED_DETAIL = "PASSWORD_EXPIRED: รหัสผ่านหมดอายุ (ครบ 90 วัน) กรุณาเปลี่ยนรหัสผ่านที่หน้าโปรไฟล์ก่อนใช้งาน"


def _require_department(role: str, department) -> None:
    """แอดมินแผนกต้องมีแผนกเสมอ — ไม่มีแผนกจะมองไม่เห็นข้อมูลอะไรเลยในระบบ"""
    if role != SUPER_ADMIN_ROLE and not (department or "").strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="กรุณาระบุแผนก/หมวดงานของแอดมิน (แอดมินจะเห็นเฉพาะข้อมูลของแผนกนี้)"
        )

def _require_super_admin(current_user: User) -> None:
    if current_user.role != SUPER_ADMIN_ROLE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="คุณไม่มีสิทธิ์เข้าถึงหรือจัดการข้อมูลผู้ใช้งานระบบ"
        )

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer()


# ─── Helper: Get current user from token ──────────────────────────────────────

async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Dependency: ตรวจสอบ JWT Access Token และดึง User จาก DB
    + ตัด token ที่ออกก่อนเปลี่ยนรหัสผ่าน และล็อกแอดมินที่รหัสผ่านหมดอายุไว้แค่การเปลี่ยนรหัส"""
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
    if token_issued_before_password_change(payload.get("iat"), user.password_changed_at):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="รหัสผ่านถูกเปลี่ยนแล้ว กรุณาเข้าสู่ระบบใหม่")
    if (password_status(user.password_changed_at)["password_expired"]
            and request.url.path not in _ALLOWED_WHEN_PASSWORD_EXPIRED):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=PASSWORD_EXPIRED_DETAIL)
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
        department=user.department,
        **password_status(user.password_changed_at)
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
    if token_issued_before_password_change(payload.get("iat"), user.password_changed_at):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="รหัสผ่านถูกเปลี่ยนแล้ว กรุณาเข้าสู่ระบบใหม่")

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


MAX_IMPORT_FILE_BYTES = 2 * 1024 * 1024


async def _existing_departments(db: AsyncSession) -> List[str]:
    rows = await db.execute(
        select(User.department).where(User.role != SUPER_ADMIN_ROLE, User.department.is_not(None)).distinct()
    )
    return sorted(d for d in rows.scalars().all() if d and d.strip())


@router.get("/users/import/template")
async def download_user_import_template(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """ไฟล์ Excel template สำหรับนำเข้าบัญชีแอดมินหลายคน (มีรายชื่อแผนกปัจจุบันในชีตวิธีกรอก)"""
    _require_super_admin(current_user)
    content = build_template(await _existing_departments(db))
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="admin_import_template.xlsx"'},
    )


@router.post("/users/import")
async def import_users(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """นำเข้าบัญชีแอดมินจาก Excel + สร้างรหัสผ่านเริ่มต้นให้ทุกคน (ดู app/services/user_import.py)
    มีแถวผิดแม้แถวเดียว → ไม่สร้างใครเลย คืน errors ให้แก้ไฟล์ — สำเร็จ → คืนรหัสผ่านเริ่มต้น (แสดงครั้งเดียว)"""
    _require_super_admin(current_user)
    content = await file.read(MAX_IMPORT_FILE_BYTES + 1)
    if len(content) > MAX_IMPORT_FILE_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ไฟล์ใหญ่เกิน 2 MB")
    try:
        rows, errors = parse_rows(content)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if rows:
        existing = await db.execute(select(User.username).where(User.username.in_([r["username"] for r in rows])))
        taken = {u.lower() for u in existing.scalars().all()}  # MySQL เทียบ username แบบไม่สนตัวพิมพ์
        for r in [r for r in rows if r["username"].lower() in taken]:
            errors.append({"row": r["row"], "username": r["username"], "message": "Username นี้มีอยู่แล้วในระบบ"})
            rows.remove(r)
    if errors or not rows:
        errors.sort(key=lambda e: e["row"])
        return {"created": [], "errors": errors or [{"row": None, "username": "", "message": "ไม่พบรายชื่อในไฟล์"}]}

    known = set(await _existing_departments(db))
    created = []
    for r in rows:
        password = generate_password(r["username"])
        db.add(User(
            username=r["username"],
            # bcrypt ช้าโดยตั้งใจ (~0.2 วิ/คน) — ทำใน threadpool ไม่ให้ค้าง event loop ตอนนำเข้าหลายสิบคน
            password_hash=await run_in_threadpool(hash_password, password),
            display_name=r["display_name"],
            role=r["role"],
            department=r["department"],
            # NULL = บังคับเปลี่ยนรหัสผ่านตอนล็อกอินครั้งแรก — ต้องใช้ null() เพราะ None เฉยๆ
            # SQLAlchemy ตัดออกจาก INSERT แล้วไปใช้ server_default now() แทน
            password_changed_at=null(),
        ))
        created.append({**r, "password": password})
    await db.commit()

    set_audit(request, detail={"imported_users": [r["username"] for r in created]})
    new_departments = sorted({r["department"] for r in created if r["department"] and r["department"] not in known})
    return {"created": created, "errors": [], "new_departments": new_departments}


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
        try:
            validate_password(body.password, user.username)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        user.password_hash = hash_password(body.password)
        # SuperAdmin ตั้งรหัสให้ = รหัสใหม่ เริ่มนับอายุ 90 วันใหม่ (token เดิมของบัญชีนั้นใช้ไม่ได้อีก)
        user.password_changed_at = datetime.now(timezone.utc)
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
