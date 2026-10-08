# TUH Chatbot SPO Test Runner (testchatbotSPO)

โฟลเดอร์สำหรับรันเทสระบบแชทบอทของโรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ พร้อมออกรายงาน Excel สวยงาม

## โครงสร้างไฟล์ในโฟลเดอร์

```
testchatbotSPO/
├── run_test.py                                          # สคริปต์หลักสำหรับรันเทสและสร้าง Excel
├── add_chunks_to_excel.py                               # สคริปต์ดึง Chunk & หัวข้อจาก Admin History เติมลง Excel
├── evaluate_accuracy.py                                 # สคริปต์ประเมิน Accuracy ด้วย Gemma 4 26B
├── evaluate_with_llama.py                               # สคริปต์ประเมินเปรียบเทียบข้ามโมเดล (Gemma 4 vs Llama 3.3 70B) ลงชีท accllm
├── add_summary_sheet.py                                 # สคริปต์สร้างชีท summary สรุปภาพรวม Inter-Model Evaluation
├── questions_dataset.csv                                # ชุดคำถาม ISO (80 ข้อ) รูปแบบ CSV
├── questions_dataset.xlsx                               # ชุดคำถาม ISO (80 ข้อ) รูปแบบ Excel
├── test_result_gemma_all_80_questions_with_chunks_accllm_summary.xlsx # [ล่าสุด] รวมชีท summary + accllm + ข้อมูลเทส
└── README.md                                            # คู่มือการใช้งาน
```

## คอลัมน์ในตารางผลการทดสอบ Excel (.xlsx)

1. **ข้อที่**: ลำดับข้อในการทดสอบ
2. **หัวข้อของคำถาม**: หมวดหมู่นโยบาย ISO ของคำถามนั้นๆ (Category)
3. **คำถาม**: ข้อความคำถามที่ส่งเข้าแชทบอท (สุ่มลำดับ)
4. **คำตอบที่บอทตอบ**: ข้อความตอบกลับจริงจากแชทบอท (RAG Pipeline + Google Gemma 4 26B A4B IT)
5. **คำตอบที่คาดหวัง**: คำตอบตามเกณฑ์มาตรฐาน (Golden Answer)
6. **Chunk ที่ใช้ตอบ (Chunk IDs)**: รหัส Chunk ที่ RAG ดึงมาใช้ตอบจริงจากประวัติหลังบ้าน (เช่น `#139, #137`)
7. **เอกสารและหน้าที่ Chunk สังกัด**: ชื่อไฟล์ PDF นโยบายและเลขหน้าที่ Chunk นั้นอยู่
8. **เวลาในการตอบ**: เวลาที่บอทใช้ในการตอบสนอง (Response Time เป็นวินาที)

## การรันสคริปต์

ก่อนรันสคริปต์ ให้มั่นใจว่าได้สตาร์ท Backend เรียบร้อยแล้ว:
```bash
python run_backend.py
```

### คำสั่งรันเทส:

1. **รันเทสแบบสุ่ม (ค่าเริ่มต้น ใช้ไฟล์ชุดคำถามในโฟลเดอร์หรือ Google Sheets):**
   ```bash
   py testchatbotSPO/run_test.py
   ```

2. **ทดสอบแบบสุ่มเฉพาะ 10 ข้อแรก (เพื่อความรวดเร็ว):**
   ```bash
   py testchatbotSPO/run_test.py --limit 10
   ```

3. **ดึงชุดคำถามจาก Google Sheets URL:**
   ```bash
   py testchatbotSPO/run_test.py --sheet "https://docs.google.com/spreadsheets/d/1M3KaHBdxmUsE6zg716IW-QmpWe32hNxUxUF6T62SGZQ/edit?usp=sharing"
   ```
   > **หมายเหตุ:** หาก Google Sheets ติดสิทธิ์ 401 Unauthorized (Private) ให้เปิดแชร์เป็น "ทุกคนที่มีลิงก์ (Anyone with the link)" ใน Google Sheets หรือให้สคริปต์ดึงจากไฟล์สำรอง `questions_dataset.csv` โดยอัตโนมัติ

4. **ระบุชื่อไฟล์ผลลัพธ์ Excel เอง:**
   ```bash
   py testchatbotSPO/run_test.py --limit 15 --output "my_test_result.xlsx"
   ```

5. **ปรับหน่วงเวลา (วินาที) ระหว่างข้อ (เพื่อป้องกัน Rate Limit 429):**
   ```bash
   py testchatbotSPO/run_test.py --delay 2.5
   ```
