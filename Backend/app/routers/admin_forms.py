"""
TUH Chatbot AI — Admin Router: Forms
แยกออกมาจาก Backend/app/routers/admin.py
_parse_pages() ย้ายไปที่ app/services/form_service.py
"""
import time
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.config import settings
from app.core.security import safe_path, safe_filename
from app.routers.auth import get_current_user
from app.models.models import User, Form as FormModel
from app.schemas.schemas import FormResponse, FormCreate
from app.services.form_service import _parse_pages
from app.services.department_scope import (
    check_department, department_column_filter, owner_department_for, require_super_admin, scope_department
)
from app.services.audit_service import add_audit_detail

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _check_form_access(form: FormModel, user: User) -> None:
    add_audit_detail(form=form.name, form_file=form.filename, department=form.department)
    check_department(form.department, user, "คุณไม่มีสิทธิ์จัดการแบบฟอร์มของแผนกอื่น")


@router.get("/forms", response_model=List[FormResponse])
async def get_forms(
    department: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """รายการแบบฟอร์มสำหรับหน้าจัดการใน AdminWeb — แอดมินแผนกเห็นเฉพาะของแผนกตัวเอง
    (เดิมเป็น public endpoint แต่มีแค่ AdminWeb เรียก — แชทบอทอ่านแบบฟอร์มจาก DB โดยตรง
    และดาวน์โหลดไฟล์ผ่าน /api/forms/download/... ซึ่งยังเป็น public เหมือนเดิม)"""
    query = select(FormModel)
    scope = department_column_filter(FormModel.department, scope_department(current_user, department))
    if scope is not None:
        query = query.where(scope)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/forms", response_model=FormResponse, status_code=status.HTTP_201_CREATED)
async def create_form(
    body: FormCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    import uuid
    new_form = FormModel(
        id=str(uuid.uuid4()),
        name=body.name,
        filename=body.filename,
        page=body.page,
        download_link=body.download_link,
        department=owner_department_for(current_user, body.department)
    )
    db.add(new_form)
    add_audit_detail(form=new_form.name, form_file=new_form.filename, department=new_form.department)
    await db.commit()
    await db.refresh(new_form)
    return new_form


@router.delete("/forms/{form_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_form(
    form_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(FormModel).where(FormModel.id == form_id))
    form = result.scalar_one_or_none()
    if not form:
        raise HTTPException(status_code=404, detail="ไม่พบแบบฟอร์มนี้")
    _check_form_access(form, current_user)
    await db.delete(form)
    await db.commit()


class DeleteFormRequest(BaseModel):
    id: str


@router.post("/forms/delete")
async def delete_form_compatibility(
    payload: DeleteFormRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    form_id = payload.id
    result = await db.execute(select(FormModel).where(FormModel.id == form_id))
    form = result.scalar_one_or_none()
    if not form:
        raise HTTPException(status_code=404, detail="ไม่พบแบบฟอร์มนี้")
    _check_form_access(form, current_user)

    # Delete file from disk
    if form.filename:
        forms_dir = Path(settings.UPLOADS_DIR) / "forms"
        filepath = safe_path(forms_dir, form.filename)
        if filepath.exists():
            try:
                filepath.unlink()
            except Exception:
                pass

    await db.delete(form)
    await db.commit()
    return {"success": True}


@router.post("/forms/upload")
async def upload_form_compatibility(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from urllib.parse import unquote, quote

    form_name = unquote(request.headers.get("x-form-name", "").strip())
    filename = unquote(request.headers.get("x-file-name", "form.pdf").strip())
    page = unquote(request.headers.get("x-form-page", "").strip())

    add_audit_detail(form=form_name or None, form_file=filename or None, pages=page or None)
    if not form_name or not filename:
        raise HTTPException(status_code=400, detail="กรุณากรอกชื่อและเลือกไฟล์แบบฟอร์มให้ครบถ้วน")
    filename = safe_filename(filename)  # ป้องกัน Path Traversal จาก x-file-name header

    # ชื่อแบบฟอร์มซ้ำกัน = อัปเดตแบบฟอร์มเดิม — อัปเดตทับของแผนกอื่นไม่ได้ (เช็คก่อนเขียนไฟล์)
    result = await db.execute(select(FormModel).where(func.lower(FormModel.name) == func.lower(form_name)))
    existing_form = result.scalar_one_or_none()
    if existing_form:
        _check_form_access(existing_form, current_user)

    post_data = await request.body()

    forms_dir = Path(settings.UPLOADS_DIR) / "forms"
    forms_dir.mkdir(parents=True, exist_ok=True)

    ts = int(time.time())
    temp_filepath = forms_dir / f"_temp_{ts}_{filename}"

    with open(str(temp_filepath), "wb") as f:
        f.write(post_data)

    final_filename = f"{ts}_{filename}"
    final_filepath = forms_dir / final_filename

    if page:
        try:
            import fitz
            src_doc = fitz.open(str(temp_filepath))
            total = len(src_doc)
            page_indices = _parse_pages(page, total)

            if not page_indices:
                src_doc.close()
                if temp_filepath.exists():
                    temp_filepath.unlink()
                raise HTTPException(
                    status_code=400,
                    detail=f"หน้าที่ระบุ ({page}) ไม่อยู่ในไฟล์ PDF (มีทั้งหมด {total} หน้า)"
                )

            new_doc = fitz.open()
            for pi in page_indices:
                new_doc.insert_pdf(src_doc, from_page=pi, to_page=pi)
            new_doc.save(str(final_filepath))
            new_doc.close()
            src_doc.close()

            if temp_filepath.exists():
                temp_filepath.unlink()
        except HTTPException:
            raise
        except Exception as e:
            # Fallback
            if temp_filepath.exists():
                temp_filepath.rename(final_filepath)
    else:
        if temp_filepath.exists():
            temp_filepath.rename(final_filepath)

    # Save/Update in DB
    host_header = request.headers.get("host", "localhost:8000")
    download_link = f"http://{host_header}/api/forms/download/{quote(final_filename)}"

    if existing_form:
        # Delete old file
        if existing_form.filename:
            old_filepath = safe_path(forms_dir, existing_form.filename)
            if old_filepath.exists():
                try:
                    old_filepath.unlink()
                except Exception:
                    pass
        existing_form.filename = final_filename
        existing_form.page = page
        existing_form.download_link = download_link
        message = "อัปเดตแบบฟอร์มเดิมและอัปโหลดไฟล์ใหม่สำเร็จ"
    else:
        new_form = FormModel(
            id=f"form-{int(time.time() * 1000)}",
            name=form_name,
            filename=final_filename,
            page=page,
            download_link=download_link,
            department=owner_department_for(
                current_user, unquote(request.headers.get("x-form-department", "").strip())
            )
        )
        db.add(new_form)
        add_audit_detail(department=new_form.department)
        message = "บันทึกและอัปโหลดแบบฟอร์มสำเร็จ"

    try:
        await db.commit()
    except Exception:
        # บันทึกลงฐานข้อมูลไม่สำเร็จ — ลบไฟล์ที่เพิ่งเขียนทิ้ง ไม่ให้ค้างใน uploads/forms โดยไม่มีแถวอ้างถึง
        await db.rollback()
        if final_filepath.exists():
            final_filepath.unlink()
        raise

    return {"success": True, "message": message}


class UpdateFormDepartmentRequest(BaseModel):
    id: str
    department: Optional[str] = None  # None/"" = ยังไม่ระบุแผนก


@router.post("/forms/update_department")
async def update_form_department(
    payload: UpdateFormDepartmentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """ย้ายแบบฟอร์มไปแผนกอื่น — SuperAdmin เท่านั้น"""
    require_super_admin(current_user, "เฉพาะ SuperAdmin เท่านั้นที่ย้ายแผนกของแบบฟอร์มได้")
    result = await db.execute(select(FormModel).where(FormModel.id == payload.id))
    form = result.scalar_one_or_none()
    if not form:
        raise HTTPException(status_code=404, detail="ไม่พบแบบฟอร์มนี้")
    new_department = (payload.department or "").strip() or None
    add_audit_detail(form=form.name, from_department=form.department or "ยังไม่ระบุ",
                     to_department=new_department or "ยังไม่ระบุ")
    form.department = new_department
    await db.commit()
    return {"success": True, "department": form.department}
