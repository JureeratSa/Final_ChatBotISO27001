"""
กำหนดแผนกให้ข้อมูลเดิมหลังรัน migration a7c3e5d9f1b2 (add department scoping)

- เอกสาร / แบบฟอร์มที่ยังไม่มีแผนก → แผนกตั้งต้น (--default, ค่าเริ่มต้น "งานสารสนเทศ")
  แล้ว SuperAdmin ค่อยย้ายรายไฟล์ที่เป็นของแผนกอื่นจากหน้า AdminWeb
- คำถามที่บอทตอบไม่ได้ที่ยังไม่มีแผนก → เดาจากประวัติคำตอบล่าสุดของคำถามเดียวกัน
  (เอกสารที่ค้นเจอตอนนั้น) ถ้าหาประวัติไม่เจอปล่อยว่างไว้ (เห็นแค่ SuperAdmin)
- history.cited_docs ของแถวเก่าไม่เติม — ระบบกรองด้วย referenced_docs แทนอยู่แล้ว

รันจากโฟลเดอร์ Backend:
    python scripts/backfill_departments.py            # ดูผลก่อน ไม่เขียนอะไรลง DB
    python scripts/backfill_departments.py --apply    # เขียนจริง
"""
import argparse
import asyncio
import json
import os
import sys

sys.path.insert(0, os.getcwd())

from sqlalchemy import func, select  # noqa: E402

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.models.models import ChatHistory, Document, Form, UnansweredQuery  # noqa: E402
from app.services.department_scope import guess_department  # noqa: E402


async def main(default_department: str, apply: bool) -> None:
    async with AsyncSessionLocal() as db:
        docs = (await db.execute(select(Document).where(Document.department.is_(None)))).scalars().all()
        print(f"เอกสารที่ยังไม่มีแผนก {len(docs)} ไฟล์ → {default_department}")
        for d in docs:
            print(f"  - {d.filename}")
            d.department = default_department

        forms = (await db.execute(select(Form).where(Form.department.is_(None)))).scalars().all()
        print(f"แบบฟอร์มที่ยังไม่มีแผนก {len(forms)} รายการ → {default_department}")
        for f in forms:
            print(f"  - {f.name}")
            f.department = default_department

        # ให้ guess_department เห็นแผนกที่เพิ่งกำหนดด้านบน (ยังไม่ commit)
        await db.flush()

        unanswered = (await db.execute(
            select(UnansweredQuery).where(UnansweredQuery.department.is_(None))
        )).scalars().all()
        guessed = 0
        for u in unanswered:
            row = (await db.execute(
                select(ChatHistory.referenced_docs)
                .where(func.lower(ChatHistory.query) == u.query.strip().lower())
                .order_by(ChatHistory.timestamp.desc())
                .limit(1)
            )).scalar_one_or_none()
            dept = await guess_department(db, json.loads(row or "[]"))
            if dept:
                u.department = dept
                guessed += 1
        print(f"คำถามที่ตอบไม่ได้ที่ยังไม่มีแผนก {len(unanswered)} รายการ → เดาแผนกได้ {guessed} รายการ"
              f" (ที่เหลือ {len(unanswered) - guessed} รายการเห็นแค่ SuperAdmin)")

        if apply:
            await db.commit()
            print("บันทึกลงฐานข้อมูลแล้ว")
        else:
            await db.rollback()
            print("ยังไม่ได้บันทึก (dry run) — ใส่ --apply เพื่อเขียนจริง")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--default", default="งานสารสนเทศ", help="แผนกตั้งต้นของเอกสาร/แบบฟอร์มเดิม")
    parser.add_argument("--apply", action="store_true", help="เขียนลงฐานข้อมูลจริง")
    args = parser.parse_args()
    if sys.platform == "win32":
        # aiomysql บน Windows ต้องใช้ selector event loop
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main(args.default, args.apply))
