/**
 * TUH Chatbot AI v2 — Data Migration Script
 * PM / BA Role: สร้าง script migrate ข้อมูลจาก JSON files เก่าเข้า PostgreSQL
 * รัน: python migrate_data.py
 */
import json
import os
import sys
import time
import hashlib
import asyncio
from pathlib import Path

# ตั้งค่า path
ROOT_DIR = Path(__file__).parent.parent  # PJChatbot/
OLD_DB_DIR = ROOT_DIR / "user" / "backend" / "db"

# Database connection
DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://tuhchatbot:tuhchatbot2026@localhost:5432/tuhchatbot"
)


async def main():
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from sqlalchemy import select

    sys.path.insert(0, str(ROOT_DIR / "v2" / "backend"))
    from app.models.models import (
        User, Document, SystemSettings, Feedback,
        UnansweredQuery, Form as FormModel, Announcement
    )
    from app.core.database import Base
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    engine = create_async_engine(DB_URL, echo=True)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    # สร้างตาราง
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Tables created")

    async with SessionLocal() as session:

        # ─── 1. Migrate Admin → Users ──────────────────────────────────────────
        admin_file = OLD_DB_DIR / "db_admin.json"
        users_count = (await session.execute(select(User).limit(1))).scalar_one_or_none()
        if not users_count and admin_file.exists():
            admin_data = json.loads(admin_file.read_text(encoding="utf-8"))
            # ตรวจว่าเป็น old format (pbkdf2) หรือ new (bcrypt)
            old_hash = admin_data.get("password_hash", "")
            old_salt = admin_data.get("password_salt", "")

            # Hash ใหม่ด้วย bcrypt (ค่าเริ่มต้น admin1234)
            # Note: ใน production ให้ user reset password เอง
            new_hash = pwd_context.hash("admin1234")

            user = User(
                username=admin_data.get("username", "admin"),
                password_hash=new_hash,
                display_name=admin_data.get("name", "แอดมิน สารสนเทศ"),
                role=admin_data.get("role", "System Administrator"),
                is_active=True
            )
            session.add(user)
            print(f"✅ Migrated admin user: {user.username}")

        # ─── 2. Migrate Settings ────────────────────────────────────────────────
        settings_file = OLD_DB_DIR / "db_settings.json"
        cfg_existing = (await session.execute(
            select(SystemSettings).where(SystemSettings.id == "config")
        )).scalar_one_or_none()

        if not cfg_existing and settings_file.exists():
            data = json.loads(settings_file.read_text(encoding="utf-8"))
            cfg = SystemSettings(
                id="config",
                model_name=data.get("model_name", "google/gemini-2.5-flash"),
                temperature=float(data.get("temperature", 0.4)),
                max_tokens=int(data.get("max_tokens", 1000)),
                top_k=int(data.get("top_k", 3)),
                system_prompt=data.get("system_prompt"),
                welcome_message=data.get("welcome_message"),
                chat_greeting=data.get("chat_greeting"),
                custom_faqs=json.dumps(data.get("custom_faqs", []), ensure_ascii=False),
                predefined_faqs=json.dumps(data.get("predefined_faqs", []), ensure_ascii=False),
                last_build_duration=data.get("last_build_duration"),
            )
            session.add(cfg)
            print("✅ Migrated settings")

        # ─── 3. Migrate Documents ───────────────────────────────────────────────
        docs_file = OLD_DB_DIR / "db_documents.json"
        if docs_file.exists():
            docs_data = json.loads(docs_file.read_text(encoding="utf-8"))
            for d in docs_data:
                existing = (await session.execute(
                    select(Document).where(Document.filename == d.get("filename"))
                )).scalar_one_or_none()
                if not existing:
                    doc = Document(
                        filename=d.get("filename", ""),
                        display_name=d.get("display_name"),
                        status=d.get("status", "Active"),
                        pages=d.get("pages"),
                        size=d.get("size"),
                        exclude_pages=",".join(map(str, d.get("exclude_pages", []))),
                    )
                    session.add(doc)
            print(f"✅ Migrated {len(docs_data)} documents")

        # ─── 4. Migrate Feedback ────────────────────────────────────────────────
        feedback_file = OLD_DB_DIR / "db_feedback.json"
        if feedback_file.exists():
            fb_data = json.loads(feedback_file.read_text(encoding="utf-8"))
            migrated = 0
            for f in fb_data:
                existing = (await session.execute(
                    select(Feedback).where(Feedback.id == f.get("msgId", ""))
                )).scalar_one_or_none()
                if not existing and f.get("msgId"):
                    session.add(Feedback(
                        id=f.get("msgId"),
                        rating=f.get("rating", "like"),
                        comment=f.get("comment"),
                        query=f.get("query"),
                    ))
                    migrated += 1
            print(f"✅ Migrated {migrated} feedback entries")

        # ─── 5. Migrate Unanswered ──────────────────────────────────────────────
        unans_file = OLD_DB_DIR / "db_unanswered.json"
        if unans_file.exists():
            unans_data = json.loads(unans_file.read_text(encoding="utf-8"))
            migrated = 0
            for u in unans_data:
                existing = (await session.execute(
                    select(UnansweredQuery).where(UnansweredQuery.id == u.get("id", ""))
                )).scalar_one_or_none()
                if not existing and u.get("id"):
                    session.add(UnansweredQuery(
                        id=u.get("id"),
                        query=u.get("query", ""),
                        count=u.get("count", 1),
                        status=u.get("status", "Pending"),
                    ))
                    migrated += 1
            print(f"✅ Migrated {migrated} unanswered queries")

        # ─── 6. Migrate Forms ────────────────────────────────────────────────────
        forms_file = OLD_DB_DIR / "db_forms.json"
        if forms_file.exists():
            forms_data = json.loads(forms_file.read_text(encoding="utf-8"))
            migrated = 0
            for f in forms_data:
                existing = (await session.execute(
                    select(FormModel).where(FormModel.id == str(f.get("id", "")))
                )).scalar_one_or_none()
                if not existing and f.get("id"):
                    session.add(FormModel(
                        id=str(f.get("id")),
                        name=f.get("name", ""),
                        filename=f.get("filename"),
                        page=str(f.get("page", "")),
                        download_link=f.get("download_link"),
                    ))
                    migrated += 1
            print(f"✅ Migrated {migrated} forms")

        # ─── 7. Migrate Announcements ────────────────────────────────────────────
        ann_file = OLD_DB_DIR / "db_announcements.json"
        if ann_file.exists():
            ann_data = json.loads(ann_file.read_text(encoding="utf-8"))
            migrated = 0
            for a in ann_data:
                existing = (await session.execute(
                    select(Announcement).where(Announcement.id == int(a.get("id", 0)))
                )).scalar_one_or_none()
                if not existing:
                    session.add(Announcement(
                        title=a.get("title", ""),
                        content=a.get("content"),
                        start_date=a.get("start_date"),
                        end_date=a.get("end_date"),
                        pinned=bool(a.get("pinned", False)),
                    ))
                    migrated += 1
            print(f"✅ Migrated {migrated} announcements")

        await session.commit()
        print("\n🎉 Migration completed successfully!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
