"""
รัน Server จริง (retrieval-only, LLM stub) ต่อ TiDB Serverless "test cluster" จริง
(ไม่ใช่ SQLite local เหมือน mock_server.py) — เพื่อวัดตัวเลข throughput/latency ที่ใกล้เคียง
production จริงกว่า (TiDB lock ระดับแถว ต่างจาก SQLite ที่ lock ทั้งไฟล์)

⚠️ ต้องชี้ Backend/.env ไปที่ TiDB Serverless คลัสเตอร์ "แยกต่างหาก" สำหรับทดสอบเท่านั้น
   ห้ามชี้ไปคลัสเตอร์ production เด็ดขาด (จะเขียน ChatHistory/UnansweredQuery จริงปนกับข้อมูลจริง)
   สร้างคลัสเตอร์ทดสอบใหม่ได้ฟรีที่ https://tidbcloud.com -> Create Cluster -> Serverless
   (ใช้เวลาสร้างไม่ถึงนาที ฟรี tier รองรับได้หลายคลัสเตอร์พร้อมกัน)

ต่างจาก mock_server.py ตรงที่ "ไม่" เรียก db_patch.patch_database() เลย — ปล่อยให้ app ใช้ engine
ตัวจริงจาก Backend/app/core/database.py ซึ่งอ่านค่า DB_HOST/DB_USER/DB_PASSWORD/DB_NAME จาก
Backend/.env ตามปกติ (เหมือน production ทุกอย่าง ยกเว้นชี้คนละคลัสเตอร์)

รัน:
    python TestPFM/run_tidb_test_server.py
    -> เปิดที่ http://localhost:8002 (คนละ port กับ mock_server.py :8001 และ run_full_server.py :8000)
"""
import sys
import asyncio
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "Backend"
sys.path.insert(0, str(BACKEND_DIR))

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# config.py โหลด .env แบบ relative path ("Config.env_file = '.env'") ซึ่งอิงกับ CWD ตอนรัน
# ไม่ใช่ตำแหน่งไฟล์ config.py เอง — ถ้ารันสคริปต์นี้จากที่อื่นที่ไม่ใช่ Backend/ จะหา .env ไม่เจอ
# เลย load ตรงๆ ด้วย path เต็มก่อน import settings เพื่อกันปัญหานี้เสมอไม่ว่าจะรันจากไหน
from dotenv import load_dotenv  # noqa: E402
load_dotenv(BACKEND_DIR / ".env")

from app.core.config import settings  # noqa: E402

# ─── Safety guard: กันพลาดยิงโหลดใส่ TiDB Cloud production ───────────────────
# ค่านี้คือ DB_USER ของ production ที่ hardcode ไว้เป็น default ใน app/core/config.py
# ถ้า .env ยังไม่ได้ override เป็นคลัสเตอร์ทดสอบ ให้หยุดทันทีก่อนเผลอยิงโหลดใส่ของจริง
_PRODUCTION_DB_USER = "2LejCpHSLet7wXP.root"
if settings.DB_USER == _PRODUCTION_DB_USER:
    print("=" * 70)
    print("❌ หยุดทำงาน: Backend/.env ยังไม่ได้ override DB_USER")
    print("   ตอนนี้ระบบกำลังจะต่อ TiDB Cloud PRODUCTION ตามค่า default ใน config.py")
    print("   ต้องตั้ง DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME ใน Backend/.env")
    print("   ให้ชี้ไปคลัสเตอร์ TEST ที่แยกไว้ต่างหากก่อน แล้วค่อยรันใหม่")
    print("=" * 70)
    sys.exit(1)

import app.routers.chat as chat_module  # noqa: E402


async def _fast_stub_query_rag(query, results, config, history, forms=None):
    """เหมือน mock_server.py — ตัด LLM call จริงออก วัดเฉพาะ retrieval + TiDB write"""
    if results:
        source = results[0]["metadata"].get("source", "เอกสาร")
        return (f"[MOCK] พบข้อมูลอ้างอิงจาก {source}", True, "mock-llm")
    return ("[MOCK] ไม่พบข้อมูลที่เกี่ยวข้องในระบบ ขออภัยครับ", False, "mock-llm")


chat_module.query_rag = _fast_stub_query_rag

from app.main import app  # noqa: E402


if __name__ == "__main__":
    import uvicorn

    print("=" * 70)
    print("TIDB TEST SERVER — Retrieval-only, DB = TiDB Serverless (test cluster)")
    print(f"DB_HOST: {settings.DB_HOST}")
    print(f"DB_NAME: {settings.DB_NAME}")
    print("Listening: http://localhost:8002")
    print("=" * 70)

    config = uvicorn.Config(app, host="0.0.0.0", port=8002)
    server = uvicorn.Server(config)

    if sys.platform == "win32":
        # uvicorn.run()/asyncio.run() ไม่เคารพ set_event_loop_policy() อีกต่อไปบน Python 3.14
        # (พิสูจน์แล้วว่า loop ที่ได้จริงข้างในยังเป็น ProactorEventLoop) ทำให้ WinError 87 SSL bug
        # ที่ main.py พยายามแก้ด้วยวิธีเดิม "ไม่ทำงาน" จริงเวลาต่อ TiDB ผ่าน aiomysql — ต้องสร้าง
        # SelectorEventLoop เองแล้วรันตรงๆ แทนการพึ่ง asyncio.run() ถึงจะเลี่ยงบั๊กนี้ได้จริง
        loop = asyncio.SelectorEventLoop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(server.serve())
    else:
        asyncio.run(server.serve())
