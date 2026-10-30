"""
จัดการแบบฟอร์มดาวน์โหลด (หน้า "แบบฟอร์ม" ของ AdminWeb) — /api/admin/forms*
บอทแนบลิงก์แบบฟอร์มเมื่อคำตอบพูดถึงชื่อแบบฟอร์มนั้น; ผู้ใช้ดาวน์โหลดผ่าน /api/forms/download
"""
import logging
import time
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote, unquote

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.security import safe_filename, safe_path
from app.core.uploads import read_request_body, require_pdf
from app.models.models import Form, User
from app.schemas.schemas import FormResponse
from app.services.audit_service import add_audit_detail
from app.services.department_scope import (
    check_department, department_column_filter, owner_department_for, require_super_admin, scope_department,
)
from app.services.form_service import extract_pdf_pages, page_count

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["forms"])


class FormIdRequest(BaseModel):
    id: str


class UpdateFormDepartmentRequest(FormIdRequest):
    department: Optional[str] = None      # None/"" = ยังไม่ระบุแผนก


def forms_dir() -> Path:
    return Path(settings.UPLOADS_DIR) / "forms"


def _remove_file(filename: Optional[str]) -> None:
    if not filename:
        return
    path = safe_path(forms_dir(), filename)
    try:
        path.unlink(missing_ok=True)
    except OSError as e:
        logger.warning("[Forms] ลบไฟล์ %s ไม่สำเร็จ: %s", filename, e)


def _check_form_access(form: Form, user: User) -> None:
    add_audit_detail(form=form.name, form_file=form.filename, department=form.department)
    check_department(form.department, user, "คุณไม่มีสิทธิ์จัดการแบบฟอร์มของแผนกอื่น")


async def _get_form(db: AsyncSession, form_id: str) -> Form:
    form = (await db.execute(select(Form).where(Form.id == form_id))).scalar_one_or_none()
    if not form:
        raise HTTPException(status_code=404, detail="ไม่พบแบบฟอร์มนี้")
    return form


@router.get("/forms", response_model=List[FormResponse])
async def list_forms(department: Optional[str] = None,
                     current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    query = select(Form)
    scope = department_column_filter(Form.department, scope_department(current_user, department))
    if scope is not None:
        query = query.where(scope)
    return (await db.execute(query)).scalars().all()


@router.post("/forms/upload")
async def upload_form(request: Request, current_user: User = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)):
    """body = ไฟล์ PDF ดิบ, ข้อมูลอื่นส่งใน header: X-Form-Name, X-File-Name, X-Form-Page (เช่น "1-3,7"),
    X-Form-Department — ชื่อแบบฟอร์มซ้ำกับที่มีอยู่ = อัปเดตไฟล์ของแบบฟอร์มเดิม"""
    form_name = unquote(request.headers.get("x-form-name", "").strip())
    filename = unquote(request.headers.get("x-file-name", "form.pdf").strip())
    page = unquote(request.headers.get("x-form-page", "").strip())

    add_audit_detail(form=form_name or None, form_file=filename or None, pages=page or None)
    if not form_name or not filename:
        raise HTTPException(status_code=400, detail="กรุณากรอกชื่อและเลือกไฟล์แบบฟอร์มให้ครบถ้วน")
    filename = safe_filename(filename)
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="แบบฟอร์มรองรับเฉพาะไฟล์ PDF เท่านั้น")

    # อัปเดตทับแบบฟอร์มของแผนกอื่นไม่ได้ (เช็คก่อนเขียนไฟล์)
    existing = (await db.execute(
        select(Form).where(func.lower(Form.name) == func.lower(form_name))
    )).scalar_one_or_none()
    if existing:
        _check_form_access(existing, current_user)

    content = await read_request_body(request, settings.MAX_FORM_UPLOAD_MB * 1024 * 1024)
    require_pdf(content)

    forms_dir().mkdir(parents=True, exist_ok=True)
    ts = int(time.time())
    final_filename = f"{ts}_{filename}"
    final_path = forms_dir() / final_filename
    temp_path = forms_dir() / f"_temp_{ts}_{filename}"
    temp_path.write_bytes(content)

    # ระบุหน้า → เก็บเฉพาะหน้านั้น (ตัดหน้าไม่สำเร็จด้วยเหตุอื่น → เก็บทั้งไฟล์)
    try:
        if page and not extract_pdf_pages(temp_path, final_path, page):
            raise HTTPException(status_code=400,
                                detail=f"หน้าที่ระบุ ({page}) ไม่อยู่ในไฟล์ PDF (มีทั้งหมด {page_count(temp_path)} หน้า)")
    except HTTPException:
        temp_path.unlink(missing_ok=True)
        raise
    except Exception as e:
        logger.warning("[Forms] ตัดหน้า %s ไม่สำเร็จ เก็บทั้งไฟล์แทน: %s", page, e)
        final_path.unlink(missing_ok=True)
    if final_path.exists():
        temp_path.unlink(missing_ok=True)
    else:
        temp_path.rename(final_path)

    # เก็บเป็น path (ไม่ใส่ host) — UserWeb ต่อกับ origin ของ API เอง
    download_link = f"/api/forms/download/{quote(final_filename)}"
    if existing:
        _remove_file(existing.filename)
        existing.filename = final_filename
        existing.page = page
        existing.download_link = download_link
        message = "อัปเดตแบบฟอร์มเดิมและอัปโหลดไฟล์ใหม่สำเร็จ"
    else:
        department = unquote(request.headers.get("x-form-department", "").strip())
        form = Form(id=f"form-{int(time.time() * 1000)}", name=form_name, filename=final_filename, page=page,
                    download_link=download_link, department=owner_department_for(current_user, department))
        db.add(form)
        add_audit_detail(department=form.department)
        message = "บันทึกและอัปโหลดแบบฟอร์มสำเร็จ"

    try:
        await db.commit()
    except Exception:
        # บันทึกไม่สำเร็จ → ลบไฟล์ที่เพิ่งเขียน ไม่ให้ค้างโดยไม่มีแถวในฐานข้อมูลอ้างถึง
        await db.rollback()
        final_path.unlink(missing_ok=True)
        raise
    return {"success": True, "message": message}


@router.post("/forms/delete")
async def delete_form(payload: FormIdRequest, current_user: User = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)):
    form = await _get_form(db, payload.id)
    _check_form_access(form, current_user)
    _remove_file(form.filename)
    await db.delete(form)
    await db.commit()
    return {"success": True}


@router.post("/forms/update_department")
async def update_form_department(payload: UpdateFormDepartmentRequest,
                                 current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """ย้ายแบบฟอร์มไปแผนกอื่น — SuperAdmin เท่านั้น"""
    require_super_admin(current_user, "เฉพาะ SuperAdmin เท่านั้นที่ย้ายแผนกของแบบฟอร์มได้")
    form = await _get_form(db, payload.id)
    new_department = (payload.department or "").strip() or None
    add_audit_detail(form=form.name, from_department=form.department or "ยังไม่ระบุ",
                     to_department=new_department or "ยังไม่ระบุ")
    form.department = new_department
    await db.commit()
    return {"success": True, "department": form.department}
