"""add users.password_changed_at for 90-day password expiry

Revision ID: c9e5a7b1d3f4
Revises: b8d4f6a0c2e3
Create Date: 2026-10-29 09:00:00.000000+07:00

อายุรหัสผ่านแอดมิน 90 วัน (ดู app/services/password_policy.py) — บัญชีเดิมเริ่มนับจากวันที่รัน
migration นี้ (ไม่ใช่ created_at) ไม่อย่างนั้นบัญชีที่สร้างมานานจะหมดอายุทันทีพร้อมกันทั้งระบบ
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9e5a7b1d3f4'
down_revision: Union[str, None] = 'b8d4f6a0c2e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column(
            "password_changed_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now(),
            comment="วันเวลาที่ตั้งรหัสผ่านล่าสุด (UTC)"
        ))
    op.execute("UPDATE users SET password_changed_at = CURRENT_TIMESTAMP WHERE password_changed_at IS NULL")


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("password_changed_at")
