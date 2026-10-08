"""add resolution fields to unanswered

Revision ID: b7e4a1c9d2f3
Revises: 8c35f97ca61f
Create Date: 2026-10-08 10:00:00.000000+07:00

เพิ่มข้อมูล "ปิดรายการอย่างไร" ให้ตาราง unanswered เพื่อรองรับ flow ใหม่ในหน้าคำถามที่บอทตอบไม่ได้
(แก้ไข → เลือกวิธีแก้ / ไม่แก้ไข → ระบุเหตุผล):
  - resolution_type  วิธีแก้ ('custom_faq' / 'document_upload' / 'chunk_hint')
  - ignore_reason    เหตุผลที่ไม่แก้ ('spam' / 'chit_chat' / 'out_of_scope' / 'other')
  - note             หมายเหตุอิสระ
  - resolved_by_id   FK -> users.id (SET NULL ถ้าบัญชีถูกลบ)
  - resolved_at      เวลาที่ปิดรายการ

แถวเดิมที่เป็น Resolved/Ignored อยู่แล้วจะมีคอลัมน์ใหม่เป็น NULL (ไม่รู้ย้อนหลังว่าแก้ด้วยวิธีไหน)
แยก add column กับ create FK เป็นคนละ batch block ตามเหตุผลเดียวกับ migration 8c35f97ca61f
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7e4a1c9d2f3'
down_revision: Union[str, None] = '8c35f97ca61f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FK_RESOLVED_BY = "fk_unanswered_resolved_by_id_users"

NEW_COLUMNS = [
    ("resolution_type", lambda: sa.Column("resolution_type", sa.String(length=50), nullable=True)),
    ("ignore_reason", lambda: sa.Column("ignore_reason", sa.String(length=50), nullable=True)),
    ("note", lambda: sa.Column("note", sa.Text(), nullable=True)),
    ("resolved_by_id", lambda: sa.Column("resolved_by_id", sa.Integer(), nullable=True)),
    ("resolved_at", lambda: sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True)),
]


def _columns(table):
    inspector = sa.inspect(op.get_bind())
    return {c["name"] for c in inspector.get_columns(table)}


def _fk_names(table):
    inspector = sa.inspect(op.get_bind())
    return {fk["name"] for fk in inspector.get_foreign_keys(table) if fk["name"]}


def upgrade() -> None:
    existing = _columns("unanswered")
    missing = [make() for name, make in NEW_COLUMNS if name not in existing]
    if missing:
        with op.batch_alter_table("unanswered") as batch_op:
            for col in missing:
                batch_op.add_column(col)

    if FK_RESOLVED_BY not in _fk_names("unanswered"):
        with op.batch_alter_table("unanswered") as batch_op:
            batch_op.create_foreign_key(
                FK_RESOLVED_BY, "users", ["resolved_by_id"], ["id"], ondelete="SET NULL"
            )


def downgrade() -> None:
    if FK_RESOLVED_BY in _fk_names("unanswered"):
        with op.batch_alter_table("unanswered") as batch_op:
            batch_op.drop_constraint(FK_RESOLVED_BY, type_="foreignkey")

    existing = _columns("unanswered")
    to_drop = [name for name, _ in reversed(NEW_COLUMNS) if name in existing]
    if to_drop:
        with op.batch_alter_table("unanswered") as batch_op:
            for name in to_drop:
                batch_op.drop_column(name)
