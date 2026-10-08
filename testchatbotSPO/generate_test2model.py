#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TUH Chatbot — Generate test2Model.xlsx
======================================
1. โหลดข้อมูลการทดสอบทั้ง 80 ข้อจาก test_PF.xlsx (ซึ่งมีคำตอบจริงจาก Gemma 4 26B และ Llama 3.3 70B)
2. ประเมินคำตอบของทั้ง 2 โมเดลโดยใช้โมเดล "anthropic/claude-3-haiku" เป็นกรรมการกลาง (LLM-as-a-Judge)
3. สร้างไฟล์ผลลัพธ์ใหม่ "test2Model.xlsx" โดยไม่แก้ไขไฟล์เดิม
"""

import os
import sys
import json
import time
import re
from pathlib import Path
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent

load_dotenv(PROJECT_ROOT / "Backend" / ".env")
load_dotenv(PROJECT_ROOT / ".env")

OPENROUTER_API_KEY = (os.getenv("OPENROUTER_API_KEY") or "").split()[0]
JUDGE_MODEL = "anthropic/claude-3-haiku"
SRC_EXCEL = CURRENT_DIR / "test_PF.xlsx"
OUT_EXCEL = CURRENT_DIR / "test2Model.xlsx"
CACHE_FILE = CURRENT_DIR / "eval_claude_3_haiku_cache.json"


def load_test_data() -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """โหลดข้อมูล 80 ข้อของ Gemma และ Llama จาก test_PF.xlsx"""
    if not SRC_EXCEL.exists():
        raise FileNotFoundError(f"ไม่พบไฟล์ต้นฉบับ: {SRC_EXCEL}")

    wb = openpyxl.load_workbook(SRC_EXCEL, data_only=True)
    ws_gemma = wb["Gemma 4 26B"]
    ws_llama = wb["Llama 3.3 70B"]

    gemma_items = []
    llama_items = []

    def parse_sheet(ws):
        items = []
        for r in range(6, ws.max_row + 1):
            orig_no = ws.cell(r, 1).value
            run_no = ws.cell(r, 2).value
            category = ws.cell(r, 3).value or ""
            question = ws.cell(r, 4).value or ""
            bot_answer = ws.cell(r, 5).value or ""
            expected_answer = ws.cell(r, 6).value or ""
            raw_time = ws.cell(r, 7).value
            
            # แปลงเวลาเป็น float
            resp_time = 0.0
            if isinstance(raw_time, (int, float)):
                resp_time = float(raw_time)
            elif isinstance(raw_time, str):
                match = re.search(r"([\d\.]+)", raw_time)
                if match:
                    resp_time = float(match.group(1))

            chunk_ids = ws.cell(r, 8).value or ""
            doc_info = ws.cell(r, 9).value or ""
            hit_text = str(ws.cell(r, 10).value or "")
            is_hit = ("ตรงหมวด" in hit_text)

            items.append({
                "orig_no": orig_no,
                "run_no": run_no,
                "category": category,
                "question": question,
                "bot_answer": bot_answer,
                "expected_answer": expected_answer,
                "response_time": resp_time,
                "chunk_ids": chunk_ids,
                "doc_info": doc_info,
                "hit_text": hit_text,
                "is_hit": is_hit
            })
        return items

    gemma_items = parse_sheet(ws_gemma)
    llama_items = parse_sheet(ws_llama)
    return gemma_items, llama_items


def judge_answer_claude(
    question: str,
    expected: str,
    actual: str,
    cache: dict,
    model_tag: str = ""
) -> Dict[str, Any]:
    """เรียก Claude 3 Haiku เพื่อตรวจคำตอบและให้คะแนน"""
    cache_key = f"{question.strip()} ||| {expected.strip()} ||| {actual.strip()}"
    if cache_key in cache:
        return cache[cache_key]

    if not actual or actual.strip() in ["-", ""] or "API Error" in actual or "Connection Error" in actual:
        res = {
            "score": 0.0,
            "verdict": "ไม่ถูกต้อง",
            "reason": "ระบบไม่สามารถตอบข้อความได้ หรือเกิดข้อผิดพลาดในการเชื่อมต่อ"
        }
        cache[cache_key] = res
        return res

    act_norm = re.sub(r"\s+", " ", actual.strip())
    exp_norm = re.sub(r"\s+", " ", expected.strip())
    if act_norm == exp_norm:
        res = {
            "score": 1.0,
            "verdict": "ถูกต้อง",
            "reason": "คำตอบตรงกับคำตอบที่คาดหวังอย่างสมบูรณ์แบบ"
        }
        cache[cache_key] = res
        return res

    prompt = f"""คุณคือผู้ประเมินคุณภาพของระบบ AI Chatbot (LLM-as-a-Judge) สำหรับเอกสารมาตรฐาน ISO โรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ
หน้าที่ของคุณคือตัดสินคะแนนความถูกต้องของคำตอบจาก Chatbot เปรียบเทียบกับคำตอบที่คาดหวัง (Expected Answer) อย่างเป็นกลางและเข้มงวด

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

กรุณาตอบผลการประเมินเป็น JSON Format ดังนี้เท่านั้น (ห้ามใส่ markdown fence หรือคำเกริ่นนำ):
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
        "X-Title": "TUH Chatbot Evaluation Judge"
    }
    payload = {
        "model": JUDGE_MODEL,
        "messages": [
            {"role": "system", "content": "You are a precise, objective Thai QA evaluation judge. Output only raw JSON."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.0,
        "max_tokens": 300
    }

    for attempt in range(4):
        try:
            r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=35)
            if r.status_code == 200:
                raw_text = r.json()["choices"][0]["message"]["content"].strip()
                if raw_text.startswith("```"):
                    raw_text = re.sub(r"^```(?:json)?\n?", "", raw_text)
                    raw_text = re.sub(r"\n?```$", "", raw_text)
                parsed = json.loads(raw_text)
                score = float(parsed.get("score", 0.0))
                verdict = parsed.get("verdict", "ถูกต้อง" if score >= 1.0 else ("ถูกต้องบางส่วน" if score >= 0.5 else "ไม่ถูกต้อง"))
                res = {
                    "score": score,
                    "verdict": verdict,
                    "reason": parsed.get("reason", "").strip()
                }
                cache[cache_key] = res
                return res
            elif r.status_code == 429:
                time.sleep(3.5)
            else:
                time.sleep(2.0)
        except Exception:
            time.sleep(2.0)

    # Fallback
    res = {
        "score": 0.0,
        "verdict": "ไม่ถูกต้อง",
        "reason": "ไม่สามารถเรียกโมเดลกรรมการ Claude 3 Haiku เพื่อประเมินได้"
    }
    cache[cache_key] = res
    return res


def evaluate_all(gemma_items, llama_items):
    """รันการประเมินคำตอบทั้งหมดด้วย Claude 3 Haiku แบบคู่ขนาน"""
    cache = {}
    if CACHE_FILE.exists():
        try:
            cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            print(f"📦 โหลดแคชเดิมสำเร็จ: {len(cache)} รายการ")
        except Exception:
            cache = {}

    tasks = []
    for r in gemma_items:
        tasks.append(("gemma", r))
    for r in llama_items:
        tasks.append(("llama", r))

    print(f"🚀 เริ่มการประเมินด้วย Claude 3 Haiku ทั้งหมด {len(tasks)} รายการ (Concurrency: 5)...")

    def _worker(item_task):
        mtype, r = item_task
        res = judge_answer_claude(r["question"], r["expected_answer"], r["bot_answer"], cache, mtype)
        r["score"] = res["score"]
        r["verdict"] = res["verdict"]
        r["reason"] = res["reason"]
        return mtype, r["orig_no"], res["score"], res["verdict"]

    completed = 0
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(_worker, t) for t in tasks]
        for fut in as_completed(futures):
            mtype, orig_no, sc, vd = fut.result()
            completed += 1
            if completed % 10 == 0 or completed == len(tasks):
                print(f"   [{completed}/{len(tasks)}] {mtype.upper()} ข้อ {orig_no} -> {sc} ({vd})")

    # บันทึกแคช
    try:
        CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"💾 บันทึกแคชผลประเมินเรียบร้อย: {len(cache)} รายการ")
    except Exception as e:
        print(f"⚠️ ไม่สามารถบันทึกแคชได้: {e}")


def build_test2model_excel(gemma_items, llama_items):
    """สร้างไฟล์ Excel: test2Model.xlsx ตามโครงสร้างที่อ่านง่ายและสวยงาม"""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    # สีและสไตล์
    navy_dark = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    purple_gemma = PatternFill(start_color="581C87", end_color="581C87", fill_type="solid")
    teal_llama = PatternFill(start_color="0F766E", end_color="0F766E", fill_type="solid")
    coral_claude = PatternFill(start_color="C2410C", end_color="C2410C", fill_type="solid")
    blue_primary = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
    gray_bg = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    zebra_bg = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")

    fill_correct = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
    font_correct = Font(name="Tahoma", size=9, bold=True, color="166534")

    fill_partial = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
    font_partial = Font(name="Tahoma", size=9, bold=True, color="92400E")

    fill_incorrect = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
    font_incorrect = Font(name="Tahoma", size=9, bold=True, color="991B1B")

    fill_hit = PatternFill(start_color="E0F2FE", end_color="E0F2FE", fill_type="solid")
    font_hit = Font(name="Tahoma", size=9, bold=True, color="0369A1")

    fill_miss = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
    font_miss = Font(name="Tahoma", size=9, color="64748B")

    font_title = Font(name="Tahoma", size=15, bold=True, color="1E3A8A")
    font_subtitle = Font(name="Tahoma", size=10, color="475569")
    font_section = Font(name="Tahoma", size=11, bold=True, color="1E3A8A")
    font_white_bold = Font(name="Tahoma", size=9, bold=True, color="FFFFFF")
    font_bold = Font(name="Tahoma", size=9, bold=True, color="1E293B")
    font_regular = Font(name="Tahoma", size=9, color="1E293B")

    thin_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1")
    )
    card_border = Border(
        left=Side(style="medium", color="94A3B8"),
        right=Side(style="medium", color="94A3B8"),
        top=Side(style="medium", color="94A3B8"),
        bottom=Side(style="medium", color="94A3B8")
    )

    total_q = len(gemma_items)
    g_scores = [r["score"] for r in gemma_items]
    l_scores = [r["score"] for r in llama_items]
    g_times = [r["response_time"] for r in gemma_items]
    l_times = [r["response_time"] for r in llama_items]
    hits = [1 if r["is_hit"] else 0 for r in gemma_items]

    g_acc = (sum(g_scores) / total_q) * 100 if total_q else 0
    l_acc = (sum(l_scores) / total_q) * 100 if total_q else 0
    hit_rate = (sum(hits) / total_q) * 100 if total_q else 0

    g_strict = (sum(1 for s in g_scores if s == 1.0) / total_q) * 100 if total_q else 0
    l_strict = (sum(1 for s in l_scores if s == 1.0) / total_q) * 100 if total_q else 0

    g_avg_time = sum(g_times) / total_q if total_q else 0
    l_avg_time = sum(l_times) / total_q if total_q else 0

    # ══════════════════════════════════════════════════════════════════════════════
    # SHEET 1: Summary
    # ══════════════════════════════════════════════════════════════════════════════
    ws_sum = wb.create_sheet(title="Summary")
    ws_sum.views.sheetView[0].showGridLines = True

    ws_sum.cell(2, 2, "รายงานสรุปผลการทดสอบระบบ AI Chatbot TUH ISO — เปรียบเทียบ 2 โมเดล").font = font_title
    ws_sum.cell(3, 2, "สมองแชทบอท: Google Gemma 4 26B vs Meta Llama 3.3 70B | กรรมการตัดสิน: Anthropic Claude 3 Haiku").font = font_subtitle
    ws_sum.cell(4, 2, f"ทดสอบทั้งหมด {total_q} ข้อ (ชุดข้อมูลจริง) | วันที่จัดทำ: {time.strftime('%d/%m/%Y %H:%M:%S')}").font = Font(name="Tahoma", size=9, italic=True, color="64748B")

    # 4 KPI Cards
    cards = [
        ("Gemma 4 (26B) คะแนนเฉลี่ย", f"{g_acc:.1f}%", f"ถูกสมบูรณ์ {g_strict:.1f}% (ตรวจโดย Claude 3 Haiku)", purple_gemma),
        ("Llama 3.3 (70B) คะแนนเฉลี่ย", f"{l_acc:.1f}%", f"ถูกสมบูรณ์ {l_strict:.1f}% (ตรวจโดย Claude 3 Haiku)", teal_llama),
        ("การดึง Chunk ตรงหมวด (Hit Rate)", f"{hit_rate:.1f}%", f"ดึงตรง {sum(hits)}/{total_q} ข้อ", navy_dark),
        ("เวลาเฉลี่ย Gemma vs Llama", f"{g_avg_time:.2f}s | {l_avg_time:.2f}s", "เวลาตอบสนองจริงของแชทบอท", blue_primary)
    ]

    for i, (title, val, sub, fill) in enumerate(cards):
        col_start = 2 + (i * 2)
        ws_sum.merge_cells(start_row=6, start_column=col_start, end_row=6, end_column=col_start + 1)
        ws_sum.merge_cells(start_row=7, start_column=col_start, end_row=7, end_column=col_start + 1)
        ws_sum.merge_cells(start_row=8, start_column=col_start, end_row=8, end_column=col_start + 1)

        c_title = ws_sum.cell(6, col_start, title)
        c_title.fill = fill
        c_title.font = font_white_bold
        c_title.alignment = Alignment(horizontal="center", vertical="center")

        c_val = ws_sum.cell(7, col_start, val)
        c_val.font = Font(name="Tahoma", size=14, bold=True, color="1E3A8A")
        c_val.alignment = Alignment(horizontal="center", vertical="center")
        c_val.fill = gray_bg

        c_sub = ws_sum.cell(8, col_start, sub)
        c_sub.font = Font(name="Tahoma", size=8, color="64748B")
        c_sub.alignment = Alignment(horizontal="center", vertical="center")
        c_sub.fill = gray_bg

        for r in range(6, 9):
            for c in range(col_start, col_start + 2):
                ws_sum.cell(r, c).border = card_border

    # ตารางที่ 1: KPI
    ws_sum.cell(10, 2, "1. ตารางเปรียบเทียบตัวชี้วัดประสิทธิภาพเชิงลึก (ประเมินโดย Claude 3 Haiku)").font = font_section
    kpi_headers = [
        "มิติการวัดผล (Dimension)",
        "ตัวชี้วัดย่อย (Metric)",
        "สมองที่ 1: Google Gemma 4 (26B)",
        "สมองที่ 2: Meta Llama 3.3 (70B)",
        "ผลการวิเคราะห์และข้อสรุป (Claude 3 Haiku Evaluation)"
    ]
    ws_sum.row_dimensions[11].height = 26
    for ci, h in enumerate(kpi_headers, 2):
        cell = ws_sum.cell(11, ci, h)
        cell.fill = navy_dark
        cell.font = font_white_bold
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border

    g_p50 = sorted(g_times)[len(g_times)//2] if g_times else 0
    l_p50 = sorted(l_times)[len(l_times)//2] if l_times else 0
    g_p95 = sorted(g_times)[int(len(g_times)*0.95)] if g_times else 0
    l_p95 = sorted(l_times)[int(len(l_times)*0.95)] if l_times else 0

    kpi_rows = [
        ("1. มิติความถูกต้อง (Accuracy)", "Balanced Accuracy (คะแนนรวมเฉลี่ย)", f"{g_acc:.2f}%", f"{l_acc:.2f}%", "รวมคะแนนถูกต้องสมบูรณ์ (1.0) และถูกต้องบางส่วน (0.5)"),
        ("1. มิติความถูกต้อง (Accuracy)", "Strict Accuracy (ถูกต้องสมบูรณ์ 100%)", f"{g_strict:.2f}%", f"{l_strict:.2f}%", "คำตอบมีสาระสำคัญครบถ้วนถูกต้องตามเกณฑ์มาตรฐานโรงพยาบาล"),
        ("1. มิติความถูกต้อง (Accuracy)", "ตอบถูกต้องสมบูรณ์ (1.0 คะแนน)", f"{sum(1 for s in g_scores if s == 1.0)} ข้อ", f"{sum(1 for s in l_scores if s == 1.0)} ข้อ", "ตอบได้แม่นยำตรงตามข้อเท็จจริงในเอกสาร"),
        ("1. มิติความถูกต้อง (Accuracy)", "ตอบถูกต้องบางส่วน (0.5 คะแนน)", f"{sum(1 for s in g_scores if s == 0.5)} ข้อ", f"{sum(1 for s in l_scores if s == 0.5)} ข้อ", "ตอบใจความหลักถูกแต่ขาดรายละเอียดปลีกย่อยบางข้อ"),
        ("1. มิติความถูกต้อง (Accuracy)", "ตอบไม่ถูกต้อง (0.0 คะแนน)", f"{sum(1 for s in g_scores if s == 0.0)} ข้อ", f"{sum(1 for s in l_scores if s == 0.0)} ข้อ", "ตอบผิดประเด็น หรือมีข้อมูลคลาดเคลื่อน"),
        ("2. มิติการค้นคืน (Retrieval)", "การดึง Chunk ตรงหมวด (Hit Rate)", f"{hit_rate:.2f}%", f"{hit_rate:.2f}%", "ระบบ Hybrid Search (ChromaDB + BM25) ดึงเอกสารได้ตรงหมวดนโยบาย"),
        ("3. มิติเวลา (Latency & UX)", "เวลาตอบสนองเฉลี่ย (Average Latency)", f"{g_avg_time:.2f} วินาที", f"{l_avg_time:.2f} วินาที", "ความเร็วในการประมวลผล RAG Pipeline รวมการ Generate ข้อความ"),
        ("3. มิติเวลา (Latency & UX)", "มัธยฐานเวลาตอบ (Median / P50)", f"{g_p50:.2f} วินาที", f"{l_p50:.2f} วินาที", "คำถามเกินครึ่งหนึ่งตอบเสร็จภายในเวลานี้"),
        ("3. มิติเวลา (Latency & UX)", "เกณฑ์ความเร็วขั้นสูง (95th Percentile - P95)", f"{g_p95:.2f} วินาที", f"{l_p95:.2f} วินาที", "95% ของคำถามตอบเสร็จภายในระยะเวลานี้")
    ]

    for ri, row in enumerate(kpi_rows, 12):
        ws_sum.row_dimensions[ri].height = 22
        for ci, val in enumerate(row, 2):
            cell = ws_sum.cell(ri, ci, val)
            cell.font = font_bold if ci in [3, 4] else font_regular
            cell.alignment = Alignment(horizontal="center" if ci in [3, 4] else "left", vertical="center")
            cell.border = thin_border
            if ci == 4:
                cell.fill = PatternFill(start_color="F0FDFA", end_color="F0FDFA", fill_type="solid")
            elif ci == 5:
                cell.fill = PatternFill(start_color="FAF5FF", end_color="FAF5FF", fill_type="solid")

    # ตารางที่ 2: หมวดหมู่
    cat_row_start = 13 + len(kpi_rows)
    ws_sum.cell(cat_row_start, 2, "2. สรุปผลการประเมินแยกตามหมวดหมู่นโยบาย ISO (Category Breakdown)").font = font_section
    cat_headers = [
        "ลำดับ", "หมวดหมู่นโยบาย ISO (ในชีท)", "จำนวนข้อ",
        "ดึง Chunk ตรงหมวด", "คะแนน Gemma 4 (26B)", "คะแนน Llama 3.3 (70B)",
        "เวลาเฉลี่ย Gemma", "เวลาเฉลี่ย Llama", "โมเดลที่ทำได้ดีกว่า"
    ]
    ws_sum.row_dimensions[cat_row_start + 1].height = 26
    for ci, h in enumerate(cat_headers, 2):
        cell = ws_sum.cell(cat_row_start + 1, ci, h)
        cell.fill = navy_dark
        cell.font = font_white_bold
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border

    cats_set = []
    for r in gemma_items:
        if r["category"] not in cats_set:
            cats_set.append(r["category"])

    curr_r = cat_row_start + 2
    for idx, cat in enumerate(cats_set, 1):
        ws_sum.row_dimensions[curr_r].height = 22
        g_sub = [r for r in gemma_items if r["category"] == cat]
        l_sub = [r for r in llama_items if r["category"] == cat]
        cnt = len(g_sub)
        c_hits = sum(1 for r in g_sub if r["is_hit"])
        c_hit_rate = (c_hits / cnt) * 100 if cnt else 0
        c_g_score = (sum(r["score"] for r in g_sub) / cnt) * 100 if cnt else 0
        c_l_score = (sum(r["score"] for r in l_sub) / cnt) * 100 if cnt else 0
        c_g_time = sum(r["response_time"] for r in g_sub) / cnt if cnt else 0
        c_l_time = sum(r["response_time"] for r in l_sub) / cnt if cnt else 0

        if c_l_score > c_g_score:
            better = f"Llama 3.3 (+{c_l_score - c_g_score:.1f}%)"
        elif c_g_score > c_l_score:
            better = f"Gemma 4 (+{c_g_score - c_l_score:.1f}%)"
        else:
            better = "ผลเท่ากัน (Tie)"

        row_vals = [
            idx, cat, cnt, f"{c_hit_rate:.1f}%", f"{c_g_score:.1f}%", f"{c_l_score:.1f}%",
            f"{c_g_time:.2f}s", f"{c_l_time:.2f}s", better
        ]
        for ci, val in enumerate(row_vals, 2):
            cell = ws_sum.cell(curr_r, ci, val)
            cell.font = font_regular
            cell.alignment = Alignment(horizontal="center" if ci != 3 else "left", vertical="center")
            cell.border = thin_border
            if ci == 6:
                cell.fill = PatternFill(start_color="FAF5FF", end_color="FAF5FF", fill_type="solid")
            elif ci == 7:
                cell.fill = PatternFill(start_color="F0FDFA", end_color="F0FDFA", fill_type="solid")
            elif ci == 10:
                if "Llama" in str(val):
                    cell.font = Font(name="Tahoma", size=9, bold=True, color="0F766E")
                elif "Gemma" in str(val):
                    cell.font = Font(name="Tahoma", size=9, bold=True, color="581C87")
        curr_r += 1

    ws_sum.column_dimensions["A"].width = 3
    ws_sum.column_dimensions["B"].width = 24
    ws_sum.column_dimensions["C"].width = 38
    ws_sum.column_dimensions["D"].width = 22
    ws_sum.column_dimensions["E"].width = 22
    ws_sum.column_dimensions["F"].width = 22
    ws_sum.column_dimensions["G"].width = 18
    ws_sum.column_dimensions["H"].width = 18
    ws_sum.column_dimensions["I"].width = 20
    ws_sum.column_dimensions["J"].width = 25

    # ══════════════════════════════════════════════════════════════════════════════
    # SHEET 2: Model Comparison (Side-by-Side)
    # ══════════════════════════════════════════════════════════════════════════════
    ws_cmp = wb.create_sheet(title="Model Comparison")
    ws_cmp.views.sheetView[0].showGridLines = True

    ws_cmp.cell(2, 2, "ตารางเปรียบเทียบคำตอบข้อต่อข้อ: Gemma 4 26B vs Llama 3.3 70B").font = font_title
    ws_cmp.cell(3, 2, "ตัดสินคะแนนและประเมินผลโดยโมเดลกลาง: Anthropic Claude 3 Haiku (LLM-as-a-Judge)").font = font_subtitle

    cmp_headers = [
        "ข้อที่ (เดิม)", "ลำดับสุ่ม", "หมวดหมู่นโยบาย", "คำถาม", "คำตอบที่คาดหวัง",
        "สิ่งที่บอทตอบ [Gemma 4 26B]", "สิ่งที่บอทตอบ [Llama 3.3 70B]",
        "เวลา [Gemma]", "เวลา [Llama]",
        "Chunk IDs", "หัวข้อเอกสารและหน้าที่ Chunk สังกัด", "การดึง Chunk ตรงหมวด",
        "คะแนน Gemma", "ผลตัดสิน Gemma", "เหตุผล Gemma (Claude 3 Haiku)",
        "คะแนน Llama", "ผลตัดสิน Llama", "เหตุผล Llama (Claude 3 Haiku)",
        "ผลเปรียบเทียบ"
    ]
    ws_cmp.row_dimensions[5].height = 28
    for ci, h in enumerate(cmp_headers, 2):
        cell = ws_cmp.cell(5, ci, h)
        if "Gemma" in h:
            cell.fill = purple_gemma
        elif "Llama" in h:
            cell.fill = teal_llama
        else:
            cell.fill = navy_dark
        cell.font = font_white_bold
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border

    for ri, (g_item, l_item) in enumerate(zip(gemma_items, llama_items), 6):
        ws_cmp.row_dimensions[ri].height = 65
        if l_item["score"] > g_item["score"]:
            comp_txt = f"Llama ชนะ (+{l_item['score'] - g_item['score']:.1f})"
        elif g_item["score"] > l_item["score"]:
            comp_txt = f"Gemma ชนะ (+{g_item['score'] - l_item['score']:.1f})"
        else:
            comp_txt = "คะแนนเท่ากัน"

        row_vals = [
            g_item["orig_no"],
            g_item["run_no"],
            g_item["category"],
            g_item["question"],
            g_item["expected_answer"],
            g_item["bot_answer"],
            l_item["bot_answer"],
            f"{g_item['response_time']:.2f}s",
            f"{l_item['response_time']:.2f}s",
            g_item["chunk_ids"],
            g_item["doc_info"],
            g_item["hit_text"],
            g_item["score"],
            g_item["verdict"],
            g_item["reason"],
            l_item["score"],
            l_item["verdict"],
            l_item["reason"],
            comp_txt
        ]
        for ci, val in enumerate(row_vals, 2):
            cell = ws_cmp.cell(ri, ci, val)
            cell.font = font_regular
            cell.border = thin_border

            # การจัดแนว
            if ci in [2, 3]:
                cell.alignment = Alignment(horizontal="center", vertical="top")
            elif ci in [9, 10, 14, 15, 17, 18, 20]:
                cell.alignment = Alignment(horizontal="center", vertical="top")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)

            # สีไฮไลต์
            if ci in [14, 15]:
                if g_item["score"] == 1.0:
                    cell.fill = fill_correct
                    cell.font = font_correct
                elif g_item["score"] == 0.5:
                    cell.fill = fill_partial
                    cell.font = font_partial
                else:
                    cell.fill = fill_incorrect
                    cell.font = font_incorrect
            elif ci in [17, 18]:
                if l_item["score"] == 1.0:
                    cell.fill = fill_correct
                    cell.font = font_correct
                elif l_item["score"] == 0.5:
                    cell.fill = fill_partial
                    cell.font = font_partial
                else:
                    cell.fill = fill_incorrect
                    cell.font = font_incorrect
            elif ci == 13:
                if val == "ตรงหมวด (Hit)":
                    cell.fill = fill_hit
                    cell.font = font_hit
                else:
                    cell.fill = fill_miss
                    cell.font = font_miss
            elif ci == 20:
                if "Llama" in str(val):
                    cell.font = Font(name="Tahoma", size=9, bold=True, color="0F766E")
                elif "Gemma" in str(val):
                    cell.font = Font(name="Tahoma", size=9, bold=True, color="581C87")

    cmp_widths = {
        "A": 3, "B": 12, "C": 12, "D": 25, "E": 32, "F": 32, "G": 42, "H": 42,
        "I": 14, "J": 14, "K": 18, "L": 35, "M": 18, "N": 14, "O": 16, "P": 35,
        "Q": 14, "R": 16, "S": 35, "T": 18
    }
    for col_letter, w in cmp_widths.items():
        ws_cmp.column_dimensions[col_letter].width = w

    # ══════════════════════════════════════════════════════════════════════════════
    # SHEETS 3 & 4: Detailed Model Sheets
    # ══════════════════════════════════════════════════════════════════════════════
    for model_title, m_data, m_fill in [
        ("Gemma 4 26B", gemma_items, purple_gemma),
        ("Llama 3.3 70B", llama_items, teal_llama)
    ]:
        ws_m = wb.create_sheet(title=model_title)
        ws_m.views.sheetView[0].showGridLines = True

        ws_m.cell(2, 2, f"ผลการทดสอบระบบแชทบอท TUH — โมเดล {model_title}").font = font_title
        ws_m.cell(3, 2, f"คำตอบจากแชทบอทจริง ประเมินและให้คะแนนโดย Anthropic Claude 3 Haiku").font = font_subtitle

        m_headers = [
            "ข้อที่ (เดิม)", "ลำดับสุ่ม", "หมวดหมู่นโยบาย (ในชีท)", "คำถาม", "สิ่งที่บอทตอบ",
            "คำตอบที่คาดหวัง", "เวลาในการตอบ", "Chunk ที่ใช้ตอบ", "หัวข้อเอกสารและหน้าที่ Chunk สังกัด",
            "การดึง Chunk ตรงหมวด", "คะแนน", "ผลตัดสิน", "เหตุผลการให้คะแนน (Claude 3 Haiku)"
        ]
        ws_m.row_dimensions[5].height = 26
        for ci, h in enumerate(m_headers, 2):
            cell = ws_m.cell(5, ci, h)
            cell.fill = m_fill
            cell.font = font_white_bold
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = thin_border

        for ri, r in enumerate(m_data, 6):
            ws_m.row_dimensions[ri].height = 60
            row_vals = [
                r["orig_no"],
                r["run_no"],
                r["category"],
                r["question"],
                r["bot_answer"],
                r["expected_answer"],
                f"{r['response_time']:.2f} วินาที",
                r["chunk_ids"],
                r["doc_info"],
                r["hit_text"],
                r["score"],
                r["verdict"],
                r["reason"]
            ]
            for ci, val in enumerate(row_vals, 2):
                cell = ws_m.cell(ri, ci, val)
                cell.font = font_regular
                cell.border = thin_border

                if ci in [2, 3, 8]:
                    cell.alignment = Alignment(horizontal="center", vertical="top")
                elif ci in [11, 12, 13]:
                    cell.alignment = Alignment(horizontal="center", vertical="top")
                else:
                    cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)

                if ci == 11:
                    if val == "ตรงหมวด (Hit)":
                        cell.fill = fill_hit
                        cell.font = font_hit
                    else:
                        cell.fill = fill_miss
                        cell.font = font_miss
                elif ci in [12, 13]:
                    if r["score"] == 1.0:
                        cell.fill = fill_correct
                        cell.font = font_correct
                    elif r["score"] == 0.5:
                        cell.fill = fill_partial
                        cell.font = font_partial
                    else:
                        cell.fill = fill_incorrect
                        cell.font = font_incorrect

        m_widths = {
            "A": 3, "B": 12, "C": 12, "D": 25, "E": 35, "F": 45, "G": 38,
            "H": 16, "I": 18, "J": 35, "K": 20, "L": 12, "M": 16, "N": 45
        }
        for col_letter, w in m_widths.items():
            ws_m.column_dimensions[col_letter].width = w

    wb.save(OUT_EXCEL)
    print(f"\n🎉 บันทึกไฟล์ Excel ใหม่สำเร็จแล้ว: {OUT_EXCEL}")


def main():
    print("=" * 80)
    print("🤖 TUH Chatbot — Evaluation & Report Generator (test2Model.xlsx)")
    print(f"🎯 กรรมการตัดสิน: {JUDGE_MODEL}")
    print("=" * 80)

    # 1. โหลดข้อมูลเดิม
    print(f"\n📂 กำลังโหลดข้อมูลคำตอบเดิมจาก: {SRC_EXCEL.name} ...")
    gemma_items, llama_items = load_test_data()
    print(f"✅ โหลดข้อมูลสำเร็จ: Gemma {len(gemma_items)} ข้อ, Llama {len(llama_items)} ข้อ")

    # 2. ให้ Claude 3 Haiku ตรวจคำตอบทั้งหมด
    print(f"\n⚖️ กำลังให้โมเดล '{JUDGE_MODEL}' ตรวจให้คะแนนคำตอบ...")
    evaluate_all(gemma_items, llama_items)

    # 3. สร้างรายงาน Excel test2Model.xlsx
    print(f"\n📊 กำลังสร้างไฟล์ Excel ใหม่: {OUT_EXCEL.name} ...")
    build_test2model_excel(gemma_items, llama_items)
    print("\n✅ เสร็จสมบูรณ์ทุกขั้นตอน!")


if __name__ == "__main__":
    main()
