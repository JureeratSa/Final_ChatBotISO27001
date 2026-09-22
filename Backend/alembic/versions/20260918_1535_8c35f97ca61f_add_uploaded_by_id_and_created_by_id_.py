"""add uploaded_by_id and created_by_id foreign keys to users

Revision ID: 8c35f97ca61f
Revises: 337aed1af62c
Create Date: 2026-09-18 15:35:28.967578+07:00

เพิ่ม FK จริง documents.uploaded_by_id / announcements.created_by_id -> users.id
คู่กับคอลัมน์ string เดิม (uploaded_by / created_by) ที่ยังเก็บไว้เป็น cache แสดงผล —
ไม่ลบ/ไม่แตะคอลัมน์เดิม เพื่อไม่ให้โค้ดที่อ่านค่านั้นตรงๆ พัง

หลัง add column จะ backfill ข้อมูลเดิมให้ทันที 2 รอบ:
  รอบ 1 — จับคู่ด้วย users.username (unique อยู่แล้วตาม schema จึงไม่มีทางกำกวม)
  รอบ 2 — จับคู่ด้วย users.display_name เฉพาะกรณีที่ชื่อนั้นตรงกับผู้ใช้ "คนเดียว" เท่านั้น
           (display_name ไม่ unique ในระดับ DB ถ้ามีมากกว่า 1 คนชื่อซ้ำ จะปล่อยเป็น NULL ไว้
           แทนการเดาสุ่ม เพื่อไม่ให้ข้อมูลผูกกับคนผิด)
แถวที่หาเจ้าของไม่เจอเลย (บัญชีถูกลบไปแล้ว/ไม่มีในระบบ) จะเหลือ uploaded_by_id/created_by_id
เป็น NULL ต่อไป — ค่า string เดิมยังอ่านได้ตามปกติเป็น fallback
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8c35f97ca61f'
down_revision: Union[str, None] = '337aed1af62c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FK_DOCUMENTS = "fk_documents_uploaded_by_id_users"
FK_ANNOUNCEMENTS = "fk_announcements_created_by_id_users"


def _columns(table):
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {c["name"] for c in inspector.get_columns(table)}


def _fk_names(table):
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {fk["name"] for fk in inspector.get_foreign_keys(table) if fk["name"]}


def _backfill(bind, table, string_col, id_col):
    # รอบ 1: จับคู่ด้วย username (unique เสมอ ปลอดภัย 100%)
    bind.execute(sa.text(f"""
        UPDATE {table}
        SET {id_col} = (SELECT u.id FROM users u WHERE u.username = {table}.{string_col})
        WHERE {id_col} IS NULL
          AND {string_col} IS NOT NULL
          AND EXISTS (SELECT 1 FROM users u WHERE u.username = {table}.{string_col})
    """))
    # รอบ 2: จับคู่ด้วย display_name เฉพาะกรณีชื่อนี้ไม่ซ้ำกับใครเลย
    bind.execute(sa.text(f"""
        UPDATE {table}
        SET {id_col} = (SELECT u.id FROM users u WHERE u.display_name = {table}.{string_col} LIMIT 1)
        WHERE {id_col} IS NULL
          AND {string_col} IS NOT NULL
          AND (SELECT COUNT(*) FROM users u WHERE u.display_name = {table}.{string_col}) = 1
    """))


def upgrade() -> None:
    bind = op.get_bind()

    # แยก "เพิ่มคอลัมน์" กับ "เพิ่ม FK constraint" เป็นคนละ batch_alter_table block เสมอ —
    # SQLite เพิ่มคอลัมน์ตรงๆ ได้ (ไม่ต้อง recreate table) แต่เพิ่ม FK constraint ต้องอาศัย
    # batch mode ทำ copy-and-move ทั้งตาราง ถ้ารวมสองงานนี้ไว้ block เดียว คำสั่ง backfill
    # (ข้างล่าง) ที่รันคั่นกลางจะมองไม่เห็นคอลัมน์ใหม่เพราะยังไม่ถูก apply จริง — บน MySQL/TiDB
    # batch mode (recreate="auto") แค่ส่ง ALTER ตรงๆ เหมือนเดิม ไม่กระทบพฤติกรรมเดิมบน production
    if "uploaded_by_id" not in _columns("documents"):
        with op.batch_alter_table("documents") as batch_op:
            batch_op.add_column(sa.Column("uploaded_by_id", sa.Integer(), nullable=True))
    _backfill(bind, "documents", "uploaded_by", "uploaded_by_id")
    if FK_DOCUMENTS not in _fk_names("documents"):
        with op.batch_alter_table("documents") as batch_op:
            batch_op.create_foreign_key(
                FK_DOCUMENTS, "users", ["uploaded_by_id"], ["id"], ondelete="SET NULL"
            )

    if "created_by_id" not in _columns("announcements"):
        with op.batch_alter_table("announcements") as batch_op:
            batch_op.add_column(sa.Column("created_by_id", sa.Integer(), nullable=True))
    _backfill(bind, "announcements", "created_by", "created_by_id")
    if FK_ANNOUNCEMENTS not in _fk_names("announcements"):
        with op.batch_alter_table("announcements") as batch_op:
            batch_op.create_foreign_key(
                FK_ANNOUNCEMENTS, "users", ["created_by_id"], ["id"], ondelete="SET NULL"
            )


def downgrade() -> None:
    if FK_ANNOUNCEMENTS in _fk_names("announcements"):
        with op.batch_alter_table("announcements") as batch_op:
            batch_op.drop_constraint(FK_ANNOUNCEMENTS, type_="foreignkey")
    if "created_by_id" in _columns("announcements"):
        with op.batch_alter_table("announcements") as batch_op:
            batch_op.drop_column("created_by_id")

    if FK_DOCUMENTS in _fk_names("documents"):
        with op.batch_alter_table("documents") as batch_op:
            batch_op.drop_constraint(FK_DOCUMENTS, type_="foreignkey")
    if "uploaded_by_id" in _columns("documents"):
        with op.batch_alter_table("documents") as batch_op:
            batch_op.drop_column("uploaded_by_id")
