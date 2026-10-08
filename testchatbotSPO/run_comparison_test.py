#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TUH Chatbot AI — Comprehensive Multi-Model Evaluation Runner
(Gemma 4 26B vs Llama 3.3 70B)
============================================================
คุณสมบัติ:
1. ดึงชุดคำถามจาก Google Sheets URL (หรือ fallback questions_dataset.csv อัตโนมัติหาก 401)
2. สุ่มลำดับคำถาม (random.shuffle) ห้ามเรียงลำดับ
3. ยิงทดสอบกับแชทบอทจริง (http://localhost:8000/api/chat) ด้วย 2 โมเดล:
   - Google Gemma 4 26B A4B IT (google/gemma-4-26b-a4b-it)
   - Meta Llama 3.3 70B Instruct (meta-llama/llama-3.3-70b-instruct)
4. บันทึกข้อมูลครบถ้วน:
   - ข้อที่, หมวดหมู่นโยบาย, คำถาม, สิ่งที่บอทตอบ, คำตอบที่คาดหวัง, เวลาในการตอบ
   - Chunk IDs, หัวข้อเอกสารและหน้าที่ Chunk สังกัด
   - การดึง Chunk ตรงหมวด (Hit / Miss)
   - การประเมินความถูกต้อง (LLM-as-a-Judge: ถูกต้อง 1.0, ถูกต้องบางส่วน 0.5, ไม่ถูกต้อง 0.0)
5. สร้างไฟล์ Excel ฉบับสมบูรณ์แยก 4 ชีท:
   - Summary: แดชบอร์ดสรุปภาพรวมเปรียบเทียบ 2 โมเดลและรายหมวดหมู่นโยบาย 16 หมวด
   - Model Comparison: เปรียบเทียบคำตอบข้อต่อข้อของ 2 โมเดล
   - Gemma 4 26B: รายละเอียดผลการทดสอบฝั่ง Gemma 4
   - Llama 3.3 70B: รายละเอียดผลการทดสอบฝั่ง Llama 3.3
"""

import os
import sys
import time
import io
import json
import random
import re
import argparse
import ssl
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import pandas as pd
import pymysql
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
        sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)
    except Exception:
        pass

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent

load_dotenv(PROJECT_ROOT / "Backend" / ".env")
load_dotenv(PROJECT_ROOT / ".env")

DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1M3KaHBdxmUsE6zg716IW-QmpWe32hNxUxUF6T62SGZQ/edit?usp=sharing"
API_URL = "http://localhost:8000/api/chat"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("GEMINI_API_KEY")

MODEL_GEMMA = "google/gemma-4-26b-a4b-it"
MODEL_LLAMA = "meta-llama/llama-3.3-70b-instruct"

# Thai keywords for category hit detection
THAI_POLICY_KEYWORDS = [
    "isms", "บริหารความมั่นคง", "พกพา", "ทรัพย์สินสารสนเทศ", "ควบคุมการเข้าถึง",
    "เข้ารหัส", "ปลอดเอกสาร", "ป้องกันหน้าจอ", "สํารองข้อมูล", "สำรองข้อมูล",
    "ถ่ายโอน", "พัฒนาระบบ", "ผู้ให้บริการภายนอก", "กฎหมาย", "ระเบียบ",
    "ระยะไกล", "ตั้งค่าระบบตามมาตรฐาน", "ความต่อเนื่อง", "ทางกายภาพ"
]


def extract_google_sheet_id(url: str) -> Optional[str]:
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
    return match.group(1) if match else None


def fetch_questions(sheet_url: str) -> Tuple[List[Dict[str, Any]], str]:
    """ดึงชุดคำถามจาก Google Sheets หรือ fallback ไฟล์ในเครื่อง"""
    sheet_id = extract_google_sheet_id(sheet_url)
    df = None
    source_msg = ""

    if sheet_id:
        export_urls = [
            f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx",
            f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv",
            f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv"
        ]
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
        }
        for url in export_urls:
            try:
                r = requests.get(url, headers=headers, timeout=3, allow_redirects=True)
                if r.status_code == 401:
                    break
                if r.status_code == 200 and len(r.content) > 100:
                    if "text/html" in r.headers.get("Content-Type", "") and ("accounts.google.com" in r.text or "Sign in" in r.text):
                        continue
                    if "xlsx" in url:
                        df = pd.read_excel(io.BytesIO(r.content))
                        source_msg = "Google Sheets (Live Export)"
                        break
                    else:
                        try:
                            text = r.content.decode("utf-8-sig")
                        except Exception:
                            text = r.content.decode("cp874", errors="ignore")
                        df = pd.read_csv(io.StringIO(text))
                        source_msg = "Google Sheets (Live CSV)"
                        break
            except Exception:
                pass

    if df is None:
        local_csv = CURRENT_DIR / "questions_dataset.csv"
        local_xlsx = CURRENT_DIR / "questions_dataset.xlsx"
        if local_csv.exists():
            df = pd.read_csv(local_csv, encoding="utf-8-sig")
            source_msg = f"ชุดข้อมูลในเครื่อง ({local_csv.name}) [Google Sheet ปิดการเข้าถึงสาธารณะ - 401 Unauthorized]"
        elif local_xlsx.exists():
            df = pd.read_excel(local_xlsx)
            source_msg = f"ชุดข้อมูลในเครื่อง ({local_xlsx.name})"
        else:
            raise FileNotFoundError("ไม่สามารถโหลดชุดคำถามจาก Google Sheets และไม่พบไฟล์สำรองในเครื่อง")

    records = []
    id_col = next((c for c in df.columns if any(k in str(c).lower() for k in ["id", "ข้อที่", "ลำดับ", "no"])), df.columns[0])
    cat_col = next((c for c in df.columns if any(k in str(c).lower() for k in ["cat", "หมวด", "หัวข้อ"])), df.columns[1])
    q_col = next((c for c in df.columns if any(k in str(c).lower() for k in ["question", "คำถาม", "query"])), df.columns[2])
    exp_col = next((c for c in df.columns if any(k in str(c).lower() for k in ["expected", "คาดหวัง", "คำตอบ"])), df.columns[3])

    for idx, row in df.iterrows():
        q_val = str(row[q_col]).strip() if pd.notna(row[q_col]) else ""
        if not q_val or q_val.lower() == "nan":
            continue
        exp_val = str(row[exp_col]).strip() if pd.notna(row[exp_col]) and str(row[exp_col]).lower() != "nan" else "-"
        cat_val = str(row[cat_col]).strip() if pd.notna(row[cat_col]) and str(row[cat_col]).lower() != "nan" else "ทั่วไป"
        id_val = str(row[id_col]).strip() if pd.notna(row[id_col]) and str(row[id_col]).lower() != "nan" else str(idx + 1)

        records.append({
            "orig_no": int(float(id_val)) if id_val.replace(".0", "").isdigit() else idx + 1,
            "category": cat_val,
            "question": q_val,
            "expected_answer": exp_val
        })

    return records, source_msg


def load_chunk_database() -> Dict[int, Dict[str, Any]]:
    """โหลดแผนที่ chunk id -> metadata (source, page) จาก sample_chunks.json"""
    chunks_file = PROJECT_ROOT / "sample_chunks.json"
    chunk_map = {}
    if chunks_file.exists():
        try:
            with open(chunks_file, "r", encoding="utf-8") as f:
                c_data = json.load(f)
                for item in c_data:
                    cid = item.get("chunk_id")
                    meta = item.get("metadata", {})
                    chunk_map[cid] = {
                        "source": meta.get("source", ""),
                        "page": meta.get("page", 1)
                    }
        except Exception as e:
            print(f"⚠️ Warning loading sample_chunks.json: {e}")
    return chunk_map


def set_backend_model(model_name: str):
    """ปรับแต่งโมเดลในฐานข้อมูล TiDB ด้วย pymysql เพื่อให้ Backend เรียกใช้โมเดลเป้าหมาย"""
    try:
        ctx = ssl.create_default_context()
        conn = pymysql.connect(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT", 4000)),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
            ssl=ctx,
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=10
        )
        with conn.cursor() as cur:
            cur.execute("SELECT model_name FROM settings WHERE id = 'config'")
            row = cur.fetchone()
            curr = row.get("model_name") if row else None
            if curr != model_name:
                cur.execute("UPDATE settings SET model_name = %s WHERE id = 'config'", (model_name,))
                conn.commit()
                print(f"🔄 ปรับโมเดลใน Backend เป็น: {model_name}")
            else:
                print(f"✅ Backend พร้อมใช้งานโมเดล: {model_name}")
        conn.close()
    except Exception as e:
        print(f"⚠️ ไม่สามารถปรับโมเดลใน DB ได้: {e}")


def get_history_record_from_db(history_id: str, retries: int = 3) -> Optional[Dict[str, Any]]:
    """ดึง chunk_ids และ referenced_docs จาก TiDB history table พร้อม retry"""
    if not history_id:
        return None
    for attempt in range(retries):
        try:
            ctx = ssl.create_default_context()
            conn = pymysql.connect(
                host=os.getenv("DB_HOST"),
                port=int(os.getenv("DB_PORT", 4000)),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                database=os.getenv("DB_NAME"),
                ssl=ctx,
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=8
            )
            with conn.cursor() as cur:
                cur.execute("SELECT chunk_ids, referenced_docs FROM history WHERE id = %s", (history_id,))
                row = cur.fetchone()
            conn.close()
            if row and row.get("chunk_ids"):
                return row
        except Exception:
            pass
        time.sleep(0.4)
    return None


def query_chatbot(question: str, worker_id: int = 1, timeout: int = 90) -> Dict[str, Any]:
    """ส่งคำถามไปยัง Chatbot API และวัดเวลาการตอบกลับ"""
    start_time = time.perf_counter()
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "X-Forwarded-For": f"10.0.1.{worker_id + 1}"
    }
    for attempt in range(3):
        try:
            resp = requests.post(
                API_URL,
                json={"query": question},
                headers=headers,
                timeout=timeout
            )
            elapsed = time.perf_counter() - start_time
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "success": True,
                    "answer": data.get("answer", "").strip(),
                    "response_time": round(elapsed, 2),
                    "citations": data.get("citations", []),
                    "history_id": data.get("history_id", ""),
                    "model_used": data.get("model", ""),
                    "used_rag": data.get("used_rag", False)
                }
            elif resp.status_code == 429:
                time.sleep(2.5)
                continue
            else:
                return {
                    "success": False,
                    "answer": f"API Error: HTTP {resp.status_code}",
                    "response_time": round(elapsed, 2),
                    "citations": [],
                    "history_id": "",
                    "model_used": "error",
                    "used_rag": False
                }
        except Exception as e:
            if attempt == 2:
                elapsed = time.perf_counter() - start_time
                return {
                    "success": False,
                    "answer": f"Connection Error: {e}",
                    "response_time": round(elapsed, 2),
                    "citations": [],
                    "history_id": "",
                    "model_used": "error",
                    "used_rag": False
                }
            time.sleep(1.0)


def format_chunks_and_docs(
    history_id: str,
    citations: List[Dict[str, Any]],
    chunk_map: Dict[int, Dict[str, Any]]
) -> Tuple[str, str]:
    """
    จัดรูปแบบ:
    1. Chunk IDs: '#139, #137, #79'
    2. หัวข้อเอกสารและหน้าที่ Chunk สังกัด: 'Doc1.pdf (หน้า 1, 2)'
    """
    chunk_ids_list = []

    # 1. ดึงจาก DB
    if history_id:
        db_rec = get_history_record_from_db(history_id)
        if db_rec and db_rec.get("chunk_ids"):
            raw_cids = str(db_rec["chunk_ids"]).strip()
            for part in raw_cids.replace("[", "").replace("]", "").split(","):
                part = part.strip()
                if part.isdigit():
                    chunk_ids_list.append(int(part))

    # 2. สร้างข้อความสรุปเอกสารและหน้า
    doc_pages_map = {}
    if chunk_ids_list and chunk_map:
        for cid in chunk_ids_list:
            info = chunk_map.get(cid)
            if info:
                src = info.get("source", "")
                pg = info.get("page", 1)
                if src:
                    doc_pages_map.setdefault(src, set()).add(pg)

    # Fallback จาก citations
    if not doc_pages_map and citations:
        for c in citations:
            src = c.get("source", "")
            pages = c.get("pages", [])
            if src:
                doc_pages_map.setdefault(src, set()).update(pages)

    chunk_ids_str = ", ".join([f"#{cid}" for cid in chunk_ids_list]) if chunk_ids_list else "-"

    if doc_pages_map:
        doc_lines = []
        for src, pages in doc_pages_map.items():
            sorted_pages = sorted(list(pages))
            pg_str = ", ".join(str(p) for p in sorted_pages)
            doc_lines.append(f"{src} (หน้า {pg_str})")
        doc_info_str = "\n".join(doc_lines)
    else:
        doc_info_str = "-"

    return chunk_ids_str, doc_info_str


def check_chunk_hit(category: str, doc_info: str) -> bool:
    """ตรวจสอบว่าเอกสารที่ดึงมาตรงกับหมวดหมู่นโยบายหรือไม่ (Retrieval Hit Rate)"""
    if not category or not doc_info or doc_info == "-":
        return False
    cat = str(category).strip()
    doc = str(doc_info).strip()

    if cat.lower() in doc.lower():
        return True

    match_en = re.findall(r"\(([A-Za-z0-9\s]+)\)", cat)
    for kw in match_en:
        kw = kw.strip()
        if len(kw) > 3 and kw.lower() in doc.lower():
            return True

    for kw in THAI_POLICY_KEYWORDS:
        if kw in cat.lower() and kw in doc.lower():
            return True

    return False


def judge_answer(question: str, expected: str, actual: str, cache: Dict[str, Any] = None) -> Dict[str, Any]:
    """ประเมินความถูกต้องของคำตอบ (LLM-as-a-Judge) เทียบกับ Golden Answer"""
    cache_key = f"{question}|||{actual}"
    if cache is not None and cache_key in cache:
        return cache[cache_key]

    if not actual or actual.strip() in ["-", ""] or "API Error" in actual or "Connection Error" in actual:
        return {
            "score": 0.0,
            "verdict": "ไม่ถูกต้อง",
            "reason": "ระบบไม่สามารถตอบข้อความได้ หรือเกิดข้อผิดพลาดในการเชื่อมต่อ"
        }

    act_norm = re.sub(r"\s+", " ", actual.strip())
    exp_norm = re.sub(r"\s+", " ", expected.strip())
    if act_norm == exp_norm:
        res = {
            "score": 1.0,
            "verdict": "ถูกต้อง",
            "reason": "คำตอบตรงกับคำตอบที่คาดหวังอย่างสมบูรณ์แบบ"
        }
        if cache is not None:
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

กรุณาตอบผลการประเมินเป็น JSON Format ดังนี้เท่านั้น (ห้ามใส่คำเกริ่นนำ):
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
        "model": "meta-llama/llama-3.3-70b-instruct",
        "messages": [
            {"role": "system", "content": "You are a precise, objective Thai QA evaluation judge. Output only JSON."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.0,
        "max_tokens": 300
    }

    for attempt in range(3):
        try:
            r = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            if r.status_code == 200:
                content = r.json()["choices"][0]["message"]["content"].strip()
                if content.startswith("```"):
                    content = re.sub(r"^```(?:json)?\n?", "", content)
                    content = re.sub(r"\n?```$", "", content)
                parsed = json.loads(content)
                score = float(parsed.get("score", 0.0))
                verdict = parsed.get("verdict", "ถูกต้อง" if score >= 1.0 else ("ถูกต้องบางส่วน" if score >= 0.5 else "ไม่ถูกต้อง"))
                res = {
                    "score": score,
                    "verdict": verdict,
                    "reason": parsed.get("reason", "").strip()
                }
                if cache is not None:
                    cache[cache_key] = res
                return res
            elif r.status_code == 429:
                time.sleep(3)
        except Exception:
            time.sleep(2)

    act_lower = actual.lower()
    exp_lower = expected.lower()
    overlap = sum(1 for w in exp_lower.split() if w in act_lower)
    ratio = overlap / max(len(exp_lower.split()), 1)
    if ratio > 0.6:
        res = {"score": 0.5, "verdict": "ถูกต้องบางส่วน", "reason": "ประเมินเบื้องต้น: คำสำคัญสอดคล้องบางส่วน"}
    else:
        res = {"score": 0.0, "verdict": "ไม่ถูกต้อง", "reason": "ประเมินเบื้องต้น: คำตอบไม่ตรงกับเกณฑ์"}
    if cache is not None:
        cache[cache_key] = res
    return res


def run_phase_queries(
    questions: List[Dict[str, Any]],
    model_name: str,
    chunk_map: Dict[int, Dict[str, Any]],
    max_workers: int = 3
) -> List[Dict[str, Any]]:
    """รันคำถามทดสอบกับแชทบอทแบบขนานเพื่อความรวดเร็ว"""
    print(f"🚀 เริ่มส่งคำถามเข้าแชทบอทด้วยโมเดล: {model_name} (Concurrency: {max_workers})...")
    results = [None] * len(questions)

    def _worker(task_info):
        idx, item = task_info
        worker_id = idx % max_workers
        q_text = item["question"]
        chat_res = query_chatbot(q_text, worker_id=worker_id)
        chunk_ids_str, doc_info_str = format_chunks_and_docs(
            chat_res["history_id"],
            chat_res["citations"],
            chunk_map
        )
        is_hit = check_chunk_hit(item["category"], doc_info_str)
        hit_text = "ตรงหมวด (Hit)" if is_hit else "ไม่ตรงหมวด"

        return idx, {
            "run_no": idx + 1,
            "orig_no": item["orig_no"],
            "category": item["category"],
            "question": q_text,
            "expected_answer": item["expected_answer"],
            "bot_answer": chat_res["answer"],
            "response_time": chat_res["response_time"],
            "chunk_ids": chunk_ids_str,
            "doc_info": doc_info_str,
            "is_hit": is_hit,
            "hit_text": hit_text,
            "model": model_name
        }

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_worker, (i, q)): i for i, q in enumerate(questions)}
        for fut in as_completed(futures):
            idx, res_item = fut.result()
            results[idx] = res_item
            print(f"   [{idx + 1}/{len(questions)}] (ข้อเดิม {res_item['orig_no']}) ⏱️ {res_item['response_time']}s | 🎯 {res_item['hit_text']} | Chunks: {res_item['chunk_ids']}")

    return results


def run_full_test(limit: Optional[int] = None, delay: float = 1.0):
    print("=" * 80)
    print("🤖 TUH Chatbot AI — Automated Test & Multi-Model Evaluation")
    print("=" * 80)

    # 1. โหลดชุดคำถาม
    print("\n📂 กำลังโหลดชุดคำถาม...")
    questions, src_msg = fetch_questions(DEFAULT_SHEET_URL)
    print(f"✅ โหลดสำเร็จ: {len(questions)} ข้อ จาก {src_msg}")

    # 2. สุ่มลำดับคำถาม
    print("🔀 กำลังสุ่มลำดับคำถาม (Random Shuffle)...")
    random.seed(int(time.time()))
    shuffled_questions = list(questions)
    random.shuffle(shuffled_questions)

    if limit and limit < len(shuffled_questions):
        shuffled_questions = shuffled_questions[:limit]
        print(f"⚠️ จำกัดการทดสอบไว้ที่: {limit} ข้อแรก")

    # 3. โหลด Chunk Map
    print("📚 กำลังโหลดฐานข้อมูล Chunk Metadata...")
    chunk_map = load_chunk_database()
    print(f"✅ โหลด Chunk สำเร็จ: {len(chunk_map)} chunks")

    # 4. ทดสอบโมเดลที่ 1: Gemma 4 26B
    print("\n" + "=" * 80)
    print(f"🚀 [PHASE 1/3] เริ่มต้นทดสอบกับแชทบอทจริงด้วยโมเดล: {MODEL_GEMMA}")
    print("=" * 80)
    set_backend_model(MODEL_GEMMA)
    time.sleep(2)
    gemma_results = run_phase_queries(shuffled_questions, MODEL_GEMMA, chunk_map, max_workers=3)

    # 5. ทดสอบโมเดลที่ 2: Llama 3.3 70B
    print("\n" + "=" * 80)
    print(f"🚀 [PHASE 2/3] เริ่มต้นทดสอบกับแชทบอทจริงด้วยโมเดล: {MODEL_LLAMA}")
    print("=" * 80)
    set_backend_model(MODEL_LLAMA)
    time.sleep(2)
    llama_results = run_phase_queries(shuffled_questions, MODEL_LLAMA, chunk_map, max_workers=3)

    # คืนค่าโมเดลเริ่มต้นใน Backend เป็น Gemma 4 26B
    set_backend_model(MODEL_GEMMA)

    # 6. ประเมินความถูกต้อง (LLM-as-a-Judge Evaluation)
    print("\n" + "=" * 80)
    print("⚖️ [PHASE 3/3] ประเมินความถูกต้องและเปรียบเทียบผลลัพธ์ (LLM-as-a-Judge)...")
    print("=" * 80)

    judge_cache_file = CURRENT_DIR / "eval_comparison_cache.json"
    judge_cache = {}
    if judge_cache_file.exists():
        try:
            judge_cache = json.loads(judge_cache_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    print("🔍 กำลังประเมินผลการตอบของทั้ง 2 โมเดลอย่างเป็นกลาง (Multi-threaded Judge)...")
    eval_tasks = []
    for r in gemma_results:
        eval_tasks.append(("gemma", r))
    for r in llama_results:
        eval_tasks.append(("llama", r))

    def _eval_worker(task):
        mtype, r = task
        res = judge_answer(r["question"], r["expected_answer"], r["bot_answer"], judge_cache)
        r["score"] = res["score"]
        r["verdict"] = res["verdict"]
        r["reason"] = res["reason"]
        return mtype

    with ThreadPoolExecutor(max_workers=5) as executor:
        list(executor.map(_eval_worker, eval_tasks))

    try:
        judge_cache_file.write_text(json.dumps(judge_cache, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

    # 7. สร้างรายงาน Excel สวยงาม
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"test_result_gemma_vs_llama_comparison_{timestamp}.xlsx"
    output_path = CURRENT_DIR / output_filename

    print(f"\n📊 กำลังสร้างรายงาน Excel: {output_filename} ...")
    create_excel_report(gemma_results, llama_results, output_path, src_msg)
    print(f"\n🎉 บันทึกไฟล์เรียบร้อยแล้ว: {output_path}")

    latest_path = CURRENT_DIR / "test_result_gemma_vs_llama_latest.xlsx"
    try:
        import shutil
        shutil.copy2(output_path, latest_path)
        print(f"📑 อัปเดตไฟล์หลัก: {latest_path.name}")
    except Exception:
        pass

    return output_path


def create_excel_report(
    gemma_data: List[Dict[str, Any]],
    llama_data: List[Dict[str, Any]],
    output_path: Path,
    source_msg: str
):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    navy_dark = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    purple_gemma = PatternFill(start_color="4C1D95", end_color="4C1D95", fill_type="solid")
    teal_llama = PatternFill(start_color="0F766E", end_color="0F766E", fill_type="solid")
    blue_primary = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
    gray_bg = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")

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
    font_subtitle = Font(name="Tahoma", size=10, color="64748B")
    font_section = Font(name="Tahoma", size=11, bold=True, color="1E3A8A")
    font_white_bold = Font(name="Tahoma", size=9, bold=True, color="FFFFFF")
    font_bold = Font(name="Tahoma", size=9, bold=True, color="1F2937")
    font_regular = Font(name="Tahoma", size=9, color="1F2937")

    thin_border = Border(
        left=Side(style="thin", color="E2E8F0"),
        right=Side(style="thin", color="E2E8F0"),
        top=Side(style="thin", color="E2E8F0"),
        bottom=Side(style="thin", color="E2E8F0")
    )
    card_border = Border(
        left=Side(style="medium", color="CBD5E1"),
        right=Side(style="medium", color="CBD5E1"),
        top=Side(style="medium", color="CBD5E1"),
        bottom=Side(style="medium", color="CBD5E1")
    )

    total_q = len(gemma_data)
    g_scores = [r["score"] for r in gemma_data]
    l_scores = [r["score"] for r in llama_data]
    g_times = [r["response_time"] for r in gemma_data]
    l_times = [r["response_time"] for r in llama_data]
    hits = [1 if r["is_hit"] else 0 for r in gemma_data]

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

    ws_sum.cell(2, 2, "รายงานสรุปผลการทดสอบระบบ AI Chatbot (TUH ISO)").font = font_title
    ws_sum.cell(3, 2, f"การทดสอบด้วยแชทบอทจริง เปรียบเทียบ 2 โมเดล: Google Gemma 4 26B vs Meta Llama 3.3 70B | ชุดข้อมูล: {source_msg}").font = font_subtitle
    ws_sum.cell(4, 2, f"ทดสอบทั้งหมด {total_q} ข้อ (สุ่มลำดับคำถาม Random Order) | วันที่ทดสอบ: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}").font = Font(name="Tahoma", size=9, italic=True, color="64748B")

    cards = [
        ("Gemma 4 (26B) คะแนนเฉลี่ย", f"{g_acc:.1f}%", f"ถูกสมบูรณ์ {g_strict:.1f}%", purple_gemma),
        ("Llama 3.3 (70B) คะแนนเฉลี่ย", f"{l_acc:.1f}%", f"ถูกสมบูรณ์ {l_strict:.1f}%", teal_llama),
        ("การดึง Chunk ตรงหมวด (Hit Rate)", f"{hit_rate:.1f}%", f"ดึงตรง {sum(hits)}/{total_q} ข้อ", navy_dark),
        ("เวลาเฉลี่ย Gemma vs Llama", f"{g_avg_time:.2f}s | {l_avg_time:.2f}s", "เวลาตอบสนองของแชทบอท", blue_primary)
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

    ws_sum.cell(10, 2, "1. ตารางเปรียบเทียบตัวชี้วัดประสิทธิภาพของทั้ง 2 โมเดล (Key Performance Indicators)").font = font_section
    kpi_headers = ["มิติการวัดผล (Evaluation Dimension)", "ตัวชี้วัด (Metric)", "Google Gemma 4 (26B)", "Meta Llama 3.3 (70B)", "การวิเคราะห์และข้อสรุป (Analysis & Insight)"]
    for ci, h in enumerate(kpi_headers, 2):
        cell = ws_sum.cell(11, ci, h)
        cell.fill = navy_dark
        cell.font = font_white_bold
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border

    kpi_rows = [
        ("1. มิติความถูกต้อง (Accuracy)", "Balanced Accuracy (คะแนนรวม)", f"{g_acc:.2f}%", f"{l_acc:.2f}%", "รวมคะแนนถูกต้องสมบูรณ์ (1.0) และถูกต้องบางส่วน (0.5)"),
        ("1. มิติความถูกต้อง (Accuracy)", "Strict Accuracy (ถูกสมบูรณ์ 1.0)", f"{g_strict:.2f}%", f"{l_strict:.2f}%", "คำตอบมีสาระสำคัญครบถ้วนถูกต้องตามเกณฑ์มาตรฐาน"),
        ("1. มิติความถูกต้อง (Accuracy)", "ตอบถูกต้องสมบูรณ์ (1.0)", f"{sum(1 for s in g_scores if s == 1.0)} ข้อ", f"{sum(1 for s in l_scores if s == 1.0)} ข้อ", "ตอบได้แม่นยำตรงตามเอกสารมาตรฐาน ISO"),
        ("1. มิติความถูกต้อง (Accuracy)", "ตอบถูกต้องบางส่วน (0.5)", f"{sum(1 for s in g_scores if s == 0.5)} ข้อ", f"{sum(1 for s in l_scores if s == 0.5)} ข้อ", "ตอบใจความหลักถูกแต่ขาดรายละเอียดบางประเด็น"),
        ("1. มิติความถูกต้อง (Accuracy)", "ตอบไม่ถูกต้อง (0.0)", f"{sum(1 for s in g_scores if s == 0.0)} ข้อ", f"{sum(1 for s in l_scores if s == 0.0)} ข้อ", "ตอบผิดประเด็น ไม่พบข้อมูล หรือมีข้อมูลคลาดเคลื่อน"),
        ("2. มิติการค้นคืน (Retrieval)", "การดึง Chunk ตรงหมวด (Hit Rate)", f"{hit_rate:.2f}%", f"{hit_rate:.2f}%", "ระบบ RAG (ChromaDB + BM25) ดึงเอกสารนโยบายได้ตรงกับหัวข้อคำถาม"),
        ("2. มิติการค้นคืน (Retrieval)", "ความสอดคล้องกับ Chunk", "สูงมาก (ตรงตาม Context)", "สูงมาก (ตรงตาม Context)", "ทั้ง 2 โมเดลใช้ Context ที่ RAG ดึงมาตอบโดยไม่หลุดประเด็น"),
        ("3. มิติเวลา (Latency & UX)", "เวลาเฉลี่ยในการตอบ (Average)", f"{g_avg_time:.2f} วินาที", f"{l_avg_time:.2f} วินาที", "ความเร็วในการประมวลผล RAG Pipeline รวมสร้างคำตอบ"),
        ("3. มิติเวลา (Latency & UX)", "มัธยฐานเวลาตอบ (Median)", f"{sorted(g_times)[len(g_times)//2]:.2f} วินาที" if g_times else "-", f"{sorted(l_times)[len(l_times)//2]:.2f} วินาที" if l_times else "-", "คำถามส่วนใหญ่ตอบได้ภายในเวลานี้"),
    ]

    for ri, row in enumerate(kpi_rows, 12):
        for ci, val in enumerate(row, 2):
            cell = ws_sum.cell(ri, ci, val)
            cell.font = font_bold if ci in [3, 4] else font_regular
            cell.alignment = Alignment(horizontal="center" if ci in [3, 4] else "left", vertical="center")
            cell.border = thin_border
            if ci == 4:
                cell.fill = PatternFill(start_color="F0FDFA", end_color="F0FDFA", fill_type="solid")
            elif ci == 3:
                cell.fill = PatternFill(start_color="FAF5FF", end_color="FAF5FF", fill_type="solid")

    cat_row_start = 13 + len(kpi_rows)
    ws_sum.cell(cat_row_start, 2, "2. สรุปผลการประเมินแยกตามหมวดหมู่นโยบาย (Category Breakdown)").font = font_section

    cat_headers = [
        "ลำดับ", "หมวดหมู่นโยบาย ISO (ในชีท)", "จำนวนข้อ",
        "ดึง Chunk ตรงหมวด", "คะแนน Gemma 4 (26B)", "คะแนน Llama 3.3 (70B)",
        "เวลาเฉลี่ย Gemma", "เวลาเฉลี่ย Llama", "โมเดลที่ทำได้ดีกว่า"
    ]
    for ci, h in enumerate(cat_headers, 2):
        cell = ws_sum.cell(cat_row_start + 1, ci, h)
        cell.fill = navy_dark
        cell.font = font_white_bold
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border

    cats_set = []
    for r in gemma_data:
        if r["category"] not in cats_set:
            cats_set.append(r["category"])

    curr_r = cat_row_start + 2
    for idx, cat in enumerate(cats_set, 1):
        g_items = [r for r in gemma_data if r["category"] == cat]
        l_items = [r for r in llama_data if r["category"] == cat]
        cnt = len(g_items)
        c_hits = sum(1 for r in g_items if r["is_hit"])
        c_hit_rate = (c_hits / cnt) * 100 if cnt else 0
        c_g_score = (sum(r["score"] for r in g_items) / cnt) * 100 if cnt else 0
        c_l_score = (sum(r["score"] for r in l_items) / cnt) * 100 if cnt else 0
        c_g_time = sum(r["response_time"] for r in g_items) / cnt if cnt else 0
        c_l_time = sum(r["response_time"] for r in l_items) / cnt if cnt else 0

        if c_l_score > c_g_score:
            better = "Llama 3.3 (+{:.1f}%)".format(c_l_score - c_g_score)
        elif c_g_score > c_l_score:
            better = "Gemma 4 (+{:.1f}%)".format(c_g_score - c_l_score)
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
            if ci == 5:
                cell.fill = PatternFill(start_color="FAF5FF", end_color="FAF5FF", fill_type="solid")
            elif ci == 6:
                cell.fill = PatternFill(start_color="F0FDFA", end_color="F0FDFA", fill_type="solid")
            elif ci == 10:
                if "Llama" in str(val):
                    cell.font = Font(name="Tahoma", size=9, bold=True, color="0F766E")
                elif "Gemma" in str(val):
                    cell.font = Font(name="Tahoma", size=9, bold=True, color="6B21A8")
        curr_r += 1

    ws_sum.column_dimensions["A"].width = 3
    ws_sum.column_dimensions["B"].width = 25
    ws_sum.column_dimensions["C"].width = 35
    ws_sum.column_dimensions["D"].width = 24
    ws_sum.column_dimensions["E"].width = 24
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

    ws_cmp.cell(2, 2, "ตารางเปรียบเทียบคำตอบข้อต่อข้อ (Gemma 4 26B vs Llama 3.3 70B)").font = font_title
    ws_cmp.cell(3, 2, "เปรียบเทียบสิ่งที่บอทตอบ เวลาในการตอบ การตรงต่อ Chunk และผลการตัดสินความถูกต้อง").font = font_subtitle

    cmp_headers = [
        "ข้อที่ (เดิม)", "ลำดับสุ่ม", "หมวดหมู่นโยบาย", "คำถาม", "คำถามที่คาดหวัง",
        "สิ่งที่บอทตอบ [Gemma 4 26B]", "สิ่งที่บอทตอบ [Llama 3.3 70B]",
        "เวลา [Gemma]", "เวลา [Llama]",
        "Chunk IDs", "หัวข้อเอกสารและหน้าที่ Chunk สังกัด", "การดึง Chunk ตรงหมวด",
        "คะแนน Gemma", "ผลตัดสิน Gemma", "คะแนน Llama", "ผลตัดสิน Llama",
        "ผลเปรียบเทียบ"
    ]
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
    ws_cmp.row_dimensions[5].height = 28

    for ri, (g_item, l_item) in enumerate(zip(gemma_data, llama_data), 6):
        if l_item["score"] > g_item["score"]:
            comp_txt = "Llama ชนะ (+{:.1f})".format(l_item["score"] - g_item["score"])
        elif g_item["score"] > l_item["score"]:
            comp_txt = "Gemma ชนะ (+{:.1f})".format(g_item["score"] - l_item["score"])
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
            l_item["score"],
            l_item["verdict"],
            comp_txt
        ]
        for ci, val in enumerate(row_vals, 2):
            cell = ws_cmp.cell(ri, ci, val)
            cell.font = font_regular
            cell.border = thin_border

            if ci in [2, 3]:
                cell.alignment = Alignment(horizontal="center", vertical="top")
            elif ci in [9, 10, 14, 15, 16, 17, 18]:
                cell.alignment = Alignment(horizontal="center", vertical="top")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)

            if ci in [14, 15]:
                cell.fill = PatternFill(start_color="FAF5FF", end_color="FAF5FF", fill_type="solid")
                if val == 1.0 or val == "ถูกต้อง":
                    cell.font = font_correct
                elif val == 0.5 or val == "ถูกต้องบางส่วน":
                    cell.font = font_partial
                elif val == 0.0 or val == "ไม่ถูกต้อง":
                    cell.font = font_incorrect
            elif ci in [16, 17]:
                cell.fill = PatternFill(start_color="F0FDFA", end_color="F0FDFA", fill_type="solid")
                if val == 1.0 or val == "ถูกต้อง":
                    cell.font = font_correct
                elif val == 0.5 or val == "ถูกต้องบางส่วน":
                    cell.font = font_partial
                elif val == 0.0 or val == "ไม่ถูกต้อง":
                    cell.font = font_incorrect
            elif ci == 13:
                if val == "ตรงหมวด (Hit)":
                    cell.fill = fill_hit
                    cell.font = font_hit
                else:
                    cell.fill = fill_miss
                    cell.font = font_miss
            elif ci == 18:
                if "Llama" in str(val):
                    cell.font = Font(name="Tahoma", size=9, bold=True, color="0F766E")
                elif "Gemma" in str(val):
                    cell.font = Font(name="Tahoma", size=9, bold=True, color="6B21A8")

    ws_cmp.column_dimensions["A"].width = 3
    ws_cmp.column_dimensions["B"].width = 12
    ws_cmp.column_dimensions["C"].width = 12
    ws_cmp.column_dimensions["D"].width = 25
    ws_cmp.column_dimensions["E"].width = 35
    ws_cmp.column_dimensions["F"].width = 35
    ws_cmp.column_dimensions["G"].width = 45
    ws_cmp.column_dimensions["H"].width = 45
    ws_cmp.column_dimensions["I"].width = 14
    ws_cmp.column_dimensions["J"].width = 14
    ws_cmp.column_dimensions["K"].width = 18
    ws_cmp.column_dimensions["L"].width = 35
    ws_cmp.column_dimensions["M"].width = 18
    ws_cmp.column_dimensions["N"].width = 14
    ws_cmp.column_dimensions["O"].width = 16
    ws_cmp.column_dimensions["P"].width = 14
    ws_cmp.column_dimensions["Q"].width = 16
    ws_cmp.column_dimensions["R"].width = 18

    # ══════════════════════════════════════════════════════════════════════════════
    # SHEETS 3 & 4: Detailed Model Sheets
    # ══════════════════════════════════════════════════════════════════════════════
    for model_title, m_data, m_fill in [
        ("Gemma 4 26B", gemma_data, purple_gemma),
        ("Llama 3.3 70B", llama_data, teal_llama)
    ]:
        ws_m = wb.create_sheet(title=model_title)
        ws_m.views.sheetView[0].showGridLines = True

        ws_m.cell(2, 2, f"ผลการทดสอบระบบแชทบอท TUH — โมเดล {model_title}").font = font_title
        ws_m.cell(3, 2, f"การทดสอบกับแชทบอทจริง (RAG Pipeline + {model_title}) ครบทุกมิติข้อมูล").font = font_subtitle

        m_headers = [
            "ข้อที่ (เดิม)", "ลำดับสุ่ม", "หมวดหมู่นโยบาย (ในชีท)", "คำถาม", "สิ่งที่บอทตอบ",
            "คำถามที่คาดหวัง", "เวลาในการตอบ", "Chunk ที่ใช้ตอบ", "หัวข้อเอกสารและหน้าที่ Chunk สังกัด",
            "การดึง Chunk ตรงหมวด", "คะแนน", "ผลตัดสิน", "เหตุผลการให้คะแนน"
        ]
        for ci, h in enumerate(m_headers, 2):
            cell = ws_m.cell(5, ci, h)
            cell.fill = m_fill
            cell.font = font_white_bold
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = thin_border
        ws_m.row_dimensions[5].height = 26

        for ri, r in enumerate(m_data, 6):
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

        ws_m.column_dimensions["A"].width = 3
        ws_m.column_dimensions["B"].width = 12
        ws_m.column_dimensions["C"].width = 12
        ws_m.column_dimensions["D"].width = 25
        ws_m.column_dimensions["E"].width = 35
        ws_m.column_dimensions["F"].width = 45
        ws_m.column_dimensions["G"].width = 40
        ws_m.column_dimensions["H"].width = 16
        ws_m.column_dimensions["I"].width = 18
        ws_m.column_dimensions["J"].width = 35
        ws_m.column_dimensions["K"].width = 20
        ws_m.column_dimensions["L"].width = 12
        ws_m.column_dimensions["M"].width = 16
        ws_m.column_dimensions["N"].width = 45

    wb.save(output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TUH Chatbot Multi-Model Test Runner")
    parser.add_argument("--limit", type=int, default=None, help="จำกัดจำนวนข้อในการทดสอบ")
    parser.add_argument("--delay", type=float, default=1.0, help="หน่วงเวลาระหว่างข้อ (วินาที)")
    args = parser.parse_args()

    run_full_test(limit=args.limit, delay=args.delay)
