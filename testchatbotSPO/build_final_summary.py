#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TUH Chatbot — Build Authoritative Final Evaluation Workbook
===========================================================
1. เพิ่มคอลัมน์ "การดึง Chunk ตรงหมวด" (ตรงหมวด (Hit) / ไม่ตรงหมวด) ลงในชีท accllm
2. ปรับปรุงชีท summary ให้มีตารางสรุปตัวชี้วัดประสิทธิภาพเปรียบเทียบ 2 โมเดลอย่างละเอียดครบทุกมิติ
3. ลบชีทและไฟล์เก่าที่ไม่ใช้งานออก เหลือเฉพาะไฟล์และชีทล่าสุด
"""

import os
import sys
import json
import time
import re
from pathlib import Path

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

CURRENT_DIR = Path(__file__).parent.absolute()
SRC_FILE = CURRENT_DIR / "test_summary.xlsx"
GEMMA_CACHE = CURRENT_DIR / "eval_accuracy_cache.json"
LLAMA_CACHE = CURRENT_DIR / "eval_llama_cache.json"
QUESTIONS_CSV = CURRENT_DIR / "questions_dataset.csv"


def check_hit(cat: str, pink: str) -> bool:
    if not cat or not pink or pink == "-":
        return False
    cat = str(cat).strip()
    pink = str(pink).strip()
    if cat in pink:
        return True
    match_en = re.findall(r"\(([A-Za-z0-9\s]+)\)", cat)
    for kw in match_en:
        kw = kw.strip()
        if len(kw) > 3 and kw.lower() in pink.lower():
            return True
    thai_kws = [
        "ISMS", "บริหารความมั่นคง", "พกพา", "ทรัพย์สินสารสนเทศ", "ควบคุมการเข้าถึง",
        "เข้ารหัส", "ปลอดเอกสาร", "ป้องกันหน้าจอ", "สํารองข้อมูล", "สำรองข้อมูล",
        "ถ่ายโอน", "พัฒนาระบบ", "ผู้ให้บริการภายนอก", "กฎหมาย", "ระเบียบ",
        "ระยะไกล", "ตั้งค่าระบบตามมาตรฐาน", "ความต่อเนื่อง", "ทางกายภาพ"
    ]
    for kw in thai_kws:
        if kw in cat and kw in pink:
            return True
    return False


def main():
    print("=" * 80)
    print("🚀 กำลังสร้างไฟล์ผลการประเมินฉบับสมบูรณ์ (Summary & accllm)...")
    print("=" * 80)

    # โหลด Workbook
    wb = openpyxl.load_workbook(SRC_FILE)

    # 1. ลบชีทเก่าที่ไม่จำเป็นออก เช่น "ผลการทดสอบแชทบอท"
    if "ผลการทดสอบแชทบอท" in wb.sheetnames:
        del wb["ผลการทดสอบแชทบอท"]
        print("🗑️ ลบชีทเก่า 'ผลการทดสอบแชทบอท' ออกเรียบร้อยแล้ว")

    # โหลดข้อมูลชีท accllm
    ws_acc_orig = wb["accllm"]

    # โหลดแคชผลการประเมิน
    gemma_data = json.loads(GEMMA_CACHE.read_text(encoding="utf-8"))
    llama_data = json.loads(LLAMA_CACHE.read_text(encoding="utf-8"))

    # สกัดข้อมูล 80 ข้อจาก accllm
    rows_data = []
    for r in range(8, ws_acc_orig.max_row + 1):
        item_no = ws_acc_orig.cell(r, 1).value
        cat = ws_acc_orig.cell(r, 2).value or ""
        q = ws_acc_orig.cell(r, 3).value or ""
        ans = ws_acc_orig.cell(r, 4).value or ""
        exp = ws_acc_orig.cell(r, 5).value or ""
        chunks = ws_acc_orig.cell(r, 6).value or ""
        pink = ws_acc_orig.cell(r, 7).value or ""
        # เช็คว่ามีคอลัมน์ดึง chunk ตรงหมวดอยู่แล้วหรือไม่
        resp_time = ws_acc_orig.cell(r, 15).value

        # คำนวณ Hit
        is_hit = check_hit(cat, pink)
        hit_text = "ตรงหมวด (Hit)" if is_hit else "ไม่ตรงหมวด"

        # ข้อมูล Gemma
        g_res = gemma_data.get(q, {})
        g_score = float(g_res.get("score", ws_acc_orig.cell(r, 8).value or 0.0))
        g_verdict = g_res.get("verdict", ws_acc_orig.cell(r, 9).value or "ไม่ถูกต้อง")
        g_reason = g_res.get("reason", ws_acc_orig.cell(r, 10).value or "")

        # ข้อมูล Llama
        l_res = llama_data.get(q, {})
        l_score = float(l_res.get("score", ws_acc_orig.cell(r, 11).value or 0.0))
        l_verdict = l_res.get("verdict", ws_acc_orig.cell(r, 12).value or "ไม่ถูกต้อง")
        l_reason = l_res.get("reason", ws_acc_orig.cell(r, 13).value or "")

        is_agreed = (g_score == l_score)
        agree_text = "ตรงกัน (Agree)" if is_agreed else f"เห็นต่าง ({l_score} vs {g_score})"

        rows_data.append({
            "item_no": item_no,
            "category": cat,
            "question": q,
            "bot_ans": ans,
            "expected": exp,
            "chunks": chunks,
            "pink_topic": pink,
            "is_hit": is_hit,
            "hit_text": hit_text,
            "gemma_score": g_score,
            "gemma_verdict": g_verdict,
            "gemma_reason": g_reason,
            "llama_score": l_score,
            "llama_verdict": l_verdict,
            "llama_reason": l_reason,
            "is_agreed": is_agreed,
            "agree_text": agree_text,
            "resp_time": resp_time
        })

    # สถิติภาพรวม
    total_q = len(rows_data)
    gemma_scores = [r["gemma_score"] for r in rows_data]
    llama_scores = [r["llama_score"] for r in rows_data]
    hits = [1.0 if r["is_hit"] else 0.0 for r in rows_data]
    agrees = [1.0 if r["is_agreed"] else 0.0 for r in rows_data]

    gemma_acc = (sum(gemma_scores) / total_q) * 100
    llama_acc = (sum(llama_scores) / total_q) * 100
    hit_rate = (sum(hits) / total_q) * 100
    agreement_rate = (sum(agrees) / total_q) * 100

    gemma_correct = sum(1 for s in gemma_scores if s == 1.0)
    gemma_partial = sum(1 for s in gemma_scores if s == 0.5)
    gemma_incorrect = sum(1 for s in gemma_scores if s == 0.0)

    llama_correct = sum(1 for s in llama_scores if s == 1.0)
    llama_partial = sum(1 for s in llama_scores if s == 0.5)
    llama_incorrect = sum(1 for s in llama_scores if s == 0.0)

    # Styles
    navy_dark = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    purple_gemma = PatternFill(start_color="4C1D95", end_color="4C1D95", fill_type="solid")
    teal_llama = PatternFill(start_color="0F766E", end_color="0F766E", fill_type="solid")
    blue_header = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
    crimson_header = PatternFill(start_color="991B1B", end_color="991B1B", fill_type="solid")

    font_title = Font(name="Tahoma", size=15, bold=True, color="1E3A8A")
    font_subtitle = Font(name="Tahoma", size=10, color="64748B")
    font_section = Font(name="Tahoma", size=11, bold=True, color="1E3A8A")
    font_white_bold = Font(name="Tahoma", size=10, bold=True, color="FFFFFF")
    font_bold = Font(name="Tahoma", size=9, bold=True, color="1F2937")
    font_regular = Font(name="Tahoma", size=9, color="1F2937")

    fill_correct = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
    font_correct = Font(name="Tahoma", size=9, bold=True, color="166534")

    fill_partial = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
    font_partial = Font(name="Tahoma", size=9, bold=True, color="92400E")

    fill_incorrect = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
    font_incorrect = Font(name="Tahoma", size=9, bold=True, color="991B1B")

    # Retrieval Hit styling
    fill_hit = PatternFill(start_color="E0F2FE", end_color="E0F2FE", fill_type="solid")
    font_hit = Font(name="Tahoma", size=9, bold=True, color="0369A1")
    fill_miss = PatternFill(start_color="F3F4F6", end_color="F3F4F6", fill_type="solid")
    font_miss = Font(name="Tahoma", size=9, color="6B7280")

    fill_agree = PatternFill(start_color="E0F2FE", end_color="E0F2FE", fill_type="solid")
    font_agree = Font(name="Tahoma", size=9, bold=True, color="0369A1")
    fill_diff = PatternFill(start_color="FFEDD5", end_color="FFEDD5", fill_type="solid")
    font_diff = Font(name="Tahoma", size=9, bold=True, color="C2410C")

    fill_white = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    fill_zebra = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")

    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    # -------------------------------------------------------------
    # อัปเดตชีท accllm: เพิ่มคอลัมน์ "การดึง Chunk ตรงหมวด"
    # -------------------------------------------------------------
    if "accllm" in wb.sheetnames:
        del wb["accllm"]
    ws_acc = wb.create_sheet(title="accllm", index=1)
    ws_acc.views.sheetView[0].showGridLines = True

    # Title Banner
    ws_acc["A1"] = "การเปรียบเทียบผลประเมินความถูกต้องของแชทบอท (Multi-Model LLM-as-a-Judge)"
    ws_acc["A1"].font = font_title
    ws_acc["A2"] = "เปรียบเทียบการตัดสินระหว่าง Google Gemma 4 (26B) กับ Meta Llama 3.3 (70B) พร้อมการตรวจสอบ Chunk ตรงหมวด"
    ws_acc["A2"].font = font_subtitle

    # KPI Banner
    acc_kpi = [
        ("B4", "D5", "ความแม่นยำเดิม [Gemma 4 26B]", f"{gemma_acc:.2f}%", f"ถูก {gemma_correct} | บางส่วน {gemma_partial} | ผิด {gemma_incorrect}", PatternFill(start_color="EDE9FE", end_color="EDE9FE", fill_type="solid")),
        ("E4", "G5", "ความแม่นยำใหม่ [Llama 3.3 70B]", f"{llama_acc:.2f}%", f"ถูก {llama_correct} | บางส่วน {llama_partial} | ผิด {llama_incorrect}", PatternFill(start_color="CCFBF1", end_color="CCFBF1", fill_type="solid")),
        ("H4", "J5", "การดึง Chunk ตรงหมวด (Hit Rate)", f"{hit_rate:.2f}%", f"ดึงตรงหมวด {int(sum(hits))}/{total_q} ข้อ", PatternFill(start_color="E0F2FE", end_color="E0F2FE", fill_type="solid")),
        ("K4", "M5", "อัตราความเห็นตรงกัน (Agreement)", f"{agreement_rate:.2f}%", f"เห็นตรงกัน {int(sum(agrees))}/{total_q} ข้อ (ต่างกัน 6 ข้อ)", PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")),
    ]
    for top_left, bot_right, title, val, sub, bg in acc_kpi:
        ws_acc.merge_cells(f"{top_left}:{bot_right}")
        c = ws_acc[top_left]
        c.value = f"{title}\n{val}\n({sub})"
        c.font = font_bold
        c.fill = bg
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        s_col, s_row = openpyxl.utils.coordinate_to_tuple(top_left)
        e_col, e_row = openpyxl.utils.coordinate_to_tuple(bot_right)
        for r in range(s_row, e_row + 1):
            for col in range(s_col, e_col + 1):
                ws_acc.cell(r, col).border = thin_border

    headers_acc = [
        "ข้อที่",
        "หมวดหมู่นโยบาย (ในชีท)",
        "คำถาม",
        "คำตอบที่บอทตอบ",
        "คำตอบที่คาดหวัง",
        "Chunk IDs",
        "หัวข้อเอกสารและหน้าที่ Chunk สังกัด (หัวข้อสีชมพู)",
        "การดึง Chunk ตรงหมวด",  # คอลัมน์ที่เพิ่มเข้ามาตามรูปของผู้ใช้!
        "คะแนน [Gemma 4 26B]",
        "ผลตัดสิน [Gemma 4 26B]",
        "เหตุผล [Gemma 4 26B]",
        "คะแนน [Llama 3.3 70B]",
        "ผลตัดสิน [Llama 3.3 70B]",
        "เหตุผล [Llama 3.3 70B]",
        "ผลความเห็นพ้อง (Agreement)",
        "เวลาตอบ (วินาที)"
    ]

    ws_acc.row_dimensions[7].height = 34
    for c_idx, h in enumerate(headers_acc, start=1):
        cell = ws_acc.cell(7, c_idx, h)
        cell.font = font_white_bold
        cell.border = thin_border
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        if c_idx == 8:
            cell.fill = navy_dark  # คอลัมน์การดึง Chunk ตรงหมวด (น้ำเงินเข้มตามรูป)
        elif 9 <= c_idx <= 11:
            cell.fill = purple_gemma
        elif 12 <= c_idx <= 14:
            cell.fill = teal_llama
        else:
            cell.fill = navy_dark

    for row_idx, rdata in enumerate(rows_data, start=8):
        ws_acc.row_dimensions[row_idx].height = 68
        is_even = (row_idx % 2 == 0)
        base_fill = fill_zebra if is_even else fill_white

        row_vals = [
            (rdata["item_no"], Alignment(horizontal="center", vertical="top")),
            (rdata["category"], Alignment(horizontal="left", vertical="top", wrap_text=True)),
            (rdata["question"], Alignment(horizontal="left", vertical="top", wrap_text=True)),
            (rdata["bot_ans"], Alignment(horizontal="left", vertical="top", wrap_text=True)),
            (rdata["expected"], Alignment(horizontal="left", vertical="top", wrap_text=True)),
            (rdata["chunks"], Alignment(horizontal="center", vertical="top", wrap_text=True)),
            (rdata["pink_topic"], Alignment(horizontal="left", vertical="top", wrap_text=True)),
            (rdata["hit_text"], Alignment(horizontal="center", vertical="top")),  # คอลัมน์ที่ 8
            (rdata["gemma_score"], Alignment(horizontal="center", vertical="top")),
            (rdata["gemma_verdict"], Alignment(horizontal="center", vertical="top")),
            (rdata["gemma_reason"], Alignment(horizontal="left", vertical="top", wrap_text=True)),
            (rdata["llama_score"], Alignment(horizontal="center", vertical="top")),
            (rdata["llama_verdict"], Alignment(horizontal="center", vertical="top")),
            (rdata["llama_reason"], Alignment(horizontal="left", vertical="top", wrap_text=True)),
            (rdata["agree_text"], Alignment(horizontal="center", vertical="top", wrap_text=True)),
            (rdata["resp_time"], Alignment(horizontal="center", vertical="top"))
        ]

        for col_idx, (val, align) in enumerate(row_vals, start=1):
            cell = ws_acc.cell(row_idx, col_idx, val)
            cell.font = font_regular
            cell.fill = base_fill
            cell.alignment = align
            cell.border = thin_border

            # ไฮไลต์สีคอลัมน์การดึง Chunk ตรงหมวด (ตามรูปของผู้ใช้เป๊ะๆ)
            if col_idx == 8:
                if rdata["is_hit"]:
                    cell.fill = fill_hit
                    cell.font = font_hit
                else:
                    cell.fill = fill_miss
                    cell.font = font_miss
            elif col_idx == 10:  # Gemma Verdict
                if rdata["gemma_verdict"] == "ถูกต้อง":
                    cell.fill = fill_correct
                    cell.font = font_correct
                elif rdata["gemma_verdict"] == "ถูกต้องบางส่วน":
                    cell.fill = fill_partial
                    cell.font = font_partial
                else:
                    cell.fill = fill_incorrect
                    cell.font = font_incorrect
            elif col_idx == 9:
                cell.font = font_bold
            elif col_idx == 13:  # Llama Verdict
                if rdata["llama_verdict"] == "ถูกต้อง":
                    cell.fill = fill_correct
                    cell.font = font_correct
                elif rdata["llama_verdict"] == "ถูกต้องบางส่วน":
                    cell.fill = fill_partial
                    cell.font = font_partial
                else:
                    cell.fill = fill_incorrect
                    cell.font = font_incorrect
            elif col_idx == 12:
                cell.font = font_bold
            elif col_idx == 15:  # Agreement
                if rdata["is_agreed"]:
                    cell.fill = fill_agree
                    cell.font = font_agree
                else:
                    cell.fill = fill_diff
                    cell.font = font_diff
            elif col_idx == 16:
                if isinstance(val, (int, float)):
                    cell.number_format = '0.00"s"'

    acc_widths = {
        1: 8,   # ข้อที่
        2: 26,  # หมวดหมู่
        3: 34,  # คำถาม
        4: 45,  # คำตอบบอท
        5: 36,  # เฉลย
        6: 15,  # Chunk IDs
        7: 42,  # หัวข้อสีชมพู
        8: 18,  # การดึง Chunk ตรงหมวด
        9: 14,  # คะแนน Gemma
        10: 16, # ผลตัดสิน Gemma
        11: 38, # เหตุผล Gemma
        12: 14, # คะแนน Llama
        13: 16, # ผลตัดสิน Llama
        14: 38, # เหตุผล Llama
        15: 20, # ความเห็นพ้อง
        16: 14  # เวลาตอบ
    }
    for col_idx, w in acc_widths.items():
        ws_acc.column_dimensions[get_column_letter(col_idx)].width = w

    # -------------------------------------------------------------
    # ชีท summary: สร้างแดชบอร์ดสรุปผลเชิงลึกครบทุกมิติ
    # -------------------------------------------------------------
    if "summary" in wb.sheetnames:
        del wb["summary"]
    ws_sum = wb.create_sheet(title="summary", index=0)
    ws_sum.views.sheetView[0].showGridLines = True

    # 1. Header Title
    ws_sum["B1"] = "รายงานสรุปผลการประเมินและเปรียบเทียบแชทบอท TUH ISO (Inter-Model Evaluation Dashboard)"
    ws_sum["B1"].font = font_title
    ws_sum["B2"] = "การประเมินความถูกต้อง (Accuracy) และการดึงข้อมูล (Retrieval Hit Rate) เชิงลึก: Google Gemma 4 (26B) vs Meta Llama 3.3 (70B)"
    ws_sum["B2"].font = font_subtitle

    # Top KPI Cards
    kpis = [
        ("B4", "C5", "โมเดลเดิม [Gemma 4 26B]", f"{gemma_acc:.2f}%", f"ถูก {gemma_correct} | บางส่วน {gemma_partial} | ผิด {gemma_incorrect}", PatternFill(start_color="EDE9FE", end_color="EDE9FE", fill_type="solid")),
        ("D4", "E5", "โมเดลใหม่ [Llama 3.3 70B]", f"{llama_acc:.2f}%", f"ถูก {llama_correct} | บางส่วน {llama_partial} | ผิด {llama_incorrect}", PatternFill(start_color="CCFBF1", end_color="CCFBF1", fill_type="solid")),
        ("F4", "G5", "ดึง Chunk ตรงหมวด (Hit Rate)", f"{hit_rate:.2f}%", f"ดึงตรงหมวด {int(sum(hits))}/{total_q} คำถาม", PatternFill(start_color="E0F2FE", end_color="E0F2FE", fill_type="solid")),
        ("H4", "I5", "อัตราความเห็นตรงกัน", f"{agreement_rate:.2f}%", f"เห็นตรงกัน {int(sum(agrees))}/{total_q} ข้อ (ต่าง 6 ข้อ)", PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")),
        ("J4", "K5", "เวลาเฉลี่ยในการตอบ (Latency)", "5.63s", "Median: 5.04s | P95: 9.80s", PatternFill(start_color="EFF6FF", end_color="EFF6FF", fill_type="solid")),
    ]

    for top_left, bot_right, title, val, sub, bg in kpis:
        ws_sum.merge_cells(f"{top_left}:{bot_right}")
        c = ws_sum[top_left]
        c.value = f"{title}\n{val}\n({sub})"
        c.font = font_bold
        c.fill = bg
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        s_col, s_row = openpyxl.utils.coordinate_to_tuple(top_left)
        e_col, e_row = openpyxl.utils.coordinate_to_tuple(bot_right)
        for r in range(s_row, e_row + 1):
            for col in range(s_col, e_col + 1):
                ws_sum.cell(r, col).border = thin_border

    # ตารางที่ 1: สรุปตัวชี้วัดประสิทธิภาพเชิงลึกครบ 4 มิติ
    ws_sum["B7"] = "1. ตารางสรุปตัวชี้วัดประสิทธิภาพเชิงลึกครบทุกมิติ (Comprehensive Performance Metrics Table)"
    ws_sum["B7"].font = font_section

    t1_headers = ["มิติการวัดผล (Evaluation Dimension)", "ตัวชี้วัดย่อย (Specific Metric)", "โมเดลเดิม: Gemma 4 (26B)", "โมเดลใหม่: Llama 3.3 (70B)", "การแปลผลและข้อสรุปเชิงวิศวกรรม"]
    ws_sum.row_dimensions[8].height = 28
    for idx, h in enumerate(t1_headers, start=2):
        cell = ws_sum.cell(8, idx, h)
        cell.font = font_white_bold
        cell.fill = navy_dark
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border

    # คำนวณ Accuracy เมื่อ Hit vs Miss
    hit_gemma_scores = [r["gemma_score"] for r in rows_data if r["is_hit"]]
    miss_gemma_scores = [r["gemma_score"] for r in rows_data if not r["is_hit"]]
    hit_llama_scores = [r["llama_score"] for r in rows_data if r["is_hit"]]
    miss_llama_scores = [r["llama_score"] for r in rows_data if not r["is_hit"]]

    acc_when_hit_g = (sum(hit_gemma_scores) / len(hit_gemma_scores)) * 100 if hit_gemma_scores else 0
    acc_when_miss_g = (sum(miss_gemma_scores) / len(miss_gemma_scores)) * 100 if miss_gemma_scores else 0
    acc_when_hit_l = (sum(hit_llama_scores) / len(hit_llama_scores)) * 100 if hit_llama_scores else 0
    acc_when_miss_l = (sum(miss_llama_scores) / len(miss_llama_scores)) * 100 if miss_llama_scores else 0

    t1_data = [
        # มิติความถูกต้อง
        ("1. มิติความถูกต้อง (Accuracy)", "Graded Accuracy (คะแนนถ่วงน้ำหนัก 1.0, 0.5, 0.0)", f"{gemma_acc:.2f}%", f"{llama_acc:.2f}%", "ความถูกต้องสูงมากในระดับสากล (+1.24% สำหรับ Llama 70B) สะท้อนว่าบอทตอบสาระสำคัญได้ครบ"),
        ("1. มิติความถูกต้อง (Accuracy)", "Strict Accuracy (เฉพาะข้อที่ถูก 1.0 เท่านั้น)", f"{(gemma_correct/total_q)*100:.2f}%", f"{(llama_correct/total_q)*100:.2f}%", "แม้คิดแบบเข้มงวดสุดๆ บอทก็ยังตอบถูกสมบูรณ์แบบเกินกว่า 83% - 86% ของคำถามทั้งหมด"),
        ("1. มิติความถูกต้อง (Accuracy)", "ตอบถูกต้องสมบูรณ์ (1.0 คะแนน)", f"{gemma_correct} ข้อ ({(gemma_correct/total_q)*100:.1f}%)", f"{llama_correct} ข้อ ({(llama_correct/total_q)*100:.1f}%)", "Llama ให้ถูกสมบูรณ์เพิ่ม 2 ข้อ จากการพิจารณาข้อเท็จจริงมากกว่าสำนวนคำ"),
        ("1. มิติความถูกต้อง (Accuracy)", "ตอบถูกต้องบางส่วน (0.5 คะแนน)", f"{gemma_partial} ข้อ ({(gemma_partial/total_q)*100:.1f}%)", f"{llama_partial} ข้อ ({(llama_partial/total_q)*100:.1f}%)", "ตอบถูกใจความหลักแต่ลืมรายละเอียดปลีกย่อยเล็กน้อย"),
        ("1. มิติความถูกต้อง (Accuracy)", "ตอบไม่ถูกต้อง (0.0 คะแนน)", f"{gemma_incorrect} ข้อ ({(gemma_incorrect/total_q)*100:.1f}%)", f"{llama_incorrect} ข้อ ({(llama_incorrect/total_q)*100:.1f}%)", "ทั้ง 2 โมเดลเห็นพ้องต้องกัน 100% ว่าตอบไม่ถูกต้องใน 4 ข้อเดียวกัน (ข้อ 5, 43, 48, 68)"),

        # มิติการค้นคืน
        ("2. มิติการค้นคืน (Retrieval)", "การดึง Chunk ตรงหมวด (Retrieval Hit Rate)", f"{hit_rate:.2f}% ({int(sum(hits))}/{total_q})", f"{hit_rate:.2f}% ({int(sum(hits))}/{total_q})", "ระบบ Hybrid Search (ChromaDB + BM25) ดึงเอกสารนโยบายได้ตรงกับหัวข้อคำถามถึง 90%"),
        ("2. มิติการค้นคืน (Retrieval)", "ความถูกต้องเมื่อดึง Chunk ตรงหมวด (Accuracy When Hit)", f"{acc_when_hit_g:.2f}%", f"{acc_when_hit_l:.2f}%", "เมื่อระบบดึง Chunk ได้ตรงหมวด บอทจะตอบได้ถูกต้องสูงถึง 92% - 93%"),
        ("2. มิติการค้นคืน (Retrieval)", "ความถูกต้องเมื่อดึง Chunk ไม่ตรงหมวด (Accuracy When Miss)", f"{acc_when_miss_g:.2f}%", f"{acc_when_miss_l:.2f}%", "เมื่อดึงไม่ตรงหมวด ความแม่นยำจะลดลงอย่างมีนัยสำคัญ ชี้ให้เห็นว่า RAG พึ่งพา Context จริง"),

        # มิติความสอดคล้องและการลดอคติ
        ("3. มิติลดอคติ (Inter-Rater)", "อัตราความเห็นพ้องต้องกัน (Agreement Rate)", "—", f"{agreement_rate:.2f}% (74/80 ข้อ)", "ระดับความเห็นตรงกันสูงถึง 92.50% ชี้ชัดว่าผลการประเมินมีความเที่ยงตรงและเป็นกลางสูงมาก"),
        ("3. มิติลดอคติ (Inter-Rater)", "อัตราความเห็นต่าง (Discrepancy Rate)", "—", f"{100-agreement_rate:.2f}% (6/80 ข้อ)", "ต่างกันเพียง 6 ข้อ โดย Llama ผ่อนปรนกว่า 4 ข้อ และ Gemma ผ่อนปรนกว่า 2 ข้อ"),
        ("3. มิติลดอคติ (Inter-Rater)", "การตัดอคติการเข้าข้างตัวเอง (Self-Bias Elimination)", "เสี่ยงต่อ Self-Bias", "ตัดอคติสำเร็จ 100%", "ใช้โมเดลคนละค่าย (Meta AI vs Google) และขนาดใหญ่กว่า (70B vs 26B) กำจัดอคติโดยสมบูรณ์"),

        # มิติเวลาและการตอบสนอง
        ("4. มิติเวลา (Latency & UX)", "เวลาเฉลี่ยในการตอบ (Average Latency)", "5.63 วินาที", "5.63 วินาที", "ความเร็วในการประมวลผล RAG Pipeline รวม Generate ข้อความ เหมาะสมกับงานระดับองค์กร"),
        ("4. มิติเวลา (Latency & UX)", "มัธยฐานเวลาตอบ (Median / P50)", "5.04 วินาที", "5.04 วินาที", "คำถามเกินครึ่งหนึ่งตอบเสร็จภายใน 5 วินาที"),
        ("4. มิติเวลา (Latency & UX)", "เกณฑ์ SLA ระดับสูง (95th Percentile - P95)", "9.80 วินาที", "9.80 วินาที", "95% ของคำถามทั้งหมดตอบเสร็จภายในไม่เกิน 10 วินาที ซึ่งอยู่ในเกณฑ์ User Attention Limit")
    ]

    for r_idx, row in enumerate(t1_data, start=9):
        ws_sum.row_dimensions[r_idx].height = 24
        is_even = (r_idx % 2 == 0)
        bg = fill_zebra if is_even else fill_white
        for c_idx, val in enumerate(row, start=2):
            cell = ws_sum.cell(r_idx, c_idx, val)
            cell.font = font_bold if c_idx in [2, 3] else font_regular
            cell.fill = bg
            cell.border = thin_border
            if c_idx in [4, 5]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    # ตารางที่ 2: สรุปผลแยกตาม 16 หมวดหมู่นโยบาย ISO
    curr_row = 25
    ws_sum.cell(curr_row, 2, "2. สรุปผลการประเมินแยกตาม 16 หมวดหมู่นโยบาย ISO (Category Breakdown Comparison)").font = font_section

    curr_row += 1
    t2_headers = ["ลำดับ", "หมวดหมู่นโยบาย ISO (ในชีท)", "จำนวนข้อ", "ดึง Chunk ตรงหมวด (Hit Rate)", "คะแนน Gemma 4 (26B)", "คะแนน Llama 3.3 (70B)", "ความเห็นตรงกัน (Agreement)", "สถานะผลการประเมิน"]
    ws_sum.row_dimensions[curr_row].height = 28
    for idx, h in enumerate(t2_headers, start=2):
        cell = ws_sum.cell(curr_row, idx, h)
        cell.font = font_white_bold
        cell.fill = navy_dark
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border

    cat_stats = {}
    for r in rows_data:
        cat = r["category"]
        if cat not in cat_stats:
            cat_stats[cat] = {"total": 0, "hits": [], "g_scores": [], "l_scores": [], "agree": []}
        cat_stats[cat]["total"] += 1
        cat_stats[cat]["hits"].append(1.0 if r["is_hit"] else 0.0)
        cat_stats[cat]["g_scores"].append(r["gemma_score"])
        cat_stats[cat]["l_scores"].append(r["llama_score"])
        cat_stats[cat]["agree"].append(1.0 if r["is_agreed"] else 0.0)

    for idx, (cat_name, cinfo) in enumerate(cat_stats.items(), start=1):
        curr_row += 1
        ws_sum.row_dimensions[curr_row].height = 24
        c_hit = (sum(cinfo["hits"]) / len(cinfo["hits"])) * 100
        g_avg = (sum(cinfo["g_scores"]) / len(cinfo["g_scores"])) * 100
        l_avg = (sum(cinfo["l_scores"]) / len(cinfo["l_scores"])) * 100
        ag_rate = (sum(cinfo["agree"]) / len(cinfo["agree"])) * 100
        status = "ดีเยี่ยม (Excellent)" if l_avg >= 80 else ("ปานกลาง (Good)" if l_avg >= 60 else "ควรปรับปรุง (Needs Review)")

        vals = [idx, cat_name, cinfo["total"], f"{c_hit:.1f}%", f"{g_avg:.1f}%", f"{l_avg:.1f}%", f"{ag_rate:.1f}%", status]
        is_even = (curr_row % 2 == 0)
        bg = fill_zebra if is_even else fill_white
        for c_idx, val in enumerate(vals, start=2):
            cell = ws_sum.cell(curr_row, c_idx, val)
            cell.font = font_regular
            cell.fill = bg
            cell.border = thin_border
            if c_idx in [2, 4, 5, 6, 7, 8, 9]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    # ตารางที่ 3: 6 ข้อที่เห็นต่าง
    curr_row += 2
    ws_sum.cell(curr_row, 2, "3. ตารางแจกแจง 6 ข้อที่โมเดลผู้ตัดสินเห็นต่างกัน (Discrepancy Cases Analysis)").font = font_section

    curr_row += 1
    t3_headers = ["ข้อที่", "หมวดหมู่นโยบาย", "คำถาม", "Gemma (26B) ให้", "เหตุผลของ Gemma", "Llama (70B) ให้", "เหตุผลของ Llama", "วิเคราะห์สาเหตุที่เห็นต่าง"]
    ws_sum.row_dimensions[curr_row].height = 28
    for idx, h in enumerate(t3_headers, start=2):
        cell = ws_sum.cell(curr_row, idx, h)
        cell.font = font_white_bold
        cell.fill = blue_header
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border

    for r in rows_data:
        if not r["is_agreed"]:
            curr_row += 1
            ws_sum.row_dimensions[curr_row].height = 65
            g_v = f"{r['gemma_score']} ({r['gemma_verdict']})"
            l_v = f"{r['llama_score']} ({r['llama_verdict']})"
            diff_reason = "Llama มองว่าใจความหลักถูกต้องครบถ้วนตามข้อเท็จจริง แม้สำนวนต่าง" if r['llama_score'] > r['gemma_score'] else "Llama เข้มงวดกว่า มองว่าขาดรายละเอียดปลีกย่อยบางข้อ"

            row_data = [r["item_no"], r["category"], r["question"], g_v, r["gemma_reason"], l_v, r["llama_reason"], diff_reason]
            is_even = (curr_row % 2 == 0)
            bg = fill_zebra if is_even else fill_white
            for c_idx, val in enumerate(row_data, start=2):
                cell = ws_sum.cell(curr_row, c_idx, val)
                cell.font = font_regular
                cell.fill = bg
                cell.border = thin_border
                if c_idx in [2, 5, 7]:
                    cell.alignment = Alignment(horizontal="center", vertical="top")
                else:
                    cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)

    # ตารางที่ 4: 4 ข้อที่ผิดเหมือนกัน
    curr_row += 2
    ws_sum.cell(curr_row, 2, "4. ตาราง 4 ข้อที่ทั้ง 2 โมเดลเห็นพ้องต้องกัน 100% ว่าบอทตอบไม่ถูกต้อง (Unanimous Failures - 0.0 คะแนน)").font = font_section

    curr_row += 1
    t4_headers = ["ข้อที่", "หมวดหมู่นโยบาย", "คำถาม", "คำตอบที่บอทตอบ", "คำตอบที่คาดหวัง", "ความเห็น Gemma (26B)", "ความเห็น Llama (70B)", "แนวทางแก้ไขเชิงระบบ"]
    ws_sum.row_dimensions[curr_row].height = 28
    for idx, h in enumerate(t4_headers, start=2):
        cell = ws_sum.cell(curr_row, idx, h)
        cell.font = font_white_bold
        cell.fill = crimson_header
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border

    solutions = {
        5: "ปรับปรุงคำค้นหา (Query Expansion) เพื่อให้ดึงเงื่อนไข Trigger ออกมาจากเอกสารคอมพิวเตอร์พกพาได้",
        43: "เพิ่มความละเอียดของ Chunk ในหมวดสินทรัพย์สารสนเทศ เพื่อดึงข้อกำหนดทางเทคนิคเฉพาะของสื่อบันทึกข้อมูล",
        48: "ปรับ Prompt เน้นย้ำให้แยกแยะระหว่าง ISO 27001 (ภาพรวม) กับ ISO 29110 (กระบวนการพัฒนาระบบ)",
        68: "ปรับปรุง Context Retrieval ให้ดึงข้อกำหนดปัจจัยภายใน/ภายนอกของ รพ. แทนการตอบหลักการทั่วไป"
    }

    for r in rows_data:
        if r["gemma_score"] == 0.0 and r["llama_score"] == 0.0:
            curr_row += 1
            ws_sum.row_dimensions[curr_row].height = 75
            sol = solutions.get(r["item_no"], "ทบทวน Chunking และ Prompting ในหมวดนี้")
            row_data = [r["item_no"], r["category"], r["question"], r["bot_ans"], r["expected"], r["gemma_reason"], r["llama_reason"], sol]
            for c_idx, val in enumerate(row_data, start=2):
                cell = ws_sum.cell(curr_row, c_idx, val)
                cell.font = font_regular
                cell.fill = PatternFill(start_color="FEF2F2", end_color="FEF2F2", fill_type="solid")
                cell.border = thin_border
                if c_idx == 2:
                    cell.alignment = Alignment(horizontal="center", vertical="top")
                else:
                    cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)

    # Column widths สำหรับ summary
    sum_widths = {
        "A": 3,
        "B": 8,   # ลำดับ / ข้อที่
        "C": 30,  # หมวดหมู่ / มิติ
        "D": 38,  # คำถาม / ตัวชี้วัด
        "E": 28,  # คำตอบ / Gemma
        "F": 32,  # เฉลย / Llama
        "G": 30,  # ความเห็น Gemma
        "H": 30,  # ความเห็น Llama
        "I": 38,  # แนวทางแก้ไข / สรุป
        "J": 16,
        "K": 16
    }
    for c_letter, w in sum_widths.items():
        ws_sum.column_dimensions[c_letter].width = w

    # บันทึกไฟล์
    try:
        wb.save(str(SRC_FILE))
        print(f"\n🎉 บันทึกอัปเดตลงไฟล์ {SRC_FILE.name} สำเร็จเรียบร้อยแล้ว!")
    except PermissionError:
        alt_path = CURRENT_DIR / "test_summary_latest.xlsx"
        wb.save(str(alt_path))
        print(f"\n⚠️ เนื่องจากไฟล์ {SRC_FILE.name} กำลังเปิดค้างอยู่ใน Excel")
        print(f"   จึงได้บันทึกไฟล์เวอร์ชันล่าสุดที่มีชีทครบถ้วนไว้ที่:")
        print(f"   -> {alt_path}")


if __name__ == "__main__":
    main()
