import os
import sys
import json
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent

load_dotenv(PROJECT_ROOT / "Backend" / ".env")
load_dotenv(PROJECT_ROOT / ".env")

api_key = (os.getenv("OPENROUTER_API_KEY") or "").split()[0]
print(f"API Key loaded: {'yes' if api_key else 'no'} (len={len(api_key)})")

prompt = """คุณคือผู้ประเมินคุณภาพของระบบ AI Chatbot (LLM-as-a-Judge) สำหรับเอกสารมาตรฐาน ISO โรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ
หน้าที่ของคุณคือตัดสินคะแนนความถูกต้องของคำตอบจาก Chatbot เปรียบเทียบกับคำตอบที่คาดหวัง (Expected Answer) อย่างเป็นกลางและเข้มงวด

[คำถาม]:
เมื่อมีการเปลี่ยนแปลงโครงสร้างพื้นฐานของระบบงาน มีข้อกำหนดให้ต้องดำเนินการอย่างไรต่อไป

[คำตอบที่คาดหวัง (Expected Answer / Golden Answer)]:
ต้องมีการทบทวนและทดสอบความมั่นคงปลอดภัยของระบบงานนั้น เพื่อให้มั่นใจว่าไม่มีผลกระทบในทางลบต่อการดำเนินงานของโรงพยาบาล

[คำตอบจาก Chatbot (Actual Answer)]:
หากมีการเปลี่ยนแปลงโครงสร้างพื้นฐานของระบบงาน พี่ๆ จะต้องทำการทบทวนและทดสอบความมั่นคงปลอดภัยของระบบงานนั้นด้วยครับ เพื่อให้มั่นใจว่าการเปลี่ยนแปลงดังกล่าวจะไม่ส่งผลกระทบในทางลบต่อการดำเนินงานของโรงพยาบาลเราครับ

---
เกณฑ์การตัดสินให้คะแนนอย่างเป็นกลางและเข้มงวด:
1.0 = "ถูกต้อง": สาระสำคัญและข้อเท็จจริงหลักครบถ้วน สอดคล้องกับคำตอบที่คาดหวัง (แม้สำนวนภาษาต่างกัน หรือมีรายละเอียดเพิ่มเติมที่ถูกต้อง)
0.5 = "ถูกต้องบางส่วน": ตอบถูกบางประเด็นสำคัญ แต่ขาดรายละเอียดสำคัญบางข้อ หรือมีเนื้อหาที่ยังไม่ชัดเจน/คลุมเครือ
0.0 = "ไม่ถูกต้อง": ตอบผิดจากข้อเท็จจริง, ไม่ตรงประเด็นกับคำถาม, มีข้อมูลเท็จ (Hallucination), หรือตอบว่าไม่พบข้อมูลทั้งที่คำตอบที่คาดหวังมีข้อมูล

กรุณาตอบผลการประเมินเป็น JSON Format ดังนี้เท่านั้น (ห้ามใส่ markdown fence หรือคำเกริ่นนำ):
{
  "score": 1.0,
  "verdict": "ถูกต้อง",
  "reason": "อธิบายเหตุผลสั้นๆ 1-2 ประโยคว่าทำไมถึงได้คะแนนนี้"
}
"""

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
    "HTTP-Referer": "http://localhost:8000",
    "X-Title": "TUH Chatbot Evaluation Judge"
}

payload = {
    "model": "anthropic/claude-3-haiku",
    "messages": [
        {"role": "system", "content": "You are a precise, objective Thai QA evaluation judge. Output only raw JSON."},
        {"role": "user", "content": prompt}
    ],
    "temperature": 0.0,
    "max_tokens": 300
}

t0 = time.time()
resp = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=30)
elapsed = time.time() - t0
print(f"Status Code: {resp.status_code} in {elapsed:.2f}s")
if resp.status_code == 200:
    content = resp.json()["choices"][0]["message"]["content"]
    print("Content:")
    print(content)
else:
    print(resp.text)
