"""
TUH Chatbot AI — One-shot JSON → DB Migration Script
ย้ายข้อมูลจาก JSON files ของระบบเดิม (user/backend/db/*.json) เข้า DB ปัจจุบัน

เดิมฟังก์ชันนี้ถูกเรียกอัตโนมัติทุกครั้งที่ backend startup (ใน app/main.py lifespan) ทั้งที่
เป็นงาน one-shot ที่จำเป็นแค่ครั้งเดียวตอน migrate จากระบบเก่า (v1) มา — เสียเวลา query DB
เช็คทุกตารางทุกครั้งที่ startup ไปโดยเปล่าประโยชน์หลังจาก migrate เสร็จแล้ว จึงแยกออกมาเป็น
สคริปต์ที่รันเองตอนต้องการเท่านั้น:

    cd Backend
    python -m scripts.migrate_from_json

Idempotent: เช็คว่าแต่ละตารางมีข้อมูลอยู่แล้วหรือยังก่อน insert ทุกครั้ง รันซ้ำได้อย่างปลอดภัย
"""
import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import AsyncSessionLocal  # noqa: E402
from app.models.models import (  # noqa: E402
    SystemSettings, Document, Feedback, UnansweredQuery,
    ChatHistory, Form as FormModel, Announcement
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(message)s")
logger = logging.getLogger(__name__)


async def migrate_from_json():
    """Migrate ข้อมูลจาก JSON files เดิมเข้า DB — ตรวจสอบว่าแต่ละตารางว่างก่อน migrate ทีละตาราง"""
    old_backend_dir = Path(__file__).resolve().parents[2] / "user" / "backend" / "db"

    if not old_backend_dir.exists():
        logger.info("ไม่พบโฟลเดอร์ JSON เดิม (%s) — ไม่มีอะไรต้อง migrate", old_backend_dir)
        return

    async with AsyncSessionLocal() as session:
        # ─ Migrate Settings ─
        result = await session.execute(select(SystemSettings).where(SystemSettings.id == "config"))
        if not result.scalar_one_or_none():
            settings_file = old_backend_dir / "db_settings.json"
            if settings_file.exists():
                data = json.loads(settings_file.read_text(encoding="utf-8"))
                cfg = SystemSettings(
                    id="config",
                    model_name=data.get("model_name") or settings.DEFAULT_LLM_MODEL,
                    temperature=float(data.get("temperature", 0.4)),
                    max_tokens=int(data.get("max_tokens", 1000)),
                    top_k=int(data.get("top_k", 3)),
                    system_prompt=data.get("system_prompt"),
                    welcome_message=data.get("welcome_message"),
                    chat_greeting=data.get("chat_greeting"),
                    custom_faqs=json.dumps(data.get("custom_faqs", []), ensure_ascii=False),
                    predefined_faqs=json.dumps(data.get("predefined_faqs", []), ensure_ascii=False),
                )
                session.add(cfg)
                logger.info("Migrated settings จาก %s", settings_file.name)

        # ─ Migrate Documents ─
        docs_file = old_backend_dir / "db_documents.json"
        if docs_file.exists():
            docs_count = await session.execute(select(Document).limit(1))
            if not docs_count.scalar_one_or_none():
                docs_data = json.loads(docs_file.read_text(encoding="utf-8"))
                for d in docs_data:
                    session.add(Document(
                        filename=d.get("filename", ""),
                        display_name=d.get("display_name"),
                        status=d.get("status", "Active"),
                        pages=d.get("pages"),
                        size=d.get("size"),
                        exclude_pages=",".join(map(str, d.get("exclude_pages", []))),
                    ))
                logger.info("Migrated %d documents", len(docs_data))

        # ─ Migrate Feedback ─
        feedback_file = old_backend_dir / "db_feedback.json"
        if feedback_file.exists():
            fb_count = await session.execute(select(Feedback).limit(1))
            if not fb_count.scalar_one_or_none():
                fb_data = json.loads(feedback_file.read_text(encoding="utf-8"))
                for f in fb_data:
                    session.add(Feedback(
                        id=f.get("msgId", f"fb-{int(__import__('time').time() * 1000)}"),
                        rating=f.get("rating", "like"),
                        comment=f.get("comment"),
                        query=f.get("query"),
                    ))
                logger.info("Migrated %d feedback entries", len(fb_data))

        # ─ Migrate Unanswered ─
        unans_file = old_backend_dir / "db_unanswered.json"
        if unans_file.exists():
            unans_count = await session.execute(select(UnansweredQuery).limit(1))
            if not unans_count.scalar_one_or_none():
                unans_data = json.loads(unans_file.read_text(encoding="utf-8"))
                for u in unans_data:
                    session.add(UnansweredQuery(
                        id=u.get("id", f"unans-{int(__import__('time').time() * 1000)}"),
                        query=u.get("query", ""),
                        count=u.get("count", 1),
                        status=u.get("status", "Pending"),
                    ))
                logger.info("Migrated %d unanswered queries", len(unans_data))

        # Force SystemSettings embedding_tech to local_chroma
        result_force = await session.execute(select(SystemSettings).where(SystemSettings.id == "config"))
        cfg_force = result_force.scalar_one_or_none()
        if cfg_force:
            cfg_force.embedding_tech = "local_chroma"
        else:
            cfg_force = SystemSettings(id="config", embedding_tech="local_chroma")
            session.add(cfg_force)

        await session.commit()
        logger.info("Migration เสร็จสมบูรณ์")


if __name__ == "__main__":
    asyncio.run(migrate_from_json())
