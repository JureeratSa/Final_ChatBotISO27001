"""
ลบไฟล์ใน uploads/ ที่ไม่มีเอกสารในตาราง documents แล้ว (ค้างจากการลบเอกสารก่อนแก้ security audit M7)
— PDF, ไฟล์ขั้นตอน (.raw.txt / .cleaned.md / .chunks.json / .ocr.json) และ cache chunk+embedding ใน uploads/cache
ไม่แตะ uploads/forms (แบบฟอร์มมีตารางของตัวเอง)

    cd services/api
    python -m scripts.purge_orphan_upload_files            # ดูรายการที่จะลบ
    python -m scripts.purge_orphan_upload_files --execute  # ลบจริง
ใน Docker: docker compose exec backend python -m scripts.purge_orphan_upload_files [--execute]
"""
import argparse
from pathlib import Path

from sqlalchemy import create_engine, select

from app.core.config import settings
from app.models.models import Document
from app.services.rebuild_service import cache_file_prefix

STEP_SUFFIXES = (".raw.txt", ".cleaned.md", ".chunks.json", ".ocr.json")


def orphan_files(uploads: Path, known: set) -> list:
    out = []
    for f in uploads.iterdir():
        if not f.is_file():
            continue
        base = next((f.name[: -len(s)] for s in STEP_SUFFIXES if f.name.endswith(s)), f.name)
        if base not in known:
            out.append(f)
    cache_dir = uploads / "cache"
    if cache_dir.is_dir():
        prefixes = tuple(cache_file_prefix(name) for name in known)
        out += [f for f in cache_dir.iterdir() if f.is_file() and not f.name.startswith(prefixes)]
    return sorted(out)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    engine = create_engine(settings.DATABASE_URL_SYNC, **settings.DB_ENGINE_OPTIONS)
    with engine.connect() as conn:
        known = set(conn.execute(select(Document.filename)).scalars().all())
    engine.dispose()

    uploads = Path(settings.UPLOADS_DIR)
    files = orphan_files(uploads, known)
    for f in files:
        print(("ลบ " if args.execute else "จะลบ ") + str(f.relative_to(uploads)))
        if args.execute:
            f.unlink()
    print(f"\n{len(files)} ไฟล์" + ("" if args.execute else " — ใส่ --execute เพื่อลบจริง"))


if __name__ == "__main__":
    main()
