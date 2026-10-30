"""
ตั้งค่าบอท (หน้า "ตั้งค่า AI" และ "คู่มือตอบกลับ" ของ AdminWeb) — /api/admin/settings, /api/admin/custom_faqs

ค่าเก็บในตาราง settings แถวเดียว (id="config")
ชื่อโมเดลและ API key มาจาก .env เท่านั้น — แก้จากหน้าเว็บไม่ได้ และไม่ส่ง key ออกไปทาง API
"""
import json
import time

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.models import SystemSettings, UnansweredQuery, User
from app.schemas.schemas import CustomFaqCreate, SettingsResponse, SettingsUpdate
from app.services.audit_service import add_audit_detail
from app.services.department_scope import department_column_filter, is_super_admin, require_super_admin, scope_department
from app.services.rebuild_service import get_or_create_settings_row

router = APIRouter(prefix="/api/admin", tags=["settings"])


def _to_response(cfg: SystemSettings, **extra) -> SettingsResponse:
    return SettingsResponse(
        model_name=settings.DEFAULT_LLM_MODEL,
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
        **extra,
    )


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    masked_key = "***masked***" if settings.LLM_API_KEY else ""
    cfg = (await db.execute(select(SystemSettings).where(SystemSettings.id == "config"))).scalar_one_or_none()
    if not cfg:
        return SettingsResponse(model_name=settings.DEFAULT_LLM_MODEL, temperature=0.4, max_tokens=1000, top_k=3,
                                embedding_tech="bge-m3", gemini_api_key=masked_key)
    return _to_response(cfg, gemini_api_key=masked_key)


@router.post("/settings", response_model=SettingsResponse)
async def update_settings(body: SettingsUpdate,
                          current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    require_super_admin(current_user, "คุณไม่มีสิทธิ์ตั้งค่าระบบ AI")
    # บันทึกแค่ชื่อช่องที่แก้ ไม่เก็บค่า (system prompt ยาวมาก)
    add_audit_detail(changed_fields=sorted(body.model_dump(exclude_none=True)))
    cfg = await get_or_create_settings_row(db)
    cfg.model_name = settings.DEFAULT_LLM_MODEL
    cfg.gemini_api_key = None            # คอลัมน์เก่า — key อยู่ใน .env เท่านั้น ไม่เก็บสำเนาลงฐานข้อมูล

    for field in ("temperature", "max_tokens", "top_k", "system_prompt", "welcome_message", "chat_greeting"):
        value = getattr(body, field)
        if value is not None:
            setattr(cfg, field, value)
    if body.custom_faqs is not None:
        cfg.custom_faqs = json.dumps([f.model_dump() for f in body.custom_faqs], ensure_ascii=False)
    if body.predefined_faqs is not None:
        cfg.predefined_faqs = json.dumps([f.model_dump() for f in body.predefined_faqs], ensure_ascii=False)

    await db.commit()
    await db.refresh(cfg)
    return _to_response(cfg, success=True)


async def _require_faq_permission(db: AsyncSession, user: User, question: str) -> None:
    """FAQ ตอบแทนบอทให้ทุกคน — แอดมินแผนกเพิ่มได้เฉพาะ "สอนคำตอบ" ให้คำถามที่ตอบไม่ได้ของแผนกตัวเอง"""
    if is_super_admin(user):
        return
    rows = await db.execute(select(UnansweredQuery.query).where(
        department_column_filter(UnansweredQuery.department, scope_department(user))
    ))
    wanted = question.strip().lower()
    if not any((q or "").strip().lower() == wanted for q in rows.scalars().all()):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="แอดมินแผนกเพิ่ม FAQ ได้เฉพาะคำถามที่ตอบไม่ได้ของแผนกตัวเอง — FAQ อื่นให้ SuperAdmin เพิ่ม")


@router.post("/custom_faqs")
async def add_custom_faq(body: CustomFaqCreate,
                         current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """เพิ่ม FAQ 1 ข้อ (ตอนแก้คำถามที่ตอบไม่ได้ด้วยวิธี "สอนคำตอบ") — แอดมินแผนกใช้ได้ ต่างจาก POST /settings"""
    await _require_faq_permission(db, current_user, body.question)
    cfg = await get_or_create_settings_row(db)
    faqs = json.loads(cfg.custom_faqs or "[]")
    new_faq = {"id": f"faq-{int(time.time() * 1000)}", "icon": None,
               "question": body.question.strip(), "answer": body.answer}
    faqs.append(new_faq)
    add_audit_detail(faq_question=new_faq["question"][:200])
    cfg.custom_faqs = json.dumps(faqs, ensure_ascii=False)
    await db.commit()
    return {"success": True, "faq": new_faq, "custom_faqs": faqs}
