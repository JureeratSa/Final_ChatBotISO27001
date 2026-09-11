"""
Load/Stress Test — Full pipeline (ของจริงทั้งหมด รวม LLM call ไป OpenRouter)

⚠️ ต่างจาก locustfile_retrieval.py ตรงที่ยิงใส่ server จริง (:8000) ที่มี LLM_API_KEY จริง
   ผลกระทบที่ต้องรู้ก่อนรัน:
     - เสียเงินจริงต่อ request (ค่า OpenRouter token) — อย่ารันจำนวน user สูงๆ นานๆ
     - OpenRouter มี rate limit ของตัวเอง — error ที่เห็นอาจมาจาก OpenRouter ไม่ใช่ระบบเราพัง
       (ดู error message ใน response ประกอบก่อนสรุปว่า "ระบบรับโหลดไม่ไหว")
     - ถ้า RATE_LIMIT_* ใน Backend/app/core/config.py ถูกนำมาบังคับใช้จริงในอนาคต
       (ตอนนี้ยังไม่มี middleware ใช้ค่านี้) ก็จะกระทบผลตรงนี้ด้วย
   แนะนำให้เริ่มด้วย concurrency ต่ำๆ ก่อนเสมอ (-u 5 -r 1)

รัน:
    locust -f TestPFM/locustfile_full.py --host http://localhost:8000 \
        --headless -u 5 -r 1 -t 2m --csv TestPFM/results/full_5u
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from queries import RAG_QUERIES  # noqa: E402

from locust import HttpUser, task, between


class FullPipelineUser(HttpUser):
    # ช่วงห่างกว้างกว่า retrieval test เพราะแต่ละ request มีต้นทุนจริง (เงิน+rate limit)
    wait_time = between(3, 6)

    @task
    def ask_rag_question(self):
        query = random.choice(RAG_QUERIES)
        self.client.post("/api/chat", json={"query": query}, name="/api/chat [full]")
