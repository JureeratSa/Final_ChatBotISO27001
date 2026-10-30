"""สั่งสร้างดัชนีค้นหาใหม่ทั้งคลัง (ปุ่ม Rebuild ใน AdminWeb) — POST /api/admin/rebuild"""
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import User
from app.schemas.schemas import RebuildStatus
from app.services.department_scope import require_super_admin
from app.services.rebuild_service import get_or_create_settings_row, rebuild_in_background

router = APIRouter(prefix="/api/admin", tags=["rebuild"])


@router.post("/rebuild", response_model=RebuildStatus)
async def trigger_rebuild(background: BackgroundTasks,
                          current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """SuperAdmin เท่านั้น — การอนุมัติ/เปิด/ปิดเอกสารสั่ง rebuild ให้เองอยู่แล้ว ปุ่มนี้ใช้เมื่อต้องการสร้างใหม่ทั้งหมด"""
    require_super_admin(current_user, "การ Rebuild ฐานข้อมูลทั้งระบบทำได้เฉพาะ SuperAdmin")
    cfg = await get_or_create_settings_row(db)
    if cfg.rebuild_status == "processing":
        return RebuildStatus(status="processing", message="กำลังประมวลผลอยู่แล้ว กรุณารอสักครู่")

    cfg.rebuild_status = "processing"
    cfg.rebuild_message = "กำลังเริ่มประมวลผล..."
    await db.commit()
    background.add_task(rebuild_in_background)
    return RebuildStatus(status="processing", message="เริ่มประมวลผล Background Task แล้ว")
