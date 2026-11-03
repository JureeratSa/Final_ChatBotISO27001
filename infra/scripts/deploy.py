"""
Deploy ขึ้น production (Docker) คำสั่งเดียว — รันบนเครื่องเซิร์ฟเวอร์ที่โฟลเดอร์ repo

    python infra/scripts/deploy.py            ดึงโค้ดล่าสุด → ตรวจ → build → สลับ → ตรวจสุขภาพ (พังแล้วย้อนกลับให้เอง)
    python infra/scripts/deploy.py --check    ทำถึงขั้น build + ตรวจ migration แต่ไม่สลับของที่รันอยู่ (ซ้อมได้ทุกเมื่อ)
    python infra/scripts/deploy.py --no-pull  ใช้โค้ดที่อยู่ในโฟลเดอร์ตอนนี้ ไม่ git pull

ขั้นตอน (ล้มขั้นไหน หยุดทันที — ก่อนขั้นที่ 6 ระบบที่รันอยู่ไม่ถูกแตะเลย):
  1. โฟลเดอร์ต้องไม่มีไฟล์ที่ track แล้วถูกแก้ค้างไว้
  2. git pull --ff-only branch ปัจจุบัน (ปกติคือ main)
  3. ตรวจ migration แตะเฉพาะตารางของแชทบอท (check_migrations.py)
  4. จำ image ที่รันอยู่ไว้เป็น :rollback แล้ว docker compose build
  5. ฐานข้อมูลต้องอยู่ที่ migration ล่าสุดแล้ว (alembic current) — ถ้ามี migration ใหม่ ให้ตรวจไฟล์แล้วรัน
     `docker compose run --rm backend alembic upgrade head` เองก่อน (ไม่รันอัตโนมัติ เพราะฐานข้อมูลใช้ร่วมกับระบบอื่น)
  6. docker compose up -d → รอทุก container healthy + /api/health ตอบ 200
  7. ไม่ผ่าน → ย้อนกลับไปใช้ image :rollback (ฐานข้อมูลไม่ถูกแก้ จึงย้อนได้ทันที)
ผลทุกครั้งบันทึกต่อท้าย ~/tuh-deploy-history.log (เวลา, commit, ผล)
"""
import argparse
import json
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2]
PROJECT = "tuh-chatbot"                      # name: ใน docker-compose.yml
BUILT_SERVICES = ["backend", "userweb", "adminweb"]
ALL_SERVICES = BUILT_SERVICES + ["proxy"]
HEALTH_URL = "http://127.0.0.1:8000/api/health"
HEALTH_TIMEOUT = 360                         # backend โหลดโมเดล bge-m3 ตอนเริ่ม ใช้ราว 1–2 นาที
HISTORY_FILE = Path.home() / "tuh-deploy-history.log"
# git บนไดรฟ์เครือข่าย (Z:) ทำ maintenance/gc แล้ว error — ปิดไว้
GIT = ["git", "-c", "maintenance.auto=false", "-c", "gc.auto=0"]


class DeployError(Exception):
    pass


def run(cmd: list[str], check: bool = True) -> str:
    print(f"  $ {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd, cwd=PROJECT_DIR, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and result.returncode != 0:
        raise DeployError(f"คำสั่งล้ม: {' '.join(cmd)}\n{result.stdout}{result.stderr}".rstrip())
    return result.stdout.strip()


def step(title: str) -> None:
    print(f"\n▶ {title}", flush=True)


def container_id(service: str) -> str:
    return run(["docker", "compose", "ps", "-q", service], check=False)


def remember_running_images() -> None:
    """ติดป้าย :rollback ให้ image ที่ container ใช้อยู่จริง (ไม่ใช่ :latest — อาจถูก build ใหม่ไว้แต่ยังไม่ได้สลับ)"""
    for service in BUILT_SERVICES:
        cid = container_id(service)
        if not cid:
            print(f"  {service}: ไม่ได้รันอยู่ — ไม่มีของให้ย้อนกลับ")
            continue
        image_id = run(["docker", "inspect", "-f", "{{.Image}}", cid])
        try:
            run(["docker", "image", "tag", image_id, f"{PROJECT}-{service}:rollback"])
            continue
        except DeployError:
            pass
        # image ของ container ถูกลบไปแล้ว (build ใหม่ทับโดยไม่ได้สลับ — containerd ลบ image ที่ไม่มีชื่อทิ้ง)
        # → ใช้ :latest ก่อน build รอบนี้เป็นจุดย้อนกลับแทน
        print(f"  ⚠ {service}: ไม่เหลือ image ที่รันอยู่ — ใช้ {PROJECT}-{service}:latest (ก่อน build) เป็นจุดย้อนกลับ")
        run(["docker", "image", "tag", f"{PROJECT}-{service}:latest", f"{PROJECT}-{service}:rollback"])


def wait_healthy() -> None:
    deadline = time.time() + HEALTH_TIMEOUT
    while True:
        states = {}
        for service in ALL_SERVICES:
            cid = container_id(service)
            info = json.loads(run(["docker", "inspect", cid], check=False) or "[{}]")[0] if cid else {}
            state = info.get("State", {})
            states[service] = state.get("Health", {}).get("Status") or state.get("Status", "missing")
        if any(s == "unhealthy" for s in states.values()):
            raise DeployError(f"container ไม่ผ่าน healthcheck: {states}")
        if all(s == "healthy" for s in states.values()):
            break
        if time.time() > deadline:
            raise DeployError(f"รอเกิน {HEALTH_TIMEOUT} วินาทีแล้วยังไม่พร้อม: {states}")
        print(f"  รอ... {states}", flush=True)
        time.sleep(10)
    with urllib.request.urlopen(HEALTH_URL, timeout=10) as resp:
        if resp.status != 200:
            raise DeployError(f"{HEALTH_URL} ตอบ {resp.status}")
    print(f"  ทุก container healthy และ {HEALTH_URL} ตอบ 200")


def rollback() -> None:
    step("ย้อนกลับไปใช้ image ก่อน deploy")
    for service in BUILT_SERVICES:
        if run(["docker", "image", "ls", "-q", f"{PROJECT}-{service}:rollback"], check=False):
            run(["docker", "image", "tag", f"{PROJECT}-{service}:rollback", f"{PROJECT}-{service}:latest"])
    run(["docker", "compose", "up", "-d", "--no-build"])
    wait_healthy()


def record(commit: str, result: str) -> None:
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S}\t{commit}\t{result}\n"
    try:
        with HISTORY_FILE.open("a", encoding="utf-8") as f:
            f.write(line)
    except OSError as e:
        print(f"(บันทึกประวัติลง {HISTORY_FILE} ไม่ได้: {e})")


def deploy(args) -> str:
    step("1. ตรวจโฟลเดอร์ repo")
    branch = run(GIT + ["branch", "--show-current"])
    if dirty := run(GIT + ["status", "--porcelain", "--untracked-files=no"]):
        raise DeployError(f"มีไฟล์ที่แก้ค้างไว้ — commit หรือเก็บก่อน deploy:\n{dirty}")
    if branch != "main":
        print(f"  ⚠ อยู่ที่ branch '{branch}' ไม่ใช่ main")

    if not args.no_pull:
        step("2. ดึงโค้ดล่าสุด")
        run(GIT + ["pull", "--ff-only"])
    commit = run(GIT + ["log", "-1", "--format=%h %s"])
    print(f"  จะ deploy: {branch} @ {commit}")

    step("3. ตรวจ migration")
    print(run([sys.executable, "infra/scripts/check_migrations.py"]))

    step("4. build image ใหม่ (ระบบเดิมยังรันอยู่)")
    remember_running_images()
    run(["docker", "compose", "build"])

    step("5. ตรวจว่าฐานข้อมูลอยู่ที่ migration ล่าสุด (อ่าน alembic_version อย่างเดียว)")
    current = run(["docker", "compose", "run", "--rm", "--no-deps", "-T", "backend", "alembic", "current"])
    if "(head)" not in current:
        raise DeployError(
            f"ฐานข้อมูลยังไม่อยู่ที่ migration ล่าสุด ({current or 'ไม่มี'}) — ตรวจไฟล์ใน alembic/versions แล้วรัน\n"
            "  docker compose run --rm backend alembic upgrade head\nแล้ว deploy ใหม่"
        )
    print(f"  {current}")

    if args.check:
        return f"{commit} — ตรวจผ่าน (--check: ไม่ได้สลับ)"

    step("6. สลับไปใช้ image ใหม่")
    run(["docker", "compose", "up", "-d", "--no-build"])
    try:
        wait_healthy()
    except (DeployError, OSError) as e:
        print(f"\n❌ ระบบใหม่ไม่ผ่าน: {e}")
        try:
            rollback()
        except (DeployError, OSError) as e2:
            raise DeployError(f"ย้อนกลับไม่สำเร็จ — ต้องแก้มือทันที: {e2}") from e
        raise DeployError(
            f"deploy ไม่ผ่าน ย้อนกลับไปใช้ image เดิมแล้ว (ระบบใช้งานได้) — โค้ดในโฟลเดอร์ยังเป็น {commit}\n"
            "  ดูสาเหตุ: docker compose logs --tail 100 backend"
        ) from e
    return f"{commit} — สำเร็จ"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="ตรวจ + build อย่างเดียว ไม่สลับของที่รันอยู่")
    parser.add_argument("--no-pull", action="store_true", help="ไม่ git pull ใช้โค้ดในโฟลเดอร์ตอนนี้")
    args = parser.parse_args()
    started = time.time()
    try:
        result = deploy(args)
    except DeployError as e:
        print(f"\n❌ {e}")
        record(run(GIT + ["log", "-1", "--format=%h"], check=False), f"ล้ม: {str(e).splitlines()[0]}")
        return 1
    print(f"\n✅ {result} ({time.time() - started:.0f} วินาที)")
    record(result.split(" ", 1)[0], result.split(" — ", 1)[1])
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # console ของ Windows แสดงภาษาไทย/อีโมจิได้
    sys.exit(main())
