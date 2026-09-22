"""
conftest สำหรับ Unit Test (web_testing/unit/) — เพิ่ม Backend/ เข้า sys.path เพื่อ import
โมดูล app.* ได้เหมือนรันจาก Backend/ ตรงๆ โดยไม่ต้องย้ายไฟล์เข้าไปอยู่ใน Backend/tests/
และเพิ่ม project root เข้า sys.path เพื่อ import Admin.emb ได้แบบเดียวกับที่
Backend/app/services/rag_service.py ทำตอนโหลด HybridRetriever จริง

หมายเหตุ: Backend/app/core/config.py หาไฟล์ .env ด้วย absolute path ของตัวเองอยู่แล้ว
(ดู _backend_dir ใน config.py) จึงไม่ต้องสนใจว่ารัน pytest จาก working directory ไหน
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "Backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
