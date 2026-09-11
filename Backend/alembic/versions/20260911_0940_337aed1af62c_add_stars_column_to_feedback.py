"""add stars column to feedback (no-op — column already exists via baseline)

Revision ID: 337aed1af62c
Revises: 02ea7bfaaa35
Create Date: 2026-09-11 09:40:30.410761+07:00

หมายเหตุ: migration นี้ถูก autogenerate ซ้ำโดยไม่ตั้งใจ — คอลัมน์ `feedback.stars`
ถูกประกาศไว้แล้วใน f85537965423 (initial_schema_baseline) ตั้งแต่ต้น ทำให้รัน
`alembic upgrade head` จาก base จริงๆ (เช่นใน CI/เครื่องใหม่) ชน
`duplicate column name: stars` — แก้โดยเช็คก่อนว่าคอลัมน์มีอยู่แล้วหรือยัง
(idempotent) แทนการลบไฟล์นี้ทิ้ง เผื่อมี environment ไหนที่ alembic_version
เดินมาถึง revision นี้แล้วจริงๆ
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '337aed1af62c'
down_revision: Union[str, None] = '02ea7bfaaa35'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _feedback_columns():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {c['name'] for c in inspector.get_columns('feedback')}


def upgrade() -> None:
    if 'stars' not in _feedback_columns():
        op.add_column('feedback', sa.Column('stars', sa.Integer(), nullable=True))


def downgrade() -> None:
    if 'stars' in _feedback_columns():
        op.drop_column('feedback', 'stars')
