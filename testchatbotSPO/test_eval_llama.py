import os
import json
import requests
from dotenv import load_dotenv

load_dotenv("Backend/.env")
api_key = os.getenv("OPENROUTER_API_KEY")

prompt = """คุณคือผู้ประเมินคุณภาพของระบบ AI Chatbot (LLM-as-a-Judge) สำหรับเอกสารมาตรฐาน ISO โรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ
หน้าที่ของคุณคือตัดสินคะแนนความถูกต้องของคำตอบจาก Chatbot เปรียบเทียบกับคำตอบที่คาดหวัง (Expected Answer)

[คำถาม]:
นโยบายการสำรองข้อมูลมีรอบการสำรองอย่างไร

[คำตอบที่คาดหวัง (Expected Answer / Golden Answer)]:
กำหนดให้มีการสำรองข้อมูลทุกวัน (Daily) และสัปดาห์ละครั้ง (Weekly)

[คำตอบจาก Chatbot (Actual Answer)]:
ระบบกำหนดให้สำรองข้อมูลประจำวัน และรายสัปดาห์ โดยเก็บสำรองไว้อย่างน้อย 30 วัน

---
เกณฑ์การตัดสินให้คะแนนอย่างเป็นกลางและเข้มงวด:
1.0 = "ถูกต้อง": สาระสำคัญและข้อเท็จจริงหลักครบถ้วน สอดคล้องกับคำตอบที่คาดหวัง
0.5 = "ถูกต้องบางส่วน": ตอบถูกบางประเด็นสำคัญ แต่ขาดรายละเอียดสำคัญบางข้อ หรือมีเนื้อหาที่ยังไม่ชัดเจน/คลุมเครือ
0.0 = "ไม่ถูกต้อง": ตอบผิดจากข้อเท็จจริง, ไม่ตรงประเด็นกับคำถาม, มีข้อมูลเท็จ (Hallucination)

กรุณาตอบผลการประเมินเป็น JSON Format ดังนี้เท่านั้น:
{
  "score": 1.0,
  "verdict": "ถูกต้อง",
  "reason": "อธิบายเหตุผลสั้นๆ 1-2 ประโยคว่าทำไมถึงได้คะแนนนี้"
}
"""

r = requests.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    json={
        "model": "meta-llama/llama-3.3-70b-instruct",
        "messages": [
            {"role": "system", "content": "You are an expert AI evaluator. Output only valid JSON."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.0,
        "max_tokens": 300
    },
    timeout=25
)

print("Status:", r.status_code)
print("Content:", r.json()["choices"][0]["message"]["content"])
