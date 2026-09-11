"""
RAG Answer Quality Eval — Human Review

ยิงคำถามทุกข้อใน golden_qa.csv เข้า /api/chat จริง แล้วสร้างรายงานให้คนอ่านเทียบเอง
(ไม่ตัดสิน ถูก/ผิด อัตโนมัติ — ตามที่เลือกไว้ว่าจะใช้ human review)

Prerequisite: server ต้องรันอยู่จริง (ปกติ python -m uvicorn app.main:app จาก Backend/
หรือ TestPFM/mock_server.py ถ้าจะดูแค่ retrieval โดยไม่ผ่าน LLM จริง)

รัน:
    python TestPFM/eval/run_eval.py --host http://localhost:8000
    python TestPFM/eval/run_eval.py --host http://localhost:8001   # เทียบกับ mock (LLM stub)

Output (ใน TestPFM/eval/results/<timestamp>/):
    report.html   — เปิดดูใน browser อ่านเทียบคำถาม/expected/actual ทีละคู่ ง่ายสุด
    report.csv    — เปิดใน Excel มีคอลัมน์ reviewer_verdict/reviewer_notes ว่างไว้ให้กรอกเอง
    raw.json      — ผลดิบทั้งหมด (answer, citations, used_rag, response_time, model)
"""
import argparse
import csv
import html
import json
import time
from datetime import datetime
from pathlib import Path

import requests

EVAL_DIR = Path(__file__).resolve().parent
GOLDEN_PATH = EVAL_DIR / "golden_qa.json"


def load_golden(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def ask(host: str, question: str, timeout: int = 60):
    t0 = time.time()
    try:
        resp = requests.post(f"{host}/api/chat", json={"query": question}, timeout=timeout)
        elapsed = time.time() - t0
        if resp.status_code != 200:
            return {"error": f"HTTP {resp.status_code}: {resp.text[:300]}", "elapsed": elapsed}
        body = resp.json()
        return {
            "answer": body.get("answer", ""),
            "used_rag": body.get("used_rag"),
            "model": body.get("model"),
            "response_time": body.get("response_time"),
            "citations": [c.get("source") for c in body.get("citations", [])],
            "elapsed": elapsed,
            "error": None,
        }
    except Exception as e:
        return {"error": str(e), "elapsed": time.time() - t0}


def run(host: str, golden: list, out_dir: Path):
    results = []
    total = len(golden)
    for i, item in enumerate(golden, 1):
        print(f"[{i}/{total}] {item['id']}: {item['question'][:50]}...")
        r = ask(host, item["question"])
        results.append({**item, **r})

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "raw.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    write_csv(results, out_dir / "report.csv")
    write_html(results, out_dir / "report.html", host)
    return results


def write_csv(results, path: Path):
    fields = [
        "id", "category", "question", "expected_answer", "answer",
        "used_rag", "model", "response_time", "citations", "error",
        "reviewer_verdict", "reviewer_notes",
    ]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in results:
            row = {k: r.get(k, "") for k in fields}
            row["citations"] = ", ".join(r.get("citations") or [])
            row["reviewer_verdict"] = ""  # กรอกเอง: ถูก / บางส่วน / ผิด
            row["reviewer_notes"] = ""
            writer.writerow(row)


def write_html(results, path: Path, host: str):
    rows_html = []
    for r in results:
        error_badge = f'<span class="badge err">ERROR: {html.escape(r["error"])}</span>' if r.get("error") else ""
        used_rag_badge = (
            '<span class="badge rag">RAG</span>' if r.get("used_rag")
            else '<span class="badge norag">no-RAG</span>'
        )
        citations = ", ".join(r.get("citations") or []) or "—"
        rows_html.append(f"""
        <section class="card">
          <div class="meta">
            <span class="id">{html.escape(r['id'])}</span>
            <span class="cat">{html.escape(r['category'])}</span>
            {used_rag_badge}
            <span class="badge model">{html.escape(str(r.get('model') or '—'))}</span>
            <span class="badge time">{r.get('response_time', r.get('elapsed', '?'))}s</span>
            {error_badge}
          </div>
          <div class="q">Q: {html.escape(r['question'])}</div>
          <div class="cols">
            <div class="col expected">
              <h4>Expected</h4>
              <p>{html.escape(r['expected_answer']).replace(chr(10), '<br>')}</p>
            </div>
            <div class="col actual">
              <h4>Actual (จากแชทบอท)</h4>
              <p>{html.escape(r.get('answer') or '').replace(chr(10), '<br>')}</p>
              <p class="cite">อ้างอิง: {html.escape(citations)}</p>
            </div>
          </div>
          <div class="verdict">
            คำตัดสิน:
            <label><input type="radio" name="v-{html.escape(r['id'])}"> ถูก</label>
            <label><input type="radio" name="v-{html.escape(r['id'])}"> บางส่วน</label>
            <label><input type="radio" name="v-{html.escape(r['id'])}"> ผิด</label>
          </div>
        </section>
        """)

    doc = f"""<!doctype html>
<html lang="th"><head><meta charset="utf-8">
<title>RAG Eval Report</title>
<style>
  body {{ font-family: 'Tahoma', sans-serif; background:#f7f7f9; margin:0; padding:24px; color:#1a1a1a; }}
  h1 {{ font-size:20px; }}
  .sub {{ color:#666; margin-bottom:24px; }}
  .card {{ background:#fff; border:1px solid #e2e2e6; border-radius:8px; padding:16px 20px; margin-bottom:16px; }}
  .meta {{ display:flex; gap:8px; align-items:center; margin-bottom:8px; flex-wrap:wrap; }}
  .id {{ font-weight:bold; color:#555; }}
  .cat {{ color:#888; font-size:13px; }}
  .badge {{ font-size:12px; padding:2px 8px; border-radius:10px; background:#eee; }}
  .badge.rag {{ background:#dff5e1; color:#1a7f37; }}
  .badge.norag {{ background:#f0f0f0; color:#666; }}
  .badge.err {{ background:#fde2e2; color:#c0392b; }}
  .badge.model {{ background:#e8eefc; color:#2955c9; }}
  .badge.time {{ background:#fff3d6; color:#8a6100; }}
  .q {{ font-weight:600; margin:8px 0 12px; }}
  .cols {{ display:flex; gap:16px; }}
  .col {{ flex:1; background:#fafafa; border-radius:6px; padding:10px 12px; }}
  .col h4 {{ margin:0 0 6px; font-size:12px; text-transform:uppercase; color:#999; }}
  .col.expected {{ border-left:3px solid #2955c9; }}
  .col.actual {{ border-left:3px solid #1a7f37; }}
  .cite {{ font-size:12px; color:#888; margin-top:8px; }}
  .verdict {{ margin-top:12px; font-size:13px; color:#555; }}
  .verdict label {{ margin-right:12px; }}
  @media (max-width: 800px) {{ .cols {{ flex-direction:column; }} }}
</style>
</head><body>
<h1>RAG Answer Quality — Eval Report</h1>
<div class="sub">host: {html.escape(host)} · generated: {datetime.now().isoformat(timespec='seconds')} · {len(results)} คำถาม</div>
{''.join(rows_html)}
</body></html>"""
    path.write_text(doc, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="RAG answer quality eval (human review)")
    parser.add_argument("--host", default="http://localhost:8000")
    parser.add_argument("--golden", default=str(GOLDEN_PATH))
    args = parser.parse_args()

    golden = load_golden(Path(args.golden))
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = EVAL_DIR / "results" / stamp

    results = run(args.host, golden, out_dir)

    errors = sum(1 for r in results if r.get("error"))
    print(f"\nเสร็จแล้ว: {len(results)} คำถาม ({errors} error)")
    print(f"เปิดดูรายงาน: {out_dir / 'report.html'}")
    print(f"กรอกคำตัดสินใน Excel: {out_dir / 'report.csv'}")


if __name__ == "__main__":
    main()
