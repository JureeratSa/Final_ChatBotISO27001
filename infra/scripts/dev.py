"""
รันระบบแบบ dev (ต้องปิด Docker ก่อน เพราะใช้ port เดียวกัน)

    python infra/scripts/dev.py api      Backend API  → http://localhost:8000
    python infra/scripts/dev.py chat     แชทบอท       → http://localhost:5173
    python infra/scripts/dev.py admin    ระบบแอดมิน   → http://localhost:5174

เว็บ (chat/admin): Vite รันจากไดรฟ์เครือข่าย (Z:) ไม่ได้ สคริปต์จึงคัดลอกโค้ดไปไว้ที่ ~/tuh-<ชื่อเว็บ>
แล้วรัน dev server จากที่นั่น — ระหว่างรันจะคอยคัดลอกไฟล์ที่แก้ใน src/ ไปให้ทุก 0.5 วินาที
(แก้โค้ดใน repo ตามปกติ ไม่ต้องแก้ในโฟลเดอร์สำเนา)
"""
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2]
WEB_APPS = {
    # ชื่อ: (โฟลเดอร์ใน repo, โฟลเดอร์สำเนาบน C:, port)
    "chat": ("apps/chat-web", "tuh-user-web", 5173),
    "admin": ("apps/admin-web", "tuh-admin-web", 5174),
}
ROOT_FILES = ["package.json", "package-lock.json", "vite.config.js", "tailwind.config.js",
              "postcss.config.js", "index.html"]


def run_api() -> None:
    import asyncio
    import uvicorn

    os.chdir(PROJECT_DIR / "services" / "api")
    sys.path.insert(0, os.getcwd())
    if sys.platform == "win32":
        # aiomysql + SSL ใช้กับ event loop แบบ Proactor (ค่าเริ่มต้นของ Windows) ไม่ได้
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    print("Backend API → http://localhost:8000")
    server = uvicorn.Server(uvicorn.Config("app.main:app", host="0.0.0.0", port=8000, loop="asyncio"))
    asyncio.run(server.serve())


def _copy_if_newer(src: Path, dest: Path) -> bool:
    if dest.exists() and src.stat().st_mtime <= dest.stat().st_mtime:
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(f".{dest.name}.tmp")
    shutil.copy2(src, tmp)
    os.replace(tmp, dest)       # เขียนทับทีเดียว Vite จะไม่อ่านเจอไฟล์ครึ่งๆ
    return True


def _sync(src_dir: Path, dest_dir: Path) -> None:
    for name in ROOT_FILES:
        if (src_dir / name).exists():
            _copy_if_newer(src_dir / name, dest_dir / name)
    for src in (src_dir / "src").rglob("*"):
        if src.is_dir() or src.name.startswith((".", "~")) or ".tmp" in src.name:
            continue
        dest = dest_dir / src.relative_to(src_dir)
        try:
            if _copy_if_newer(src, dest):
                print(f"[sync] {dest.relative_to(dest_dir)}")
        except OSError as e:
            print(f"[sync] คัดลอก {src.name} ไม่สำเร็จ: {e}")


def run_web(name: str) -> None:
    folder, mirror_name, port = WEB_APPS[name]
    src_dir, dest_dir = PROJECT_DIR / folder, Path.home() / mirror_name
    print(f"คัดลอก {src_dir} → {dest_dir}")
    _sync(src_dir, dest_dir)
    if not (dest_dir / "node_modules").exists():
        subprocess.run("npm install", cwd=dest_dir, shell=True, check=True)

    server = subprocess.Popen(f"npm run dev -- --force --port {port}", cwd=dest_dir, shell=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8")
    threading.Thread(target=lambda: [print(line, end="") for line in server.stdout], daemon=True).start()
    print(f"{name} → http://localhost:{port}  (Ctrl+C เพื่อหยุด)")
    try:
        while server.poll() is None:
            time.sleep(0.5)
            _sync(src_dir, dest_dir)
    except KeyboardInterrupt:
        subprocess.run(f"taskkill /F /T /PID {server.pid}", shell=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    target = sys.argv[1] if len(sys.argv) > 1 else ""
    if target == "api":
        run_api()
    elif target in WEB_APPS:
        run_web(target)
    else:
        sys.exit(__doc__)
