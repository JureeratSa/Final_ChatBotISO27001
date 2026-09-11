"""
Mock Server — สำหรับ Retrieval-only Load Test (ไม่ต้องใช้ Docker/MySQL เลย)

รัน FastAPI app จริงทั้งหมด (Custom FAQ -> HybridRetriever (Chroma+BM25+RRF) -> Citations -> DB write)
แต่ "ตัด" การเรียก LLM จริงออก (query_rag ถูก monkeypatch ให้ตอบทันทีแบบ deterministic)
เพื่อวัด throughput/latency ของ pipeline ฝั่งเราเอง แยกออกจาก network latency ของ OpenRouter
(หลักการเดียวกับที่ Backend/tests/test_chat.py mock query_rag ไว้สำหรับ unit test)

DB: ใช้ SQLite local ผ่าน db_patch.py (ดูคำเตือนเรื่อง concurrency ในไฟล์นั้น)
    รับประกันไม่แตะ TiDB Cloud production ไม่ว่า .env จะตั้งค่าอะไรไว้ก็ตาม

รัน:
    python TestPFM/mock_server.py
    -> เปิดที่ http://localhost:8001 (คนละ port กับ server จริงที่ 8000 กันชนกัน)
"""
import sys
import asyncio
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "Backend"
sys.path.insert(0, str(BACKEND_DIR))

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from db_patch import patch_database  # noqa: E402
patch_database()

import app.routers.chat as chat_module  # noqa: E402


async def _fast_stub_query_rag(query, results, config, history, forms=None):
    """
    แทนที่ LLM call จริง (OpenRouter/Ollama) ด้วยคำตอบทันที ไม่มี network call
    ส่วนที่เหลือของ pipeline (custom FAQ check, retriever.query, citation build, DB write)
    ยังรันจริงทั้งหมด เพื่อ isolate ต้นทุนของฝั่งเราเองออกจากต้นทุนของ LLM ภายนอก
    """
    if results:
        source = results[0]["metadata"].get("source", "เอกสาร")
        return (f"[MOCK] พบข้อมูลอ้างอิงจาก {source}", True, "mock-llm")
    return ("[MOCK] ไม่พบข้อมูลที่เกี่ยวข้องในระบบ ขออภัยครับ", False, "mock-llm")


# ต้อง patch ก่อน import app.main (ซึ่งจะ mount router ที่ผูกกับ chat_module ตัวเดียวกันนี้)
chat_module.query_rag = _fast_stub_query_rag

from app.main import app  # noqa: E402


if __name__ == "__main__":
    import uvicorn

    print("=" * 70)
    print("MOCK SERVER — Retrieval-only (LLM call ถูก stub ออกแล้ว ไม่ต้องมี API key)")
    print("วัด throughput/latency ของ Custom FAQ + HybridRetriever(Chroma+BM25+RRF) + DB")
    print("DB: SQLite local (ไม่ต้องใช้ Docker/MySQL)")
    print("Listening: http://localhost:8001")
    print("=" * 70)
    uvicorn.run(app, host="0.0.0.0", port=8001)
