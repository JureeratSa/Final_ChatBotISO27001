"""add admin audit logs

Revision ID: b8d4f6a0c2e3
Revises: a7c3e5d9f1b2
Create Date: 2026-10-28 15:00:00.000000+07:00

บันทึกการเข้าสู่ระบบ / ออกจากระบบ และการแก้ไขข้อมูลของแอดมิน (ดู app/services/audit_service.py)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8d4f6a0c2e3'
down_revision: Union[str, None] = 'a7c3e5d9f1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "admin_audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="รหัสบันทึก"),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False, comment="วันเวลาที่เกิดเหตุการณ์"),
        sa.Column("user_id", sa.Integer(), nullable=True,
                  comment="รหัสผู้ใช้ (NULL = ระบุตัวไม่ได้ เช่น ล็อกอินด้วยชื่อที่ไม่มีในระบบ)"),
        sa.Column("username", sa.String(length=100), nullable=True, comment="ชื่อผู้ใช้ ณ เวลาที่บันทึก"),
        sa.Column("department", sa.String(length=100), nullable=True, comment="แผนกของผู้ใช้ ณ เวลาที่บันทึก"),
        sa.Column("action", sa.String(length=50), nullable=False, comment="ประเภทเหตุการณ์"),
        sa.Column("method", sa.String(length=10), nullable=True, comment="HTTP method"),
        sa.Column("path", sa.String(length=500), nullable=True, comment="API path ที่เรียก"),
        sa.Column("status_code", sa.Integer(), nullable=True, comment="HTTP status ของผลลัพธ์"),
        sa.Column("ip_address", sa.String(length=64), nullable=True, comment="IP ของเครื่องที่เชื่อมต่อเข้ามา"),
        sa.Column("user_agent", sa.String(length=500), nullable=True, comment="อุปกรณ์/เบราว์เซอร์ (User-Agent)"),
        sa.Column("detail", sa.Text(), nullable=True, comment="รายละเอียดเพิ่มเติม (JSON)"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_admin_audit_logs_timestamp", "admin_audit_logs", ["timestamp"], unique=False)
    op.create_index("ix_admin_audit_logs_user_id", "admin_audit_logs", ["user_id"], unique=False)
    op.create_index("ix_admin_audit_logs_action", "admin_audit_logs", ["action"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_admin_audit_logs_action", table_name="admin_audit_logs")
    op.drop_index("ix_admin_audit_logs_user_id", table_name="admin_audit_logs")
    op.drop_index("ix_admin_audit_logs_timestamp", table_name="admin_audit_logs")
    op.drop_table("admin_audit_logs")
