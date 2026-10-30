"""widen forms download_link for thai filenames

Revision ID: e9ac8c9f5d7b
Revises: d4f8a2b6c1e9
Create Date: 2026-10-26 14:15:04.694508+07:00

ลิงก์ดาวน์โหลดแบบฟอร์มเก็บชื่อไฟล์แบบ URL-encode — ตัวอักษรไทย 1 ตัวกลายเป็น 9 ตัว (%E0%B8%xx)
ชื่อไฟล์ไทยราว 50 ตัวจึงยาวเกิน VARCHAR(500) เดิม ทำให้อัปโหลดแบบฟอร์มล้มด้วย
"Data too long for column 'download_link'" (500) — ขยายเป็น 2048
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e9ac8c9f5d7b'
down_revision: Union[str, None] = 'd4f8a2b6c1e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("forms") as batch_op:
        batch_op.alter_column("download_link", existing_type=sa.String(length=500),
                              type_=sa.String(length=2048), existing_nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("forms") as batch_op:
        batch_op.alter_column("download_link", existing_type=sa.String(length=2048),
                              type_=sa.String(length=500), existing_nullable=True)
