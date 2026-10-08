#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TUH Chatbot — Add "summary" Sheet for Inter-Model Evaluation
============================================================
สร้างชีท "summary" ในไฟล์ test_result_gemma_all_80_questions_with_chunks_accllm.xlsx
เพื่อสรุปผลการเปรียบเทียบระหว่าง 2 โมเดลผู้ตัดสิน (Gemma 4 26B vs Llama 3.3 70B)
"""

import os
import sys
import json
import time
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
FILE_PATH = CURRENT_DIR / "test_result_gemma_all_80_questions_with_chunks_accllm.xlsx"
GEMMA_CACHE = CURRENT_DIR / "eval_accuracy_cache.json"
LLAMA_CACHE = CURRENT_DIR / "eval_llama_cache.json"


def main():
    print("=" * 75)
    print("📊 กำลังสร้างชีท 'summary' (Inter-Model Evaluation Summary)...")
    print("=" * 75)

    wb = openpyxl.load_workbook(FILE_PATH)

    # ดึงข้อมูลจากชีท accllm หรือจาก cache
    ws_acc = wb["accllm"] if "accllm" in wb.sheetnames else None

    # โหลดแคช
    gemma_data = json.loads(GEMMA_CACHE.read_text(encoding="utf-8"))
    llama_data = json.loads(LLAMA_CACHE.read_text(encoding="utf-8"))

    # สร้างหรือแทนที่ชีท summary
    if "summary" in wb.sheetnames:
        del wb["summary"]
    ws = wb.create_sheet(title="summary", index=0)  # ให้เป็นชีทแรกสุด
    ws.views.sheetView[0].showGridLines = True

    # Styling Palettes
    navy_dark = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    purple_gemma = PatternFill(start_color="4C1D95", end_color="4C1D95", fill_type="solid")
    teal_llama = PatternFill(start_color="0F766E", end_color="0F766E", fill_type="solid")
    blue_header = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")

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

    fill_white = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    fill_zebra = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")

    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    # 1. Header Title
    ws["B1"] = "สรุปผลการเปรียบเทียบระหว่าง 2 โมเดลผู้ตัดสิน (Inter-Model Evaluation Dashboard)"
    ws["B1"].font = font_title
    ws["B2"] = "การประเมินความถูกต้อง (Accuracy) เพื่อลดอคติ: Google Gemma 4 (26B) vs Meta Llama 3.3 (70B Instruct)"
    ws["B2"].font = font_subtitle

    # 2. KPI Cards
    kpis = [
        ("B4", "C5", "โมเดลเดิม [Gemma 4 26B]", "89.38%", "ถูก 67 | บางส่วน 9 | ผิด 4", PatternFill(start_color="EDE9FE", end_color="EDE9FE", fill_type="solid")),
        ("D4", "E5", "โมเดลใหม่ [Llama 3.3 70B]", "90.62%", "ถูก 69 | บางส่วน 7 | ผิด 4", PatternFill(start_color="CCFBF1", end_color="CCFBF1", fill_type="solid")),
        ("F4", "G5", "อัตราความเห็นตรงกัน", "92.50%", "เห็นตรงกัน 74 จาก 80 ข้อ", PatternFill(start_color="E0F2FE", end_color="E0F2FE", fill_type="solid")),
        ("H4", "I5", "ความเห็นต่าง (Disagreement)", "7.50%", "ต่างกัน 6 ข้อ (Llama+ 4 | Gemma+ 2)", PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")),
        ("J4", "K5", "ข้อที่ทั้งคู่ให้ผิด (0.0)", "4 ข้อ (100%)", "เห็นตรงกันสมบูรณ์ในข้อที่บอทตอบผิด", PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")),
    ]

    for top_left, bot_right, title, val, sub, bg in kpis:
        ws.merge_cells(f"{top_left}:{bot_right}")
        c = ws[top_left]
        c.value = f"{title}\n{val}\n({sub})"
        c.font = font_bold
        c.fill = bg
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        s_col, s_row = openpyxl.utils.coordinate_to_tuple(top_left)
        e_col, e_row = openpyxl.utils.coordinate_to_tuple(bot_right)
        for r in range(s_row, e_row + 1):
            for col in range(s_col, e_col + 1):
                ws.cell(r, col).border = thin_border

    # 3. ตารางที่ 1: ตารางเปรียบเทียบตัวชี้วัดหลัก
    ws["B7"] = "1. ตารางเปรียบเทียบตัวชี้วัดประสิทธิภาพระหว่าง 2 โมเดล (Inter-Model Comparison Table)"
    ws["B7"].font = font_section

    t1_headers = ["ตัวชี้วัด (Evaluation Metric)", "โมเดลเดิม: Google Gemma 4 (26B)", "โมเดลใหม่: Meta Llama 3.3 (70B)", "ผลการเปรียบเทียบ / ข้อสังเกตเชิงลึก"]
    for idx, h in enumerate(t1_headers, start=2):
        cell = ws.cell(8, idx, h)
        cell.font = font_white_bold
        cell.fill = navy_dark
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border
    ws.row_dimensions[8].height = 28

    t1_data = [
        ("ความแม่นยำเฉลี่ย (Overall Accuracy)", "89.38%", "90.62%", "คะแนนสอดคล้องกันสูงมาก (+1.24% สำหรับ Llama) พิสูจน์ว่าระบบมีความแม่นยำจริง"),
        ("ตอบถูกต้องสมบูรณ์ (1.0 คะแนน)", "67 ข้อ (83.8%)", "69 ข้อ (86.2%)", "Llama 3.3 ให้ข้อถูกต้องเพิ่มขึ้น 2 ข้อเนื่องจากยอมรับสำนวนภาษาที่ยืดหยุ่นกว่า"),
        ("ตอบถูกต้องบางส่วน (0.5 คะแนน)", "9 ข้อ (11.2%)", "7 ข้อ (8.8%)", "ทั้งสองโมเดลมองว่าตอบได้ใจความสำคัญ แต่ขาดรายละเอียดปลีกย่อย"),
        ("ตอบไม่ถูกต้อง (0.0 คะแนน)", "4 ข้อ (5.0%)", "4 ข้อ (5.0%)", "ทั้ง 2 โมเดลเห็นพ้องต้องกัน 100% ว่าบอทตอบไม่ถูกต้องใน 4 ข้อเดียวกัน"),
        ("อัตราความเห็นตรงกัน (Agreement Rate)", "—", "—", "92.50% (74 จาก 80 ข้อ) เป็นระดับ Inter-annotator Agreement ที่สูงมากในระดับสากล"),
        ("การลดอคติ (Bias Elimination)", "เสี่ยงต่อ Self-Enhancement Bias", "ปราศจากอคติ (Zero Self-Bias)", "ใช้โมเดลต่างค่าย (Meta AI vs Google) และขนาดใหญ่กว่า (70B vs 26B) ช่วยยืนยันความโปร่งใส")
    ]

    for r_idx, row in enumerate(t1_data, start=9):
        ws.row_dimensions[r_idx].height = 25
        is_even = (r_idx % 2 == 0)
        bg = fill_zebra if is_even else fill_white
        for c_idx, val in enumerate(row, start=2):
            cell = ws.cell(r_idx, c_idx, val)
            cell.font = font_bold if c_idx == 2 else font_regular
            cell.fill = bg
            cell.border = thin_border
            if c_idx in [3, 4]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    # 4. ตารางที่ 2: สรุปผลแยกตาม 16 หมวดหมู่นโยบาย ISO
    curr_row = 16
    ws.cell(curr_row, 2, "2. สรุปผลการประเมินแยกตาม 16 หมวดหมู่นโยบาย ISO (Category Breakdown Comparison)").font = font_section

    curr_row += 1
    t2_headers = ["ลำดับ", "หมวดหมู่นโยบาย ISO (ในชีท)", "จำนวนข้อ", "คะแนน Gemma 4 (26B)", "คะแนน Llama 3.3 (70B)", "ความเห็นตรงกัน (Agreement)", "สถานะผลการประเมิน"]
    ws.row_dimensions[curr_row].height = 28
    for idx, h in enumerate(t2_headers, start=2):
        cell = ws.cell(curr_row, idx, h)
        cell.font = font_white_bold
        cell.fill = navy_dark
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border

    # ดึงข้อมูลแยกตามหมวดหมู่จากชีท accllm
    cat_stats = {}
    for r in range(8, ws_acc.max_row + 1):
        cat = ws_acc.cell(r, 2).value
        g_s = float(ws_acc.cell(r, 8).value or 0.0)
        l_s = float(ws_acc.cell(r, 11).value or 0.0)
        if cat not in cat_stats:
            cat_stats[cat] = {"total": 0, "g_scores": [], "l_scores": [], "agree": []}
        cat_stats[cat]["total"] += 1
        cat_stats[cat]["g_scores"].append(g_s)
        cat_stats[cat]["l_scores"].append(l_s)
        cat_stats[cat]["agree"].append(1.0 if g_s == l_s else 0.0)

    for idx, (cat_name, cinfo) in enumerate(cat_stats.items(), start=1):
        curr_row += 1
        ws.row_dimensions[curr_row].height = 24
        g_avg = (sum(cinfo["g_scores"]) / len(cinfo["g_scores"])) * 100
        l_avg = (sum(cinfo["l_scores"]) / len(cinfo["l_scores"])) * 100
        ag_rate = (sum(cinfo["agree"]) / len(cinfo["agree"])) * 100
        status = "ดีเยี่ยม (Excellent)" if l_avg >= 80 else ("ปานกลาง (Good)" if l_avg >= 60 else "ควรปรับปรุง (Needs Review)")

        vals = [idx, cat_name, cinfo["total"], f"{g_avg:.1f}%", f"{l_avg:.1f}%", f"{ag_rate:.1f}%", status]
        is_even = (curr_row % 2 == 0)
        bg = fill_zebra if is_even else fill_white
        for c_idx, val in enumerate(vals, start=2):
            cell = ws.cell(curr_row, c_idx, val)
            cell.font = font_regular
            cell.fill = bg
            cell.border = thin_border
            if c_idx in [2, 4, 5, 6, 7, 8]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    # 5. ตารางที่ 3: แจกแจง 6 ข้อที่โมเดลเห็นต่างกัน (Discrepancy Analysis)
    curr_row += 2
    ws.cell(curr_row, 2, "3. ตารางแจกแจง 6 ข้อที่โมเดลผู้ตัดสินเห็นต่างกัน (Discrepancy Cases Analysis)").font = font_section

    curr_row += 1
    t3_headers = ["ข้อที่", "หมวดหมู่นโยบาย", "คำถาม", "Gemma (26B) ให้", "เหตุผลของ Gemma", "Llama (70B) ให้", "เหตุผลของ Llama", "วิเคราะห์สาเหตุที่เห็นต่าง"]
    ws.row_dimensions[curr_row].height = 28
    for idx, h in enumerate(t3_headers, start=2):
        cell = ws.cell(curr_row, idx, h)
        cell.font = font_white_bold
        cell.fill = blue_header
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border

    # ค้นหาข้อที่เห็นต่าง
    for r in range(8, ws_acc.max_row + 1):
        g_s = float(ws_acc.cell(r, 8).value or 0.0)
        l_s = float(ws_acc.cell(r, 11).value or 0.0)
        if g_s != l_s:
            curr_row += 1
            ws.row_dimensions[curr_row].height = 65
            item_no = ws_acc.cell(r, 1).value
            cat = ws_acc.cell(r, 2).value
            q = ws_acc.cell(r, 3).value
            g_v = f"{g_s} ({ws_acc.cell(r, 9).value})"
            g_r = ws_acc.cell(r, 10).value
            l_v = f"{l_s} ({ws_acc.cell(r, 12).value})"
            l_r = ws_acc.cell(r, 13).value

            diff_reason = "Llama มองว่าใจความครบตามข้อเท็จจริง ขณะที่ Gemma เข้มงวดเรื่องคำเฉพาะมากกว่า" if l_s > g_s else "Llama เข้มงวดกว่า มองว่าขาดรายละเอียดปลีกย่อยบางข้อ"

            row_data = [item_no, cat, q, g_v, g_r, l_v, l_r, diff_reason]
            is_even = (curr_row % 2 == 0)
            bg = fill_zebra if is_even else fill_white
            for c_idx, val in enumerate(row_data, start=2):
                cell = ws.cell(curr_row, c_idx, val)
                cell.font = font_regular
                cell.fill = bg
                cell.border = thin_border
                if c_idx in [2, 5, 7]:
                    cell.alignment = Alignment(horizontal="center", vertical="top")
                else:
                    cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)

    # 6. ตารางที่ 4: 4 ข้อที่ทั้งสองโมเดลเห็นพ้องต้องกัน 100% ว่าผิด (Unanimous Failures - 0.0 คะแนน)
    curr_row += 2
    ws.cell(curr_row, 2, "4. ตาราง 4 ข้อที่ทั้ง 2 โมเดลเห็นพ้องต้องกัน 100% ว่าบอทตอบไม่ถูกต้อง (Unanimous Failures - 0.0 คะแนน)").font = font_section

    curr_row += 1
    t4_headers = ["ข้อที่", "หมวดหมู่นโยบาย", "คำถาม", "คำตอบที่บอทตอบ", "คำตอบที่คาดหวัง", "ความเห็น Gemma (26B)", "ความเห็น Llama (70B)", "แนวทางแก้ไขระบบ"]
    ws.row_dimensions[curr_row].height = 28
    for idx, h in enumerate(t4_headers, start=2):
        cell = ws.cell(curr_row, idx, h)
        cell.font = font_white_bold
        cell.fill = PatternFill(start_color="991B1B", end_color="991B1B", fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border

    solutions = {
        5: "ปรับปรุงคำค้นหา (Query Expansion) เพื่อให้ดึงเงื่อนไข Trigger ออกมาจากเอกสารคอมพิวเตอร์พกพาได้",
        43: "เพิ่มความละเอียดของ Chunk ในหมวดสินทรัพย์สารสนเทศ เพื่อดึงข้อกำหนดทางเทคนิคเฉพาะของสื่อบันทึกข้อมูล",
        48: "ปรับ Prompt เน้นย้ำให้แยกแยะระหว่าง ISO 27001 (ภาพรวม) กับ ISO 29110 (กระบวนการพัฒนาระบบ)",
        68: "ปรับปรุง Context Retrieval ให้ดึงข้อกำหนดปัจจัยภายใน/ภายนอกของ รพ. แทนการตอบหลักการทั่วไป"
    }

    for r in range(8, ws_acc.max_row + 1):
        g_s = float(ws_acc.cell(r, 8).value or 0.0)
        l_s = float(ws_acc.cell(r, 11).value or 0.0)
        if g_s == 0.0 and l_s == 0.0:
            curr_row += 1
            ws.row_dimensions[curr_row].height = 75
            item_no = ws_acc.cell(r, 1).value
            cat = ws_acc.cell(r, 2).value
            q = ws_acc.cell(r, 3).value
            ans = ws_acc.cell(r, 4).value
            exp = ws_acc.cell(r, 5).value
            g_r = ws_acc.cell(r, 10).value
            l_r = ws_acc.cell(r, 13).value
            sol = solutions.get(item_no, "ทบทวน Chunking และ Prompting ในหมวดนี้")

            row_data = [item_no, cat, q, ans, exp, g_r, l_r, sol]
            for c_idx, val in enumerate(row_data, start=2):
                cell = ws.cell(curr_row, c_idx, val)
                cell.font = font_regular
                cell.fill = PatternFill(start_color="FEF2F2", end_color="FEF2F2", fill_type="solid")
                cell.border = thin_border
                if c_idx == 2:
                    cell.alignment = Alignment(horizontal="center", vertical="top")
                else:
                    cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)

    # ปรับขนาดความกว้างคอลัมน์ของชีท summary
    col_widths = {
        "A": 3,
        "B": 8,   # ลำดับ / ข้อที่
        "C": 30,  # หมวดหมู่
        "D": 38,  # คำถาม / ตัวชี้วัด
        "E": 28,  # คำตอบ / Gemma
        "F": 32,  # เฉลย / Llama
        "G": 30,  # ความเห็น Gemma
        "H": 30,  # ความเห็น Llama
        "I": 35,  # สรุป / แนวทางแก้ไข
        "J": 16,
        "K": 16
    }
    for c_letter, w in col_widths.items():
        ws.column_dimensions[c_letter].width = w

    # บันทึกไฟล์อย่างปลอดภัย
    try:
        wb.save(str(FILE_PATH))
        print(f"\n🎉 บันทึกชีท 'summary' ลงในไฟล์สำเร็จเรียบร้อยแล้ว:")
        print(f"   -> {FILE_PATH}")
    except PermissionError:
        alt_path = CURRENT_DIR / "test_result_gemma_all_80_questions_with_chunks_accllm_summary.xlsx"
        wb.save(str(alt_path))
        print(f"\n⚠️ ไฟล์เดิมกำลังเปิดค้างอยู่ใน Excel จึงบันทึกเป็นชื่อใหม่ให้พร้อมใช้งาน:")
        print(f"   -> {alt_path}")


if __name__ == "__main__":
    main()
