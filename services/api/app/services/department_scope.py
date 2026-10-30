"""
Department Scoping
แยกสิทธิ์ AdminWeb ตามแผนก (หมวดงาน):
- SuperAdmin (role 'System Administrator') เห็น/จัดการได้ทุกแผนก + ส่วนกลางของระบบ
- แอดมินแผนก เห็น/จัดการได้เฉพาะเอกสาร แบบฟอร์ม ประวัติคำตอบ และคำถามที่ตอบไม่ได้ของแผนกตัวเอง

ฝั่งแชทบอท (ผู้ใช้ทั่วไป) ไม่ถูกกรอง — บอทยังค้นจากเอกสารทุกแผนกเหมือนเดิม
"""
import json
from collections import Counter
from typing import Iterable, List, Optional, Set

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import ChatHistory, Document, User

SUPER_ADMIN_ROLE = "System Administrator"
# ค่า ?department= ที่ SuperAdmin ใช้ดูเฉพาะรายการที่ยังไม่ระบุแผนก (department IS NULL)
UNASSIGNED = "__unassigned__"


def is_super_admin(user: User) -> bool:
    return user.role == SUPER_ADMIN_ROLE


def require_super_admin(user: User, detail: str = "เฉพาะ SuperAdmin เท่านั้นที่ทำรายการนี้ได้") -> None:
    if not is_super_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def scope_department(user: User, requested: Optional[str] = None) -> Optional[str]:
    """แผนกที่ต้องใช้กรองข้อมูลของ request นี้ — None = ไม่กรอง (SuperAdmin ดูทุกแผนก)
    SuperAdmin ส่ง ?department= มาเพื่อเลือกดูทีละแผนกได้ แอดมินแผนกถูกล็อกเป็นแผนกตัวเองเสมอ
    (แอดมินที่ยังไม่มีแผนกได้ค่า "" ซึ่งไม่ตรงกับแถวไหนเลย = มองไม่เห็นอะไร)"""
    if is_super_admin(user):
        return requested or None
    return user.department or ""


def check_department(owner_department: Optional[str], user: User, detail: str) -> None:
    """แอดมินแผนกแก้ได้เฉพาะของแผนกตัวเอง — ของที่ยังไม่ระบุแผนก (NULL) แก้ได้แค่ SuperAdmin"""
    if is_super_admin(user):
        return
    if not user.department or owner_department != user.department:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def owner_department_for(user: User, requested: Optional[str] = None) -> Optional[str]:
    """แผนกที่จะติดให้ของที่สร้างใหม่ — แอดมินแผนกได้แผนกตัวเองเสมอ, SuperAdmin เลือกได้ (ไม่เลือก = ยังไม่ระบุ)"""
    if is_super_admin(user):
        return requested or None
    return user.department


def department_column_filter(column, department: Optional[str]):
    """เงื่อนไข WHERE ของคอลัมน์แผนก ตามค่าที่ได้จาก scope_department — None = ไม่กรอง"""
    if department is None:
        return None
    if department == UNASSIGNED:
        return column.is_(None)
    return column == department


async def department_filenames(db: AsyncSession, department: str) -> Set[str]:
    rows = await db.execute(
        select(Document.filename).where(department_column_filter(Document.department, department))
    )
    return set(rows.scalars().all())


async def history_scope_filter(db: AsyncSession, user: User, requested: Optional[str] = None):
    """เงื่อนไข WHERE ของ ChatHistory ที่ผู้ใช้คนนี้เห็นได้ — None = เห็นทั้งหมด (SuperAdmin ไม่เลือกแผนก)"""
    dept = scope_department(user, requested)
    if dept is None:
        return None
    return history_department_filter(await department_filenames(db, dept))


def _like_json_item(value: str) -> str:
    """pattern ของ LIKE ที่จับ "value" ใน JSON array (escape % และ _ ซึ่งพบบ่อยในชื่อไฟล์)
    escape [ ด้วย — SQL Server ถือว่า [...] ใน LIKE เป็นชุดตัวอักษร (MySQL/TiDB อ่าน \\[ เป็น [ ตรงตัวเหมือนเดิม)"""
    item = json.dumps(value, ensure_ascii=False)
    return "%" + (item.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                  .replace("[", "\\[")) + "%"


def history_department_filter(filenames: Iterable[str]):
    """เงื่อนไข WHERE ของประวัติที่เกี่ยวกับเอกสารชุดนี้
    ใช้ cited_docs (เอกสารที่คำตอบอิงจริง) — แถวเก่าที่ยังไม่มี cited_docs ใช้ referenced_docs
    (ทุกเอกสารที่ค้นเจอ) แทน ซึ่งกว้างกว่า แต่ไม่ทำให้ประวัติเก่าหายไปจากแผนก"""
    filenames = list(filenames)
    if not filenames:
        return ChatHistory.id.is_(None)  # ไม่มีเอกสารเลย = ไม่เห็นประวัติใด (id เป็น PK ไม่มีวัน NULL)
    cited = or_(*[ChatHistory.cited_docs.like(_like_json_item(f), escape="\\") for f in filenames])
    legacy = or_(*[ChatHistory.referenced_docs.like(_like_json_item(f), escape="\\") for f in filenames])
    return or_(cited, ChatHistory.cited_docs.is_(None) & legacy)


def answer_documents(rag_results: List[dict], cited_results: List[dict]) -> List[str]:
    """เอกสารที่คำตอบนี้ "เกี่ยวกับ" — ถ้ามีเอกสารที่ถูกอ้างอิงใช้ชุดนั้น ไม่มี (ตอบไม่ได้/ไม่ใช้ RAG)
    ใช้เอกสารอันดับ 1 ที่ค้นเจอ ซึ่งเป็นตัวเดียวกับที่ใช้เดาแผนกของคำถามที่ตอบไม่ได้"""
    def _sources(results):
        out = []
        for r in results or []:
            src = ((r or {}).get("metadata") or {}).get("source")
            if src and src not in out:
                out.append(src)
        return out

    cited = _sources(cited_results)
    if cited:
        return cited
    top = _sources(rag_results)
    return top[:1]


async def guess_department(db: AsyncSession, filenames: List[str]) -> Optional[str]:
    """แผนกที่เป็นเจ้าของเอกสารชุดนี้มากที่สุด (เสมอกันเลือกตามลำดับเอกสาร) — ไม่มีแผนกเลยคืน None"""
    if not filenames:
        return None
    rows = await db.execute(
        select(Document.filename, Document.department).where(Document.filename.in_(filenames))
    )
    dept_of = {fn: dept for fn, dept in rows.all() if dept}
    ordered = [dept_of[f] for f in filenames if f in dept_of]
    if not ordered:
        return None
    counts = Counter(ordered)
    best = max(counts.values())
    return next(d for d in ordered if counts[d] == best)
