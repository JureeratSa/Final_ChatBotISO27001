# """
# TUH Chatbot AI — Deploy UserWeb / AdminWeb ขึ้น XAMPP
# ทำหน้าที่: คัดลอกโค้ดไป build บนไดรฟ์ C: (build บน network drive Z: ไม่ได้ เพราะ path มีช่องว่าง)
#           สำรองเวอร์ชันเดิมใน htdocs แล้ววางไฟล์ที่ build ใหม่แทน
# รัน: python deploy_xampp.py admin | user | all
# ระหว่างแก้โค้ดให้ใช้ run_admin_web.py / run_user_web.py (dev server) แล้วค่อยรันสคริปต์นี้ตอนพร้อมขึ้น XAMPP
# """
import os
import shutil
import subprocess
import sys
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

base_dir = os.path.dirname(os.path.abspath(__file__))
htdocs_app = r"C:\xampp\htdocs\tuh_chatbot_ai"
# เก็บ backup นอก htdocs เพื่อไม่ให้ Apache เสิร์ฟไฟล์เก่าออกไป
backup_root = r"C:\xampp\tuh_backups"
build_root = r"C:\Users\ITS\tuh-xampp-build"

TARGETS = {
    "user": {
        "src": os.path.join(base_dir, "UserWeb"),
        "base": "/tuh_chatbot_ai/",
        "out": htdocs_app,
        # UserWeb อยู่ที่ root ของแอป — ห้ามลบโฟลเดอร์ admin/ ที่ซ้อนอยู่ข้างใน
        "keep": {"admin"},
    },
    "admin": {
        "src": os.path.join(base_dir, "AdminWeb"),
        "base": "/tuh_chatbot_ai/admin/",
        "out": os.path.join(htdocs_app, "admin"),
        "keep": set(),
    },
}


def run(cmd, cwd):
    print(f"  > {cmd}")
    result = subprocess.run(cmd, cwd=cwd, shell=True)
    if result.returncode != 0:
        sys.exit(f"❌ คำสั่งล้มเหลว (exit {result.returncode}): {cmd}")


def deploy(name):
    cfg = TARGETS[name]
    build_dir = os.path.join(build_root, name)
    print(f"\n🚀 Deploy {name} → {cfg['out']}")

    # 1) Mirror โค้ดไป C: — ไม่เอา node_modules/dist จาก Z: (คัดลอกข้ามไดรฟ์แล้วใช้ไม่ได้)
    print("1/4 คัดลอกโค้ดไป build บนไดรฟ์ C:")
    os.makedirs(build_dir, exist_ok=True)
    rc = subprocess.run(
        ["robocopy", cfg["src"], build_dir, "/MIR", "/XD", "node_modules", "dist",
         "/NFL", "/NDL", "/NJH", "/NJS", "/NP"],
    ).returncode
    if rc >= 8:  # robocopy: 0-7 = สำเร็จ, 8 ขึ้นไป = มีไฟล์คัดลอกไม่สำเร็จ
        sys.exit(f"❌ robocopy ล้มเหลว (exit {rc})")

    # 2) ติดตั้ง package ครั้งแรก หรือเมื่อ package-lock.json เปลี่ยน
    lock = os.path.join(build_dir, "package-lock.json")
    stamp = os.path.join(build_dir, "node_modules", ".lock-mtime")
    lock_mtime = str(os.path.getmtime(lock)) if os.path.exists(lock) else ""
    if not os.path.exists(stamp) or open(stamp).read() != lock_mtime:
        print("2/4 ติดตั้ง package (npm ci)")
        run("npm ci --no-audit --no-fund", build_dir)
        with open(stamp, "w") as f:
            f.write(lock_mtime)
    else:
        print("2/4 package เป็นปัจจุบันแล้ว ข้าม npm ci")

    # 3) Build พร้อม --base ให้ตรงกับ subpath บน XAMPP
    print("3/4 Build")
    run(f"npm run build -- --base={cfg['base']}", build_dir)
    dist = os.path.join(build_dir, "dist")

    # 4) สำรองของเดิม แล้ววางของใหม่แทน
    print("4/4 สำรองเวอร์ชันเดิมแล้ววางไฟล์ใหม่ลง htdocs")
    out = cfg["out"]
    os.makedirs(out, exist_ok=True)
    backup = os.path.join(backup_root, f"{name}-{datetime.now():%Y%m%d-%H%M%S}")
    shutil.copytree(out, backup, ignore=shutil.ignore_patterns(*cfg["keep"]))
    for entry in os.listdir(out):
        if entry in cfg["keep"]:
            continue
        path = os.path.join(out, entry)
        shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)
    shutil.copytree(dist, out, dirs_exist_ok=True)

    print(f"✅ {name} ขึ้น XAMPP แล้ว — http://localhost:8080{cfg['base']} (กด Ctrl+F5 เพื่อโหลดใหม่)")
    print(f"   เวอร์ชันเดิมเก็บไว้ที่ {backup} (คัดลอกกลับไปวางใน {out} ได้ถ้าต้องการย้อน)")


if __name__ == "__main__":
    choice = sys.argv[1] if len(sys.argv) > 1 else ""
    names = list(TARGETS) if choice == "all" else [choice]
    if not all(n in TARGETS for n in names):
        sys.exit("วิธีใช้: python deploy_xampp.py admin | user | all")
    for n in names:
        deploy(n)
