"""
Integration test: Alembic migration ครอบคลุมทั้งหมด (alembic/versions/*)
รันจริงกับ SQLite ชั่วคราว (tmp_path — อยู่บน local disk เสมอ ไม่ใช่ network share ที่ repo
อาจอยู่บน) เพื่อยืนยันว่า:
  1. `alembic upgrade head` สร้างตารางครบตามที่ app/models/models.py ประกาศไว้จริง
  2. `alembic downgrade base` ล้างตารางกลับเป็นตอนเริ่มต้นได้สะอาด (ไม่ทิ้งขยะ)
ป้องกันไม่ให้ migration หลุด sync จาก models.py ไปโดยไม่มีใครรู้ตัว
"""
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

BACKEND_DIR = Path(__file__).resolve().parents[1]
EXPECTED_TABLES = {
    "users", "documents", "settings", "history",
    "feedback", "unanswered", "forms", "announcements",
}


@pytest.fixture
def alembic_config(tmp_path, monkeypatch):
    db_path = tmp_path / "alembic_test.db"
    db_url = f"sqlite:///{db_path.as_posix()}"
    monkeypatch.setenv("ALEMBIC_DATABASE_URL", db_url)

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.attributes["configure_logger"] = False
    return cfg, db_url


def test_upgrade_head_creates_all_model_tables(alembic_config):
    cfg, db_url = alembic_config
    command.upgrade(cfg, "head")

    engine = create_engine(db_url)
    tables = set(inspect(engine).get_table_names())
    engine.dispose()

    assert EXPECTED_TABLES.issubset(tables)


def test_downgrade_base_drops_all_model_tables(alembic_config):
    cfg, db_url = alembic_config
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")

    engine = create_engine(db_url)
    tables = set(inspect(engine).get_table_names())
    engine.dispose()

    assert tables.isdisjoint(EXPECTED_TABLES)
