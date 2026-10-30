"""
จัดการบัญชีแอดมิน (SuperAdmin เท่านั้น) — /api/auth/users*, /api/auth/departments
"""
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import null, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import bump_token_version, get_current_user
from app.core.database import get_db
from app.core.security import hash_password
from app.models.models import User
from app.schemas.schemas import UserCreate, UserResponse, UserUpdate
from app.services.audit_service import set_audit
from app.services.department_scope import SUPER_ADMIN_ROLE, is_super_admin, require_super_admin
from app.services.password_policy import validate_password
from app.services.user_import import build_template, generate_password, parse_rows

router = APIRouter(prefix="/api/auth", tags=["users"])

NO_PERMISSION = "คุณไม่มีสิทธิ์เข้าถึงหรือจัดการข้อมูลผู้ใช้งานระบบ"
MAX_IMPORT_FILE_BYTES = 2 * 1024 * 1024


def _require_department(role: str, department) -> None:
    """แอดมินแผนกต้องมีแผนก — ไม่มีแผนกจะมองไม่เห็นข้อมูลอะไรเลย"""
    if role != SUPER_ADMIN_ROLE and not (department or "").strip():
        raise HTTPException(status_code=400, detail="กรุณาระบุแผนก/หมวดงานของแอดมิน (แอดมินจะเห็นเฉพาะข้อมูลของแผนกนี้)")


async def _get_user(db: AsyncSession, user_id: int) -> User:
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="ไม่พบผู้ใช้นี้")
    return user


async def _existing_departments(db: AsyncSession) -> List[str]:
    rows = await db.execute(
        select(User.department).where(User.role != SUPER_ADMIN_ROLE, User.department.is_not(None)).distinct()
    )
    return sorted(d for d in rows.scalars().all() if d and d.strip())


@router.get("/users", response_model=List[UserResponse])
async def list_users(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    require_super_admin(current_user, NO_PERMISSION)
    return (await db.execute(select(User).order_by(User.created_at))).scalars().all()


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(body: UserCreate, request: Request,
                      current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    require_super_admin(current_user, NO_PERMISSION)
    if (await db.execute(select(User).where(User.username == body.username))).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username นี้มีอยู่แล้วในระบบ")
    _require_department(body.role, body.department)

    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        display_name=body.display_name,
        role=body.role,
        department=(body.department or "").strip() or None,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    set_audit(request, detail={"target_user": user.username, "role": user.role, "department": user.department})
    return user


@router.get("/users/import/template")
async def download_import_template(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """ไฟล์ Excel สำหรับกรอกรายชื่อแอดมินหลายคน (ชีตวิธีกรอกมีรายชื่อแผนกปัจจุบัน)"""
    require_super_admin(current_user, NO_PERMISSION)
    return Response(
        content=build_template(await _existing_departments(db)),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="admin_import_template.xlsx"'},
    )


@router.post("/users/import")
async def import_users(request: Request, file: UploadFile = File(...),
                       current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """สร้างบัญชีจาก Excel พร้อมสุ่มรหัสผ่านเริ่มต้น (คืนรหัสให้ครั้งเดียว)
    มีแถวผิดแม้แถวเดียว → ไม่สร้างใครเลย แล้วคืนรายการที่ต้องแก้"""
    require_super_admin(current_user, NO_PERMISSION)
    content = await file.read(MAX_IMPORT_FILE_BYTES + 1)
    if len(content) > MAX_IMPORT_FILE_BYTES:
        raise HTTPException(status_code=400, detail="ไฟล์ใหญ่เกิน 2 MB")
    try:
        rows, errors = parse_rows(content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if rows:
        found = await db.execute(select(User.username).where(User.username.in_([r["username"] for r in rows])))
        taken = {u.lower() for u in found.scalars().all()}   # MySQL เทียบ username แบบไม่สนตัวพิมพ์
        for r in [r for r in rows if r["username"].lower() in taken]:
            errors.append({"row": r["row"], "username": r["username"], "message": "Username นี้มีอยู่แล้วในระบบ"})
            rows.remove(r)
    if errors or not rows:
        errors.sort(key=lambda e: e["row"])
        return {"created": [], "errors": errors or [{"row": None, "username": "", "message": "ไม่พบรายชื่อในไฟล์"}]}

    known_departments = set(await _existing_departments(db))
    created = []
    for r in rows:
        password = generate_password(r["username"])
        db.add(User(
            username=r["username"],
            password_hash=await run_in_threadpool(hash_password, password),  # bcrypt ช้า ไม่ให้ค้าง event loop
            display_name=r["display_name"],
            role=r["role"],
            department=r["department"],
            # NULL = ต้องเปลี่ยนรหัสตอนล็อกอินครั้งแรก (ใช้ null() เพราะ None จะถูกแทนด้วยค่า default ของคอลัมน์)
            password_changed_at=null(),
        ))
        created.append({**r, "password": password})
    await db.commit()

    set_audit(request, detail={"imported_users": [r["username"] for r in created]})
    new_departments = sorted({r["department"] for r in created if r["department"] and r["department"] not in known_departments})
    return {"created": created, "errors": [], "new_departments": new_departments}


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, body: UserUpdate, request: Request,
                      current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    require_super_admin(current_user, NO_PERMISSION)
    user = await _get_user(db, user_id)
    _require_department(body.role if body.role is not None else user.role,
                        body.department if body.department is not None else user.department)

    # บันทึกลง audit log ว่าเปลี่ยนอะไร (ค่าเดิม → ค่าใหม่) — รหัสผ่านบันทึกแค่ว่ามีการเปลี่ยน
    changes = {f: [getattr(user, f), getattr(body, f)] for f in ("display_name", "role", "department", "is_active")
               if getattr(body, f) is not None and getattr(body, f) != getattr(user, f)}
    if body.password is not None:
        changes["password"] = "changed"
    set_audit(request, detail={"target_user": user.username, "changes": changes})

    if body.password is not None:
        try:
            validate_password(body.password, user.username)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        user.password_hash = hash_password(body.password)
        user.password_changed_at = datetime.now(timezone.utc)   # เริ่มนับอายุรหัส 90 วันใหม่
        bump_token_version(user)                                 # token เดิมของบัญชีนี้ใช้ไม่ได้ทันที
    if body.display_name is not None:
        user.display_name = body.display_name
    if body.role is not None:
        user.role = body.role
    if body.department is not None:
        user.department = body.department.strip() or None
    if body.is_active is not None:
        user.is_active = body.is_active

    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, request: Request,
                      current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    require_super_admin(current_user, NO_PERMISSION)
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="ไม่สามารถลบบัญชีของตัวเองได้")
    user = await _get_user(db, user_id)
    set_audit(request, detail={"target_user": user.username, "role": user.role, "department": user.department})
    await db.delete(user)
    await db.commit()


@router.get("/departments", response_model=List[str])
async def list_departments(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """รายชื่อแผนก (ตัวเลือกตอนกรอง/ย้ายแผนก) — แอดมินแผนกเห็นแค่แผนกตัวเอง"""
    if not is_super_admin(current_user):
        return [current_user.department] if current_user.department else []
    return await _existing_departments(db)
