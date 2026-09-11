"""
Load/Stress Test — Retrieval-only pipeline
(Custom FAQ -> HybridRetriever(Chroma+BM25+RRF) -> Citations -> DB write, ไม่แตะ LLM จริง)

Prerequisite: เปิด mock_server.py ไว้ก่อน (python TestPFM/mock_server.py -> :8001)

รันแบบมี UI (ปรับจำนวน user/spawn rate สดๆ ผ่าน browser):
    locust -f TestPFM/locustfile_retrieval.py --host http://localhost:8001
    แล้วเปิด http://localhost:8089

รันแบบ headless (กำหนด user/เวลาเองตรงๆ เหมาะกับ CI หรือรันซ้ำๆ):
    locust -f TestPFM/locustfile_retrieval.py --host http://localhost:8001 \
        --headless -u 100 -r 10 -t 3m --csv TestPFM/results/retrieval_100u

หรือใช้ run_stress_sweep.py เพื่อไล่ concurrency หลายระดับอัตโนมัติแล้วสรุปตารางเดียว
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from queries import RAG_QUERIES, CHITCHAT_QUERIES, UNKNOWN_QUERIES  # noqa: E402

from locust import HttpUser, task, between


class RetrievalUser(HttpUser):
    # user คิดก่อนพิมพ์คำถามถัดไป 1-3 วิ (mimic คนจริงพิมพ์แชท)
    wait_time = between(1, 3)

    @task(7)
    def ask_rag_question(self):
        """คำถามสวัสดิการทั่วไป — เส้นทางหลัก ต้องผ่าน retriever จริง"""
        query = random.choice(RAG_QUERIES)
        self.client.post("/api/chat", json={"query": query}, name="/api/chat [rag]")

    @task(2)
    def ask_unknown_question(self):
        """คำถามนอกเรื่อง — วัด fallback / unanswered-logging path"""
        query = random.choice(UNKNOWN_QUERIES)
        self.client.post("/api/chat", json={"query": query}, name="/api/chat [unknown]")

    @task(1)
    def chit_chat(self):
        """
        ทักทาย/ขอบคุณ — ดู chat.py แล้วพบว่า "ไม่" short-circuit ก่อน retriever แต่อย่างใด
        (มีแค่ custom FAQ เท่านั้นที่ข้าม retriever ได้ ดู step 2 ใน routers/chat.py)
        retriever.query() ยังถูกเรียกเหมือน RAG query ปกติ แล้วค่อยถูกทิ้งใน query_rag()
        เก็บ task นี้ไว้เพื่อวัด cost ของคำถามสั้นๆ เทียบกับคำถามยาว ไม่ใช่ baseline ที่ไม่มี retriever
        """
        query = random.choice(CHITCHAT_QUERIES)
        self.client.post("/api/chat", json={"query": query}, name="/api/chat [chitchat]")

    @task(1)
    def get_settings(self):
        self.client.get("/api/chat/settings")
