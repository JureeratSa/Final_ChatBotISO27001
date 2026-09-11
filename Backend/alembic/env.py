"""
TUH Chatbot AI — Alembic Environment
ดึง DB URL และ metadata จากแอปจริง (app.core.config / app.core.database) แทนการ hardcode
ไว้ใน alembic.ini เพื่อไม่ให้ credential หลุดไปอยู่ในไฟล์ที่ commit เข้า git
"""
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# ให้ import "app.xxx" ได้เหมือนตอนรัน uvicorn จาก Backend/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402
from app.core.database import Base  # noqa: E402
from app.models import models  # noqa: E402,F401  ต้อง import เพื่อให้ Base.metadata รู้จักทุกตาราง

# this is the Alembic Config object, which provides access to values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# metadata เป้าหมายสำหรับ 'autogenerate' — มาจาก SQLAlchemy models จริงของแอป
target_metadata = Base.metadata

# ALEMBIC_DATABASE_URL เผื่อ override ตอนรัน dry-run กับ DB อื่น (เช่น SQLite ตอนทดสอบ
# migration script เอง) โดยไม่ต้องแก้ .env จริง — ปกติแล้วใช้ DATABASE_URL_SYNC จาก settings
db_url = os.environ.get("ALEMBIC_DATABASE_URL") or settings.DATABASE_URL_SYNC
config.set_main_option("sqlalchemy.url", db_url)


def run_migrations_offline() -> None:
    """Emit SQL แทนการต่อ DB จริง (ใช้ตอนต้องการดู SQL ก่อน apply เช่น `alembic upgrade head --sql`)"""
    context.configure(
        url=db_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """ต่อ DB จริงแล้วรัน migration"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
