"""
TUH Chatbot AI — Admin Router: Settings
แยกออกมาจาก Backend/app/routers/admin.py
ไม่แยก service layer (ตามแผน) — GET /settings ไม่บังคับ login และไม่ส่ง API key ออกไป
"""
import json
import time

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.config import settings
from app.routers.auth import get_current_user
from app.models.models import User, SystemSettings
from app.schemas.schemas import SettingsResponse, SettingsUpdate, CustomFaqCreate
from app.services.audit_service import add_audit_detail

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(db: AsyncSession = Depends(get_db)):
    # API key ไม่ถูกส่งออกจาก API เลย (แม้เป็น System Administrator) — ค่าจริงอยู่ใน .env เท่านั้น
    # endpoint นี้ต้องรองรับผู้เรียกแบบไม่ login ด้วย จึงไม่บังคับ get_current_user
    gemini_key = "***masked***" if settings.LLM_API_KEY else ""

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
            gemini_api_key=gemini_key
        )

    return SettingsResponse(
        model_name=settings.DEFAULT_LLM_MODEL,  # แสดงโมเดลที่ใช้จริง (มาจากโค้ด/.env)
        # model_name=cfg.model_name or settings.DEFAULT_LLM_MODEL,  # ของเดิม: ค่าในตารางอาจค้างชื่อโมเดลเก่า
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
    # บันทึกแค่ชื่อช่องที่ส่งมาแก้ ไม่เก็บค่า (system prompt ยาว / อาจมี API key)
    add_audit_detail(changed_fields=sorted(body.model_dump(exclude_none=True)))
    result = await db.execute(select(SystemSettings).where(SystemSettings.id == "config"))
    cfg = result.scalar_one_or_none()

    if not cfg:
        cfg = SystemSettings(id="config")
        db.add(cfg)

    # บังคับให้อ่านค่าจากโค้ดและ env config เท่านั้น (ไม่ให้แก้ไขจากหน้าเว็บ)
    cfg.model_name = settings.DEFAULT_LLM_MODEL
    # API key อยู่ใน .env เท่านั้น ไม่เก็บสำเนาลงฐานข้อมูล (เดิมเขียน key จริงลงคอลัมน์นี้ทุกครั้งที่บันทึก)
    cfg.gemini_api_key = None

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


@router.post("/custom_faqs")
async def add_custom_faq(
    body: CustomFaqCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """เพิ่มคู่คำถาม-คำตอบ FAQ 1 คู่ (ตอนแก้คำถามที่บอทตอบไม่ได้ด้วยวิธี "สอน FAQ")
    แยกจาก POST /settings ซึ่งเป็นของ SuperAdmin เท่านั้น — แอดมินแผนกเพิ่ม FAQ ได้ แต่แก้ค่าอื่นของระบบไม่ได้"""
    result = await db.execute(select(SystemSettings).where(SystemSettings.id == "config"))
    cfg = result.scalar_one_or_none()
    if not cfg:
        cfg = SystemSettings(id="config")
        db.add(cfg)
    faqs = json.loads(cfg.custom_faqs or "[]")
    new_faq = {
        "id": f"faq-{int(time.time() * 1000)}",
        "icon": None,
        "question": body.question.strip(),
        "answer": body.answer,
    }
    faqs.append(new_faq)
    add_audit_detail(faq_question=new_faq["question"][:200])
    cfg.custom_faqs = json.dumps(faqs, ensure_ascii=False)
    await db.commit()
    return {"success": True, "faq": new_faq, "custom_faqs": faqs}
