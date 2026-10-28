"""add department scoping to documents, forms, unanswered and history

Revision ID: a7c3e5d9f1b2
Revises: e9ac8c9f5d7b
Create Date: 2026-10-28 10:00:00.000000+07:00

แยกสิทธิ์ AdminWeb ตามแผนก (ดู app/services/department_scope.py):
- documents.department / forms.department — แผนกเจ้าของ (NULL = ยังไม่ระบุ เห็นแค่ SuperAdmin)
- unanswered.department — แผนกที่เดาจากเอกสารอันดับ 1 ที่ค้นเจอ
- history.cited_docs — เอกสารที่คำตอบอิงจริง (JSON array) ใช้กรองประวัติตามแผนกของเอกสาร

migration นี้แก้แค่ schema — การกำหนดแผนกให้ข้อมูลเดิมทำด้วยสคริปต์แยก
(Backend/scripts/backfill_departments.py) เพราะขึ้นกับชื่อแผนกจริงในระบบ
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7c3e5d9f1b2'
down_revision: Union[str, None] = 'e9ac8c9f5d7b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_DEPARTMENT_TABLES = {
    "documents": "แผนกเจ้าของเอกสาร (ตรงกับ users.department)",
    "forms": "แผนกเจ้าของแบบฟอร์ม (NULL = ยังไม่ระบุ เห็นแค่ SuperAdmin)",
    "unanswered": "แผนกที่น่าจะเกี่ยวข้อง (เดาจากเอกสารอันดับ 1 ที่ค้นเจอ) — NULL = เดาไม่ได้ เห็นแค่ SuperAdmin",
}


def upgrade() -> None:
    for table, comment in _DEPARTMENT_TABLES.items():
        with op.batch_alter_table(table) as batch_op:
            batch_op.add_column(sa.Column("department", sa.String(length=100), nullable=True, comment=comment))
            batch_op.create_index(f"ix_{table}_department", ["department"], unique=False)

    with op.batch_alter_table("history") as batch_op:
        batch_op.add_column(sa.Column(
            "cited_docs", sa.Text(), nullable=True,
            comment="ชื่อไฟล์เอกสารที่คำตอบนี้อิงจริง (JSON array) — ใช้แยกประวัติตามแผนก, NULL = แถวเก่าก่อนมีคอลัมน์นี้"
        ))


def downgrade() -> None:
    with op.batch_alter_table("history") as batch_op:
        batch_op.drop_column("cited_docs")

    for table in reversed(list(_DEPARTMENT_TABLES)):
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_index(f"ix_{table}_department")
            batch_op.drop_column("department")
