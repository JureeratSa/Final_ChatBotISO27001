"""
Full Pipeline Server — LLM จริงไป OpenRouter, DB = SQLite local (ไม่ต้องใช้ Docker/MySQL)

ใช้คู่กับ locustfile_full.py หรือ eval/run_eval.py ตอนอยากประเมินคำตอบจริงจาก LLM
ต่างจาก mock_server.py ตรงที่ "ไม่" stub query_rag ออก — เรียก OpenRouter จริง
ต้องตั้ง OPENROUTER_API_KEY หรือ GEMINI_API_KEY ใน Backend/.env ก่อน ไม่งั้นจะ fallback
ไป Ollama local (ถ้ามี) หรือ fallback answer เฉยๆ

รัน:
    python TestPFM/run_full_server.py
    -> เปิดที่ http://localhost:8000
"""
import sys
import asyncio
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "Backend"
sys.path.insert(0, str(BACKEND_DIR))

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# config.py โหลด .env แบบ relative path ซึ่งอิงกับ CWD ตอนรัน ไม่ใช่ตำแหน่งไฟล์ config.py เอง
# ถ้ารันจากที่อื่นที่ไม่ใช่ Backend/ (เช่นรันจาก repo root ตามคำสั่งด้านล่าง) จะหา .env ไม่เจอ
# และ OPENROUTER_API_KEY/GEMINI_API_KEY จะว่างเปล่าทั้งที่ตั้งไว้จริง — load ตรงๆ ด้วย path เต็มก่อน
from dotenv import load_dotenv  # noqa: E402
load_dotenv(BACKEND_DIR / ".env")

from db_patch import patch_database  # noqa: E402
patch_database()

from app.main import app  # noqa: E402
from app.core.config import settings  # noqa: E402


if __name__ == "__main__":
    import uvicorn

    has_key = bool(settings.LLM_API_KEY)
    print("=" * 70)
    print("FULL PIPELINE SERVER — LLM จริงไป OpenRouter (มีต้นทุนจริงต่อ request)")
    print(f"API key พบแล้ว: {has_key}" + ("" if has_key else "  (จะ fallback ไป Ollama local หรือ fallback answer)"))
    print("DB: SQLite local (ไม่ต้องใช้ Docker/MySQL)")
    print("Listening: http://localhost:8000")
    print("=" * 70)
    uvicorn.run(app, host="0.0.0.0", port=8000)
