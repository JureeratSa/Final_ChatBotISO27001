"""
Stress Test Sweep — หา Breaking Point อัตโนมัติ

รัน locust แบบ headless ไล่ concurrency ขึ้นทีละระดับ (10 -> 25 -> 50 -> 100 -> ...)
เก็บผล p95/p99/error-rate ของแต่ละระดับมาสรุปเป็นตารางเดียว เพื่อตอบคำถาม
"รับโหลดพร้อมกันได้แค่ไหนก่อนเริ่มพัง"

ใช้:
    python TestPFM/run_stress_sweep.py --locustfile TestPFM/locustfile_retrieval.py --host http://localhost:8001
    python TestPFM/run_stress_sweep.py --locustfile TestPFM/locustfile_full.py --host http://localhost:8000 --levels 5,10,20 --duration 30

ผลลัพธ์ราย level เก็บเป็น CSV ไว้ที่ TestPFM/results/u<N>_stats.csv (ของ locust เอง)
"""
import argparse
import csv
import subprocess
import sys
from pathlib import Path

DEFAULT_LEVELS = [10, 25, 50, 100, 150, 200]
RESULTS_DIR = Path(__file__).resolve().parent / "results"


def run_level(locustfile: str, host: str, users: int, duration: int) -> Path:
    RESULTS_DIR.mkdir(exist_ok=True)
    prefix = RESULTS_DIR / f"u{users}"
    cmd = [
        sys.executable, "-m", "locust",
        "-f", locustfile,
        "--host", host,
        "--headless",
        "-u", str(users),
        "-r", str(max(1, users // 10)),
        "-t", f"{duration}s",
        "--csv", str(prefix),
        "--only-summary",
    ]
    print(f"\n[Sweep] concurrency={users} users, duration={duration}s ...")
    subprocess.run(cmd, check=False)
    return Path(f"{prefix}_stats.csv")


def parse_stats(csv_path: Path):
    if not csv_path.exists():
        print(f"  (ไม่พบ {csv_path.name} — locust อาจ error ก่อน generate CSV)")
        return None
    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    agg = next((r for r in rows if r["Name"] == "Aggregated"), None)
    if not agg:
        return None
    requests = int(agg["Request Count"])
    failures = int(agg["Failure Count"])
    return {
        "requests": requests,
        "failures": failures,
        "fail_pct": (failures / requests * 100) if requests else 0.0,
        "rps": agg.get("Requests/s", "?"),
        "p95_ms": agg.get("95%", "?"),
        "p99_ms": agg.get("99%", "?"),
    }


def main():
    parser = argparse.ArgumentParser(description="Stress test sweep — หา breaking point")
    parser.add_argument("--locustfile", required=True, help="เช่น TestPFM/locustfile_retrieval.py")
    parser.add_argument("--host", required=True, help="เช่น http://localhost:8001")
    parser.add_argument("--levels", default=",".join(map(str, DEFAULT_LEVELS)),
                         help="รายการ concurrency คั่นด้วย , (ดีฟอลต์: 10,25,50,100,150,200)")
    parser.add_argument("--duration", type=int, default=60, help="วินาทีที่รันต่อ 1 ระดับ (ดีฟอลต์: 60)")
    args = parser.parse_args()

    levels = [int(x) for x in args.levels.split(",")]
    summary = []

    for users in levels:
        stats_csv = run_level(args.locustfile, args.host, users, args.duration)
        stats = parse_stats(stats_csv)
        if stats:
            stats["users"] = users
            summary.append(stats)
            print(f"  -> rps={stats['rps']} p95={stats['p95_ms']}ms p99={stats['p99_ms']}ms "
                  f"fail={stats['fail_pct']:.1f}%")

    print("\n" + "=" * 66)
    print(f"{'Users':<8}{'RPS':<10}{'p95(ms)':<10}{'p99(ms)':<10}{'Fail%':<8}")
    print("=" * 66)
    for s in summary:
        print(f"{s['users']:<8}{s['rps']:<10}{s['p95_ms']:<10}{s['p99_ms']:<10}{s['fail_pct']:<8.1f}")
    print("=" * 66)
    print("อ่านผล: หา users ที่ p95/p99 เริ่มพุ่งขึ้นแบบไม่เป็นเส้นตรง หรือ Fail% เริ่ม > 0")
    print("        นั่นคือ breaking point โดยประมาณของ pipeline ที่เทสอยู่")


if __name__ == "__main__":
    main()
