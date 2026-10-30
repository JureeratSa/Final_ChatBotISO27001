"""
TUH Chatbot AI — คัดลอกข้อมูลเดิมบนเครื่องนี้เข้า Docker volume (ทำครั้งเดียวตอนย้ายมา Docker)
รัน: python docker/seed_volumes.py   (ต้อง `docker compose build` ก่อน และ backend container ต้องหยุดอยู่)

คัดลอก:
  uploads/                    → volume uploads       (PDF + cache สกัดข้อความ/OCR — ไม่ต้อง OCR ใหม่)
  index_db/bm25.pkl           → volume index_db
  CHROMA_DB_DIR (Backend/.env) → volume chroma        (ต้องเป็นชุดเดียวกับ bm25.pkl)
  HuggingFace cache bge-m3    → volume model_cache   (ไม่ต้องดาวน์โหลดโมเดล ~2 GB ใหม่)
ใช้ `docker cp` จึงอ่านจากไดรฟ์ Z: ได้ (docker mount network drive ตรงๆ ไม่ได้)
ไม่อยากคัดลอกดัชนีเดิม: ข้าม chroma/index_db แล้วสั่ง rebuild จาก AdminWeb แทนก็ได้ (--skip-index)
"""
import os
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "tuh-chatbot"          # ตรงกับ name: ใน docker-compose.yml → volume ชื่อ tuh-chatbot_<ชื่อ>
HELPER = "tuh-chatbot-seed"
APP_UID = "1000:1000"            # user app ใน backend.Dockerfile


def run(*cmd, check=True):
    print("  $", " ".join(cmd))
    return subprocess.run(cmd, check=check)


def chroma_source() -> Path:
    path = os.getenv("CHROMA_DB_DIR")
    if not path:
        env_file = ROOT / "Backend" / ".env"
        for line in env_file.read_text(encoding="utf-8").splitlines() if env_file.exists() else []:
            if line.strip().startswith("CHROMA_DB_DIR="):
                path = line.split("=", 1)[1].strip().strip('"').strip("'")
    return Path(path) if path else ROOT / "index_db" / "chroma_db"


def main():
    skip_index = "--skip-index" in sys.argv
    hf_hub = Path(os.getenv("HF_HOME", Path.home() / ".cache" / "huggingface")) / "hub"
    copies = [
        (ROOT / "uploads", "uploads", "/v/uploads"),
        (hf_hub / "models--BAAI--bge-m3", "model_cache", "/v/model_cache/huggingface/hub"),
    ]
    if not skip_index:
        copies += [
            (ROOT / "index_db" / "bm25.pkl", "index_db", "/v/index_db"),
            (chroma_source(), "chroma", "/v/chroma"),
        ]

    missing = [str(src) for src, _, _ in copies if not src.exists()]
    if missing:
        print("❌ ไม่พบ:", *missing, sep="\n   ")
        sys.exit(1)

    volumes = sorted({vol for _, vol, _ in copies})
    mounts = []
    for vol in volumes:
        # ใส่ label ของ compose — ไม่งั้น docker compose เตือน "volume already exists but was not created by Docker Compose" ทุกครั้ง
        run("docker", "volume", "create", "--label", f"com.docker.compose.project={PROJECT}",
            "--label", f"com.docker.compose.volume={vol}", f"{PROJECT}_{vol}")
        mounts += ["-v", f"{PROJECT}_{vol}:/v/{vol}"]
    run("docker", "rm", "-f", HELPER, check=False)
    # สร้างโฟลเดอร์ปลายทางก่อน — docker cp ไปยัง path ที่ยังไม่มีจะ "เปลี่ยนชื่อ" โฟลเดอร์แทนการวางไว้ข้างใน
    run("docker", "run", "-d", "--name", HELPER, *mounts, "alpine:3.20", "sh", "-c",
        "mkdir -p " + " ".join(sorted({d for _, _, d in copies})) + " && sleep 3600")
    try:
        for src, _, dest in copies:
            print(f"📦 {src} → {dest}")
            if dest in ("/v/uploads", "/v/chroma"):
                run("docker", "cp", f"{src}{os.sep}.", f"{HELPER}:{dest}")  # เนื้อหาในโฟลเดอร์
            else:
                run("docker", "cp", str(src), f"{HELPER}:{dest}")           # วางทั้งไฟล์/โฟลเดอร์ไว้ข้างใน
        # docker cp เขียนไฟล์เป็น root — ให้ user app ใน backend เขียนต่อได้ (rebuild/อัปโหลด)
        run("docker", "exec", HELPER, "chown", "-R", APP_UID, "/v")
    finally:
        run("docker", "rm", "-f", HELPER, check=False)
    print("✅ คัดลอกเข้า volume แล้ว — docker compose up -d")


if __name__ == "__main__":
    main()
