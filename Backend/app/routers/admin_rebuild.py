"""
TUH Chatbot AI — Admin Router: Rebuild
แยกออกมาจาก Backend/app/routers/admin.py
Business logic (_trigger_rebuild_background ฯลฯ) ย้ายไปที่ app/services/rebuild_service.py

หมายเหตุ: test_rebuild_status.py monkeypatch `_trigger_rebuild_background` โดยแพตช์ที่
โมดูลนี้ (admin_rebuild) ไม่ใช่ที่ rebuild_service — ดู comment ใน rebuild_service.py
"""
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.routers.auth import get_current_user
from app.models.models import User, SystemSettings
from app.schemas.schemas import RebuildStatus
from app.services.rebuild_service import _get_or_create_settings_row, _trigger_rebuild_background

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/rebuild", response_model=RebuildStatus)
async def trigger_rebuild(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Trigger การ Rebuild Vector Index ใน Background"""
    cfg = await _get_or_create_settings_row(db)
    if cfg.rebuild_status == "processing":
        return RebuildStatus(status="processing", message="กำลังประมวลผลอยู่แล้ว กรุณารอสักครู่")

    cfg.rebuild_status = "processing"
    cfg.rebuild_message = "กำลังเริ่มประมวลผล..."
    await db.commit()

    background_tasks.add_task(_trigger_rebuild_background)
    return RebuildStatus(status="processing", message="เริ่มประมวลผล Background Task แล้ว")


@router.get("/rebuild/status", response_model=RebuildStatus)
async def get_rebuild_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(SystemSettings).where(SystemSettings.id == "config"))
    cfg = result.scalar_one_or_none()
    if not cfg:
        return RebuildStatus(status="idle", message="ยังไม่ได้ประมวลผล")
    return RebuildStatus(status=cfg.rebuild_status, message=cfg.rebuild_message or "", duration=cfg.last_build_duration)
