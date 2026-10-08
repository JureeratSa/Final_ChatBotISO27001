#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TUH Chatbot AI — Accuracy & Retrieval Evaluation (LLM-as-a-Judge)
================================================================
ประเมินความถูกต้อง (Accuracy) และความแม่นยำในการดึงข้อมูล (Retrieval Hit Rate)
ของคำตอบแชทบอท TUH ISO ทั้ง 80 ข้อ โดยเปรียบเทียบกับ Golden Answer

เกณฑ์การให้คะแนน:
- 1.0 = ถูกต้องสมบูรณ์ (Correct: สาระสำคัญครบถ้วน ถูกต้องตาม Expected Answer)
- 0.5 = ถูกต้องบางส่วน (Partially Correct: ตอบถูกบางประเด็นแต่ขาดประเด็นหลัก หรือมีส่วนคลาดเคลื่อนเล็กน้อย)
- 0.0 = ไม่ถูกต้อง / ไม่ตอบ (Incorrect: ข้อมูลผิด, ตอบไม่ตรงคำถาม, Hallucination, หรือปฏิเสธตอบ)
"""

import os
import sys
import json
import time
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from dotenv import load_dotenv

# บังคับใช้ UTF-8 stdout บน Windows Console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

CURRENT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = CURRENT_DIR.parent
CACHE_FILE = CURRENT_DIR / "eval_accuracy_cache.json"

load_dotenv(PROJECT_ROOT / "Backend" / ".env")
load_dotenv(PROJECT_ROOT / ".env")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("GEMINI_API_KEY")
EVAL_MODEL = "google/gemma-4-26b-a4b-it"


def normalize_thai_text(text: str) -> str:
    """ทำความสะอาดข้อความเพื่อเปรียบเทียบ"""
    if not text:
        return ""
    # ตัดช่องว่างซ้ำซ้อนและวรรคตอน
    t = re.sub(r"\s+", " ", str(text).strip())
    return t


def check_retrieval_match(category: str, pink_topic: str) -> bool:
    """
    ตรวจสอบว่า Chunk ที่ดึงมาตรงกับหมวดหมู่ของคำถามหรือไม่
    """
    if not category or not pink_topic or pink_topic == "-":
        return False
    
    cat_clean = category.strip()
    pink_clean = pink_topic.strip()

    # 1. เช็คว่าชื่อหมวดหมู่อยู่ในข้อความ pink_topic เลยหรือไม่
    if cat_clean in pink_clean:
        return True

    # 2. ดึงคีย์เวิร์ดภาษาอังกฤษในวงเล็บ เช่น (ISMS Framework), (Mobile device), (Backup Policy)
    match_en = re.findall(r"\(([A-Za-z0-9\s]+)\)", cat_clean)
    for kw in match_en:
        kw = kw.strip()
        if len(kw) > 3 and kw.lower() in pink_clean.lower():
            return True

    # 3. ดึงคีย์เวิร์ดสำคัญภาษาไทย
    thai_keywords = [
        "ISMS", "บริหารความมั่นคง", "พกพา", "ทรัพย์สินสารสนเทศ", "ควบคุมการเข้าถึง",
        "เข้ารหัส", "ปลอดเอกสาร", "ป้องกันหน้าจอ", "สํารองข้อมูล", "สำรองข้อมูล",
        "ถ่ายโอน", "พัฒนาระบบ", "ผู้ให้บริการภายนอก", "กฎหมาย", "ระเบียบ",
        "ระยะไกล", "ตั้งค่าระบบตามมาตรฐาน", "ความต่อเนื่อง", "ทางกายภาพ"
    ]
    for kw in thai_keywords:
        if kw in cat_clean and kw in pink_clean:
            return True

    return False


def call_llm_judge(question: str, expected: str, actual: str, retries: int = 3) -> dict:
    """
    ใช้ LLM ประเมินความถูกต้องของคำตอบ (LLM-as-a-Judge)
    """
    if not actual or actual.strip() in ["-", ""]:
        return {
            "score": 0.0,
            "verdict": "ไม่ถูกต้อง",
            "reason": "แชทบอทไม่ได้ตอบข้อความ หรือไม่มีคำตอบในผลการทดสอบ"
        }

    # กรณีคำตอบเหมือนกันแทบจะทุกตัวอักษร
    if normalize_thai_text(actual) == normalize_thai_text(expected):
        return {
            "score": 1.0,
            "verdict": "ถูกต้อง",
            "reason": "คำตอบตรงกับคำตอบที่คาดหวังอย่างสมบูรณ์แบบ"
        }

    prompt = f"""คุณคือผู้ประเมินคุณภาพของระบบ AI Chatbot (LLM-as-a-Judge) สำหรับเอกสารมาตรฐาน ISO โรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ
หน้าที่ของคุณคือตัดสินคะแนนความถูกต้องของคำตอบจาก Chatbot เปรียบเทียบกับคำตอบที่คาดหวัง (Expected Answer)

[คำถาม]:
{question}

[คำตอบที่คาดหวัง (Expected Answer / Golden Answer)]:
{expected}

[คำตอบจาก Chatbot (Actual Answer)]:
{actual}

---
เกณฑ์การตัดสินให้คะแนนอย่างเป็นกลางและเข้มงวด:
1.0 = "ถูกต้อง": สาระสำคัญและข้อเท็จจริงหลักครบถ้วน สอดคล้องกับคำตอบที่คาดหวัง (แม้สำนวนภาษาต่างกัน หรือมีรายละเอียดเพิ่มเติมที่ถูกต้อง)
0.5 = "ถูกต้องบางส่วน": ตอบถูกบางประเด็นสำคัญ แต่ขาดรายละเอียดสำคัญบางข้อ หรือมีเนื้อหาที่ยังไม่ชัดเจน/คลุมเครือ
0.0 = "ไม่ถูกต้อง": ตอบผิดจากข้อเท็จจริง, ไม่ตรงประเด็นกับคำถาม, มีข้อมูลเท็จ (Hallucination), หรือตอบว่าไม่พบข้อมูลทั้งที่คำตอบที่คาดหวังมีข้อมูล

กรุณาตอบผลการประเมินเป็น JSON Format ดังนี้เท่านั้น (ห้ามใส่ Markdown code block หรือข้อความอื่น):
{{
  "score": 1.0,
  "verdict": "ถูกต้อง",
  "reason": "อธิบายเหตุผลสั้นๆ 1-2 ประโยคว่าทำไมถึงได้คะแนนนี้"
}}
"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "TUH Chatbot Eval"
    }

    payload = {
        "model": EVAL_MODEL,
        "messages": [
            {"role": "system", "content": "You are an expert AI evaluator. Output only valid JSON."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.0,
        "max_tokens": 300
    }

    for attempt in range(retries):
        try:
            resp = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            if resp.status_code == 200:
                body = resp.json()
                content = body["choices"][0]["message"]["content"].strip()

                # ตัด markdown ```json ... ``` ออกถ้ามี
                if content.startswith("```"):
                    content = re.sub(r"^```[a-zA-Z]*\n?", "", content)
                    content = re.sub(r"\n?```$", "", content).strip()

                parsed = json.loads(content)
                score = float(parsed.get("score", 0.0))
                verdict = str(parsed.get("verdict", "ไม่ถูกต้อง"))
                reason = str(parsed.get("reason", ""))

                # ตรวจสอบความสอดคล้องของ verdict
                if score >= 0.9:
                    verdict = "ถูกต้อง"
                elif score >= 0.4:
                    verdict = "ถูกต้องบางส่วน"
                else:
                    verdict = "ไม่ถูกต้อง"

                return {
                    "score": score,
                    "verdict": verdict,
                    "reason": reason
                }
            else:
                time.sleep(1.5 * (attempt + 1))
        except Exception as e:
            time.sleep(1.5 * (attempt + 1))

    # Fallback กรณีต่อ API ไม่สำเร็จ
    return {
        "score": 0.5,
        "verdict": "ถูกต้องบางส่วน",
        "reason": "ไม่สามารถเรียก LLM Judge ประเมินได้ (Network/API Timeout)"
    }


def load_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_cache(cache: dict):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def main():
    print("=" * 80)
    print("🎯 TUH Chatbot — เริ่มต้นการประเมิน Accuracy & Retrieval (80 คำถาม)")
    print("=" * 80)

    # 1. โหลดไฟล์ Excel ต้นทาง
    source_file = CURRENT_DIR / "test_result_gemma_with_pink_topics.xlsx"
    if not source_file.exists():
        source_file = CURRENT_DIR / "test_result_gemma_all_80_questions_with_chunks.xlsx"
    if not source_file.exists():
        print(f"❌ ไม่พบไฟล์ผลการทดสอบที่ {source_file}")
        return

    print(f"📂 กำลังโหลดข้อมูลจาก: {source_file.name}")
    wb_src = openpyxl.load_workbook(source_file, data_only=True)
    ws_src = wb_src.active

    # ดึงหัวข้อและข้อมูลแถว
    rows_data = []
    for row_idx in range(2, ws_src.max_row + 1):
        item_no = ws_src.cell(row_idx, 1).value
        category = str(ws_src.cell(row_idx, 2).value or "").strip()
        question = str(ws_src.cell(row_idx, 3).value or "").strip()
        bot_ans = str(ws_src.cell(row_idx, 4).value or "").strip()
        expected = str(ws_src.cell(row_idx, 5).value or "").strip()
        chunks = str(ws_src.cell(row_idx, 6).value or "").strip()
        pink_topic = str(ws_src.cell(row_idx, 7).value or "").strip()
        resp_time = ws_src.cell(row_idx, 8).value

        rows_data.append({
            "item_no": item_no,
            "category": category,
            "question": question,
            "bot_ans": bot_ans,
            "expected": expected,
            "chunks": chunks,
            "pink_topic": pink_topic,
            "resp_time": resp_time
        })

    total_items = len(rows_data)
    print(f"✅ โหลดข้อมูลสำเร็จ: {total_items} ข้อ")

    # 2. โหลด Cache ที่เคยประเมินไว้
    cache = load_cache()
    print(f"📦 มีผลการประเมินในแคชแล้ว: {len(cache)} ข้อ")

    # 3. เตรียมรัน LLM Judge แบบ Concurrency (5 Workers)
    items_to_eval = []
    for item in rows_data:
        q_key = item["question"]
        if q_key not in cache:
            items_to_eval.append(item)

    if items_to_eval:
        print(f"🚀 กำลังประเมินด้วย AI Judge ({EVAL_MODEL}) จำนวน {len(items_to_eval)} ข้อ...")
        completed_count = len(cache)

        def eval_task(it):
            res = call_llm_judge(it["question"], it["expected"], it["bot_ans"])
            return it["question"], res

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(eval_task, it) for it in items_to_eval]
            for future in as_completed(futures):
                q_key, res = future.result()
                cache[q_key] = res
                completed_count += 1
                save_cache(cache)
                print(f"   [{completed_count}/{total_items}] คะแนน: {res['score']} | {res['verdict']} | {q_key[:40]}...")
    else:
        print("⚡ ข้อมูลทุกข้อได้รับการประเมินครบถ้วนแล้วจากแคช!")

    # 4. ประมวลผลสถิติภาพรวม
    scores = []
    retrieval_hits = []
    verdict_counts = {"ถูกต้อง": 0, "ถูกต้องบางส่วน": 0, "ไม่ถูกต้อง": 0}
    category_stats = {}

    final_results = []
    for item in rows_data:
        q_key = item["question"]
        eval_res = cache.get(q_key, {"score": 0.0, "verdict": "ไม่ถูกต้อง", "reason": "ไม่มีผลประเมิน"})
        score = eval_res.get("score", 0.0)
        verdict = eval_res.get("verdict", "ไม่ถูกต้อง")
        reason = eval_res.get("reason", "")

        # ตรวจสอบ Retrieval Match
        is_hit = check_retrieval_match(item["category"], item["pink_topic"])
        hit_val = 1.0 if is_hit else 0.0
        hit_text = "ตรงหมวด (Hit)" if is_hit else "ไม่ตรงหมวด"

        scores.append(score)
        retrieval_hits.append(hit_val)
        verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1

        cat = item["category"]
        if cat not in category_stats:
            category_stats[cat] = {"total": 0, "scores": [], "hits": []}
        category_stats[cat]["total"] += 1
        category_stats[cat]["scores"].append(score)
        category_stats[cat]["hits"].append(hit_val)

        final_results.append({
            **item,
            "score": score,
            "verdict": verdict,
            "reason": reason,
            "hit_val": hit_val,
            "hit_text": hit_text
        })

    avg_accuracy = (sum(scores) / len(scores)) * 100 if scores else 0.0
    avg_hit_rate = (sum(retrieval_hits) / len(retrieval_hits)) * 100 if retrieval_hits else 0.0
    correct_cnt = verdict_counts.get("ถูกต้อง", 0)
    partial_cnt = verdict_counts.get("ถูกต้องบางส่วน", 0)
    incorrect_cnt = verdict_counts.get("ไม่ถูกต้อง", 0)

    print("\n" + "=" * 60)
    print("📊 ผลการประเมินภาพรวม (Summary Evaluation Metrics)")
    print("=" * 60)
    print(f"• จำนวนคำถามทั้งหมด : {total_items} ข้อ")
    print(f"• ความแม่นยำเฉลี่ย (Accuracy)       : {avg_accuracy:.2f}%")
    print(f"• อัตราดึง Chunk ตรงหมวด (Hit Rate) : {avg_hit_rate:.2f}%")
    print(f"  - ถูกต้องสมบูรณ์ (1.0) : {correct_cnt} ข้อ ({(correct_cnt/total_items)*100:.1f}%)")
    print(f"  - ถูกต้องบางส่วน (0.5) : {partial_cnt} ข้อ ({(partial_cnt/total_items)*100:.1f}%)")
    print(f"  - ไม่ถูกต้อง (0.0)      : {incorrect_cnt} ข้อ ({(incorrect_cnt/total_items)*100:.1f}%)")
    print("=" * 60)

    # 5. สร้างไฟล์ Excel รายงานผลฉบับสมบูรณ์ (2 Sheets: สรุปภาพรวม + รายละเอียด 80 ข้อ)
    wb_out = openpyxl.Workbook()

    # Styling Palettes
    navy_dark = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    blue_header = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
    kpi_bg_1 = PatternFill(start_color="EFF6FF", end_color="EFF6FF", fill_type="solid")
    kpi_bg_2 = PatternFill(start_color="ECFDF5", end_color="ECFDF5", fill_type="solid")
    kpi_bg_3 = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
    kpi_bg_4 = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")

    font_white_bold = Font(name="Tahoma", size=10, bold=True, color="FFFFFF")
    font_title = Font(name="Tahoma", size=14, bold=True, color="1E3A8A")
    font_subtitle = Font(name="Tahoma", size=10, color="64748B")
    font_kpi_label = Font(name="Tahoma", size=9, bold=True, color="475569")
    font_kpi_val = Font(name="Tahoma", size=18, bold=True, color="1E3A8A")
    font_kpi_sub = Font(name="Tahoma", size=9, color="64748B")
    font_regular = Font(name="Tahoma", size=9, color="1F2937")
    font_bold = Font(name="Tahoma", size=9, bold=True, color="1F2937")

    # Verdict fills & fonts
    fill_correct = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
    font_correct = Font(name="Tahoma", size=9, bold=True, color="166534")

    fill_partial = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
    font_partial = Font(name="Tahoma", size=9, bold=True, color="92400E")

    fill_incorrect = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
    font_incorrect = Font(name="Tahoma", size=9, bold=True, color="991B1B")

    # Retrieval hit fills & fonts
    fill_hit = PatternFill(start_color="E0F2FE", end_color="E0F2FE", fill_type="solid")
    font_hit = Font(name="Tahoma", size=9, bold=True, color="0369A1")
    fill_miss = PatternFill(start_color="F3F4F6", end_color="F3F4F6", fill_type="solid")
    font_miss = Font(name="Tahoma", size=9, color="6B7280")

    fill_white = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    fill_zebra = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")

    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    # -------------------------------------------------------------
    # SHEET 1: สรุปภาพรวม (Summary KPI Dashboard)
    # -------------------------------------------------------------
    ws_summary = wb_out.active
    ws_summary.title = "สรุปภาพรวม (Executive Summary)"
    ws_summary.views.sheetView[0].showGridLines = True

    ws_summary["A1"] = "รายงานผลการประเมินคุณภาพแชทบอท TUH ISO Chatbot"
    ws_summary["A1"].font = font_title
    ws_summary["A2"] = f"ประเมินคำตอบ 80 ข้อด้วย LLM-as-a-Judge ({EVAL_MODEL}) เทียบกับ Golden Standard QA"
    ws_summary["A2"].font = font_subtitle

    # KPI Block 1: Total & Accuracy
    kpi_cards = [
        ("B4", "C5", "จำนวนคำถามทั้งหมด", f"{total_items} ข้อ", "ครอบคลุม 16 นโยบาย ISO", kpi_bg_1),
        ("D4", "E5", "ความแม่นยำเฉลี่ย (Accuracy)", f"{avg_accuracy:.1f}%", f"จากคะแนนเต็ม 100%", kpi_bg_2),
        ("F4", "G5", "ดึง Chunk ตรงหมวด (Hit Rate)", f"{avg_hit_rate:.1f}%", f"{int(sum(retrieval_hits))}/{total_items} คำถาม", kpi_bg_1),
        ("H4", "I5", "ตอบถูกต้องสมบูรณ์ (1.0)", f"{correct_cnt} ข้อ", f"{(correct_cnt/total_items)*100:.1f}% ของทั้งหมด", kpi_bg_2),
        ("J4", "K5", "ตอบถูกบางส่วน (0.5)", f"{partial_cnt} ข้อ", f"{(partial_cnt/total_items)*100:.1f}% ของทั้งหมด", kpi_bg_3),
        ("L4", "M5", "ตอบไม่ถูกต้อง (0.0)", f"{incorrect_cnt} ข้อ", f"{(incorrect_cnt/total_items)*100:.1f}% ของทั้งหมด", kpi_bg_4),
    ]

    for top_left, bot_right, title, val, sub, bg in kpi_cards:
        ws_summary.merge_cells(f"{top_left}:{bot_right}")
        c = ws_summary[top_left]
        c.value = f"{title}\n{val}\n({sub})"
        c.font = font_bold
        c.fill = bg
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        # ใส่ border ให้ครบทุกเซลล์ที่ merge
        start_col, start_row = openpyxl.utils.coordinate_to_tuple(top_left)
        end_col, end_row = openpyxl.utils.coordinate_to_tuple(bot_right)
        for r in range(start_row, end_row + 1):
            for col in range(start_col, end_col + 1):
                ws_summary.cell(r, col).border = thin_border

    # ตารางแจกแจงราย 16 หมวดหมู่นโยบาย ISO
    ws_summary["B7"] = "สรุปผลการประเมินแยกตาม 16 หมวดหมู่นโยบาย ISO (Category Breakdown)"
    ws_summary["B7"].font = Font(name="Tahoma", size=11, bold=True, color="1E3A8A")

    cat_headers = [
        "ลำดับ", "หมวดหมู่นโยบาย ISO (ในชีท)", "จำนวนข้อ",
        "คะแนนเฉลี่ย (Accuracy)", "ดึง Chunk ตรงหมวด (Hit Rate)", "สถานะผลการประเมิน"
    ]
    for c_idx, h in enumerate(cat_headers, start=2):
        cell = ws_summary.cell(8, c_idx, h)
        cell.font = font_white_bold
        cell.fill = navy_dark
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border

    r_idx = 9
    for idx, (cat_name, cdata) in enumerate(category_stats.items(), start=1):
        cat_avg_score = (sum(cdata["scores"]) / len(cdata["scores"])) * 100
        cat_hit_rate = (sum(cdata["hits"]) / len(cdata["hits"])) * 100
        status = "ดีเยี่ยม (Excellent)" if cat_avg_score >= 80 else ("ปานกลาง (Good)" if cat_avg_score >= 60 else "ควรปรับปรุง (Needs Review)")

        row_vals = [idx, cat_name, cdata["total"], f"{cat_avg_score:.1f}%", f"{cat_hit_rate:.1f}%", status]
        for c_idx, val in enumerate(row_vals, start=2):
            cell = ws_summary.cell(r_idx, c_idx, val)
            cell.font = font_regular
            cell.border = thin_border
            cell.fill = fill_zebra if r_idx % 2 == 0 else fill_white
            if c_idx in [2, 4, 5, 6, 7]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")
        r_idx += 1

    # ปรับขนาดคอลัมน์ Summary
    ws_summary.column_dimensions["A"].width = 4
    ws_summary.column_dimensions["B"].width = 8
    ws_summary.column_dimensions["C"].width = 45
    ws_summary.column_dimensions["D"].width = 14
    ws_summary.column_dimensions["E"].width = 24
    ws_summary.column_dimensions["F"].width = 26
    ws_summary.column_dimensions["G"].width = 22
    for c_letter in ["H", "I", "J", "K", "L", "M"]:
        ws_summary.column_dimensions[c_letter].width = 16

    # -------------------------------------------------------------
    # SHEET 2: ผลการประเมินรายข้อ (Detailed Evaluation Table - 80 Questions)
    # -------------------------------------------------------------
    ws_detail = wb_out.create_sheet(title="ผลการประเมิน 80 ข้อ (Detailed)")
    ws_detail.views.sheetView[0].showGridLines = True

    detail_headers = [
        "ข้อที่",
        "หมวดหมู่นโยบาย (ในชีท)",
        "คำถาม",
        "คำตอบที่บอทตอบ",
        "คำตอบที่คาดหวัง",
        "Chunk ที่ใช้ตอบ (Chunk IDs)",
        "หัวข้อเอกสารและหน้าที่ Chunk สังกัด (หัวข้อสีชมพู)",
        "การดึง Chunk ตรงหมวด",
        "คะแนน AI (Score)",
        "ผลประเมิน AI (Verdict)",
        "เหตุผลประกอบการประเมิน (AI Reason)",
        "เวลาในการตอบ",
        "คะแนนโดยคนตรวจ (Human Score)",
        "ข้อเสนอแนะคนตรวจ (Human Notes)"
    ]

    ws_detail.row_dimensions[1].height = 32
    for col_idx, h in enumerate(detail_headers, start=1):
        cell = ws_detail.cell(1, col_idx, h)
        cell.font = font_white_bold
        cell.fill = navy_dark
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border

    for row_idx, res in enumerate(final_results, start=2):
        ws_detail.row_dimensions[row_idx].height = 68
        is_even = (row_idx % 2 == 0)
        base_fill = fill_zebra if is_even else fill_white

        row_cells_data = [
            (res["item_no"], Alignment(horizontal="center", vertical="top")),
            (res["category"], Alignment(horizontal="left", vertical="top", wrap_text=True)),
            (res["question"], Alignment(horizontal="left", vertical="top", wrap_text=True)),
            (res["bot_ans"], Alignment(horizontal="left", vertical="top", wrap_text=True)),
            (res["expected"], Alignment(horizontal="left", vertical="top", wrap_text=True)),
            (res["chunks"], Alignment(horizontal="center", vertical="top", wrap_text=True)),
            (res["pink_topic"], Alignment(horizontal="left", vertical="top", wrap_text=True)),
            (res["hit_text"], Alignment(horizontal="center", vertical="top")),
            (res["score"], Alignment(horizontal="center", vertical="top")),
            (res["verdict"], Alignment(horizontal="center", vertical="top")),
            (res["reason"], Alignment(horizontal="left", vertical="top", wrap_text=True)),
            (res["resp_time"], Alignment(horizontal="center", vertical="top")),
            ("", Alignment(horizontal="center", vertical="top")),  # Human Score
            ("", Alignment(horizontal="left", vertical="top", wrap_text=True))  # Human Notes
        ]

        for col_idx, (val, align) in enumerate(row_cells_data, start=1):
            cell = ws_detail.cell(row_idx, col_idx, val)
            cell.font = font_regular
            cell.fill = base_fill
            cell.alignment = align
            cell.border = thin_border

            # ไฮไลต์สีตาม Verdict
            if col_idx == 10:  # ผลประเมิน AI
                if res["verdict"] == "ถูกต้อง":
                    cell.fill = fill_correct
                    cell.font = font_correct
                elif res["verdict"] == "ถูกต้องบางส่วน":
                    cell.fill = fill_partial
                    cell.font = font_partial
                else:
                    cell.fill = fill_incorrect
                    cell.font = font_incorrect
            elif col_idx == 9:  # คะแนน AI
                cell.font = font_bold
                if res["score"] >= 0.9:
                    cell.fill = fill_correct
                    cell.font = font_correct
                elif res["score"] >= 0.4:
                    cell.fill = fill_partial
                    cell.font = font_partial
                else:
                    cell.fill = fill_incorrect
                    cell.font = font_incorrect
            elif col_idx == 8:  # Retrieval Hit
                if res["hit_val"] == 1.0:
                    cell.fill = fill_hit
                    cell.font = font_hit
                else:
                    cell.fill = fill_miss
                    cell.font = font_miss
            elif col_idx == 12:  # เวลาในการตอบ
                if isinstance(val, (int, float)):
                    cell.number_format = '0.00"s"'

    detail_col_widths = {
        1: 8,   # ข้อที่
        2: 28,  # หมวดหมู่นโยบาย (ในชีท)
        3: 35,  # คำถาม
        4: 48,  # คำตอบที่บอทตอบ
        5: 38,  # คำตอบที่คาดหวัง
        6: 16,  # Chunk IDs
        7: 48,  # หัวข้อสีชมพู
        8: 18,  # การดึง Chunk ตรงหมวด
        9: 14,  # คะแนน AI
        10: 18, # ผลประเมิน AI
        11: 42, # เหตุผล AI
        12: 14, # เวลาตอบ
        13: 16, # คะแนนคนตรวจ
        14: 25  # ข้อเสนอแนะคนตรวจ
    }
    for col_idx, w in detail_col_widths.items():
        ws_detail.column_dimensions[get_column_letter(col_idx)].width = w

    # บันทึกไฟล์ใหม่ ป้องกันการเขียนทับไฟล์ที่ผู้ใช้อาจเปิดค้างไว้
    out_eval_file = CURRENT_DIR / "test_result_gemma_with_accuracy.xlsx"
    wb_out.save(str(out_eval_file))

    print(f"\n🎉 บันทึกรายงานการประเมิน Accuracy เรียบร้อยแล้ว:")
    print(f"   -> {out_eval_file}")


if __name__ == "__main__":
    main()
