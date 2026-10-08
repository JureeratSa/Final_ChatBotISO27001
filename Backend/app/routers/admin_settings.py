"""
TUH Chatbot AI — Admin Router: Settings
แยกออกมาจาก Backend/app/routers/admin.py
ไม่แยก service layer (ตามแผน) — logic การอ่าน Authorization header เองแทนการใช้
get_current_user คงไว้ตรงนี้พร้อมคอมเมนต์อธิบายเหตุผลเดิม
"""
import json

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.config import settings
from app.routers.auth import get_current_user
from app.models.models import User, SystemSettings
from app.schemas.schemas import SettingsResponse, SettingsUpdate

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    # เปิดเผย gemini_api_key ตัวจริงเฉพาะ System Administrator เท่านั้น ให้สอดคล้องกับ
    # update_settings ด้านล่างที่บังคับ role นี้อยู่แล้ว (เดิมเช็คแค่ "login อยู่ไหม" ทำให้
    # admin role ธรรมดาที่แก้ค่านี้ไม่ได้ กลับอ่านค่าคีย์จริงได้)
    # หมายเหตุ: endpoint นี้ต้องรองรับผู้เรียกแบบไม่ login ด้วย (ดึงค่า default มาแสดง) จึง
    # parse Authorization header เองแทนการบังคับผ่าน get_current_user
    is_admin = False
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        try:
            from app.core.security import verify_access_token
            payload = verify_access_token(token)
            username = payload.get("sub")
            if username:
                result = await db.execute(select(User).where(User.username == username, User.is_active == True))
                user = result.scalar_one_or_none()
                if user and user.role == "System Administrator":
                    is_admin = True
        except Exception:
            pass

    result = await db.execute(select(SystemSettings).where(SystemSettings.id == "config"))
    cfg = result.scalar_one_or_none()
    if not cfg:
        # Return defaults
        return SettingsResponse(
            model_name=settings.DEFAULT_LLM_MODEL,
            temperature=0.4,
            max_tokens=1000,
            top_k=3,
            embedding_tech="bge-m3",
            gemini_api_key=settings.LLM_API_KEY if is_admin else "***masked***"
        )

    gemini_key = ""
    api_key_source = settings.LLM_API_KEY or cfg.gemini_api_key
    if api_key_source:
        gemini_key = api_key_source if is_admin else "***masked***"

    return SettingsResponse(
        model_name=cfg.model_name or settings.DEFAULT_LLM_MODEL,
        temperature=cfg.temperature,
        max_tokens=cfg.max_tokens,
        top_k=cfg.top_k,
        embedding_tech=cfg.embedding_tech,
        system_prompt=cfg.system_prompt,
        welcome_message=cfg.welcome_message,
        chat_greeting=cfg.chat_greeting,
        custom_faqs=json.loads(cfg.custom_faqs or "[]"),
        predefined_faqs=json.loads(cfg.predefined_faqs or "[]"),
        last_build_duration=cfg.last_build_duration,
        gemini_api_key=gemini_key
    )


@router.post("/settings", response_model=SettingsResponse)
@router.put("/settings", response_model=SettingsResponse)
async def update_settings(
    body: SettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != "System Administrator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="คุณไม่มีสิทธิ์ตั้งค่าระบบ AI"
        )
    result = await db.execute(select(SystemSettings).where(SystemSettings.id == "config"))
    cfg = result.scalar_one_or_none()

    if not cfg:
        cfg = SystemSettings(id="config")
        db.add(cfg)

    # บังคับให้อ่านค่าจากโค้ดและ env config เท่านั้น (ไม่ให้แก้ไขจากหน้าเว็บ)
    cfg.model_name = settings.DEFAULT_LLM_MODEL
    cfg.gemini_api_key = settings.LLM_API_KEY

    if body.temperature is not None:
        cfg.temperature = body.temperature
    if body.max_tokens is not None:
        cfg.max_tokens = body.max_tokens
    if body.top_k is not None:
        cfg.top_k = body.top_k
    if body.system_prompt is not None:
        cfg.system_prompt = body.system_prompt
    if body.welcome_message is not None:
        cfg.welcome_message = body.welcome_message
    if body.chat_greeting is not None:
        cfg.chat_greeting = body.chat_greeting
    if body.custom_faqs is not None:
        cfg.custom_faqs = json.dumps([f.model_dump() for f in body.custom_faqs], ensure_ascii=False)
    if body.predefined_faqs is not None:
        cfg.predefined_faqs = json.dumps([f.model_dump() for f in body.predefined_faqs], ensure_ascii=False)

    await db.commit()
    await db.refresh(cfg)

    return SettingsResponse(
        model_name=cfg.model_name,
        temperature=cfg.temperature,
        max_tokens=cfg.max_tokens,
        top_k=cfg.top_k,
        embedding_tech=cfg.embedding_tech,
        system_prompt=cfg.system_prompt,
        welcome_message=cfg.welcome_message,
        chat_greeting=cfg.chat_greeting,
        custom_faqs=json.loads(cfg.custom_faqs or "[]"),
        predefined_faqs=json.loads(cfg.predefined_faqs or "[]"),
        last_build_duration=cfg.last_build_duration,
        success=True
    )
