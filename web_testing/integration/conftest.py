"""
conftest สำหรับ Integration Test (web_testing/integration/) — เพิ่ม Backend/ เข้า sys.path
เหมือน web_testing/unit/conftest.py แล้ว "ยืม" fixture ชุดเดิมจาก Backend/tests/conftest.py
มาใช้ตรงๆ (import ฟังก์ชันที่ decorate ด้วย @pytest_asyncio.fixture เข้ามา แล้ว pytest จะเห็น
เป็น fixture ปกติเพราะชื่อยังอยู่ใน namespace ของไฟล์นี้) แทนที่จะ copy โค้ด SQLite/FastAPI
test-app setup มาซ้ำอีกชุด กัน 2 ชุดนี้ drift ออกจากกันในอนาคต

หมายเหตุ: SQLite in-memory เท่านั้น ไม่แตะ TiDB Cloud ของจริง (CLAUDE.md กฎข้อ 1) — ดูรายละเอียด
เต็มของแต่ละ fixture ได้ที่ Backend/tests/conftest.py
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "Backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))  # ให้ import Admin.emb ได้ (เหมือน web_testing/unit/conftest.py)

from tests.conftest import (  # noqa: F401 — re-export เป็น fixture ให้เทสในโฟลเดอร์นี้เห็น
    test_engine, session_maker, app_instance, client, db_session,
    admin_user, staff_user, other_staff_user, auth_header,
)
