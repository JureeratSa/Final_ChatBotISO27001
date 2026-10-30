"""add users.token_version to revoke every token when the password changes

Revision ID: d1f3a5c7e9b2
Revises: c9e5a7b1d3f4
Create Date: 2026-10-30 15:00:00.000000+07:00

เดิมตัด token เก่าด้วยการเทียบเวลาออก token (iat เป็นวินาที) กับ password_changed_at ซึ่ง TiDB เก็บละเอียด
แค่วินาที — token ที่ออกในวินาทีเดียวกับตอนเปลี่ยนรหัสจึงยังใช้ได้ (security audit L15)
token ทุกใบมี tv = token_version ตอนออก เปลี่ยนรหัสผ่าน = +1 → token เก่าทุกใบใช้ไม่ได้ทันที
บัญชีเดิมเริ่มที่ 0 และ token ที่ไม่มี tv (ออกก่อน migration) นับเป็น 0 — ไม่มีใครถูกเด้งออกตอนอัปเดต
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1f3a5c7e9b2'
down_revision: Union[str, None] = 'c9e5a7b1d3f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column(
            "token_version", sa.Integer(), nullable=False, server_default="0",
            comment="รุ่นของ token — เปลี่ยนรหัสผ่านแล้ว +1 ทำให้ token ที่ออกก่อนหน้าใช้ไม่ได้"
        ))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("token_version")
