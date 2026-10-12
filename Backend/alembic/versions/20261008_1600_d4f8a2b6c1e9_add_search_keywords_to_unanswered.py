"""add search_keywords to unanswered

Revision ID: d4f8a2b6c1e9
Revises: b7e4a1c9d2f3
Create Date: 2026-10-08 16:00:00.000000+07:00

คำค้นภาษาเอกสารที่แอดมินสอนจากหน้าคำถามที่บอทตอบไม่ได้ (JSON array) — เมื่อมีคำถามใหม่ที่คล้าย
คำถามที่สอนไว้ ระบบจะเติมคำค้นเหล่านี้ต่อท้ายข้อความที่ใช้ค้นเอกสาร (ไม่แก้ดัชนี/ไม่แก้ retriever)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4f8a2b6c1e9'
down_revision: Union[str, None] = 'b7e4a1c9d2f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(table):
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    if "search_keywords" not in _columns("unanswered"):
        with op.batch_alter_table("unanswered") as batch_op:
            batch_op.add_column(sa.Column("search_keywords", sa.Text(), nullable=True))


def downgrade() -> None:
    if "search_keywords" in _columns("unanswered"):
        with op.batch_alter_table("unanswered") as batch_op:
            batch_op.drop_column("search_keywords")
