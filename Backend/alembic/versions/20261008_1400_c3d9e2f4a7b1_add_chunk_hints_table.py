"""add chunk_hints table

Revision ID: c3d9e2f4a7b1
Revises: b7e4a1c9d2f3
Create Date: 2026-10-08 14:00:00.000000+07:00

ตารางเก็บคำถามตัวอย่างที่แอดมินผูกกับ chunk ของเอกสาร (สอนบอทผ่านเอกสาร แทนการเพิ่ม FAQ)
ผูกด้วย (source, chunk_hash) ไม่ใช่ chunk_id เพราะ chunk_id ถูกไล่เลขใหม่ทุกครั้งที่ rebuild
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d9e2f4a7b1'
down_revision: Union[str, None] = 'b7e4a1c9d2f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if "chunk_hints" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "chunk_hints",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="รหัส hint (Primary Key)"),
        sa.Column("source", sa.String(length=255), nullable=False, comment="ชื่อไฟล์เอกสารต้นทางของ chunk"),
        sa.Column("chunk_hash", sa.String(length=64), nullable=False, comment="SHA-256 ของเนื้อหา chunk"),
        sa.Column("page", sa.Integer(), nullable=True, comment="เลขหน้าของ chunk ตอนบันทึก"),
        sa.Column("content_preview", sa.Text(), nullable=True, comment="สำเนาเนื้อหา chunk ตอนบันทึก"),
        sa.Column("questions", sa.Text(), nullable=False, comment="คำถามตัวอย่าง (JSON array of string)"),
        sa.Column("unanswered_id", sa.String(length=255), nullable=True, comment="คำถามที่บอทตอบไม่ได้ซึ่งเป็นต้นเหตุ (Foreign Key)"),
        sa.Column("created_by_id", sa.Integer(), nullable=True, comment="รหัสผู้ใช้งานที่บันทึก (Foreign Key)"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="วันเวลาที่สร้าง"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="วันเวลาที่แก้ไขล่าสุด"),
        sa.ForeignKeyConstraint(["unanswered_id"], ["unanswered.id"], name="fk_chunk_hints_unanswered_id_unanswered", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], name="fk_chunk_hints_created_by_id_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "chunk_hash", name="uq_chunk_hints_source_hash"),
    )


def downgrade() -> None:
    if "chunk_hints" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table("chunk_hints")
