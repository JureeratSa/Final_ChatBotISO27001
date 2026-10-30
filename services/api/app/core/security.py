"""
รหัสผ่าน (bcrypt), JWT access token และการกันชื่อไฟล์อันตราย (path traversal)
"""
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

import bcrypt
import jwt
from fastapi import HTTPException

from app.core.config import settings


# ─── รหัสผ่าน ─────────────────────────────────────────────────────────────────

def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


# hash หลอกไว้เทียบตอนไม่พบ username — ให้เวลาตอบเท่ากับกรณีรหัสผิด (กันการเดาว่า username ไหนมีจริง)
_DUMMY_PASSWORD_HASH = bcrypt.hashpw(secrets.token_bytes(16), bcrypt.gensalt()).decode("utf-8")


def verify_user_password(plain_password: str, user) -> bool:
    """user อาจเป็น None (ไม่พบบัญชี) — ยังรัน bcrypt เสมอ"""
    if user is None:
        verify_password(plain_password, _DUMMY_PASSWORD_HASH)
        return False
    return verify_password(plain_password, user.password_hash)


# ─── JWT ──────────────────────────────────────────────────────────────────────

def create_access_token(data: Dict[str, Any]) -> str:
    """data = {"sub": username, "tv": token_version} — อายุตาม ACCESS_TOKEN_EXPIRE_MINUTES (15 นาที)
    iat ใช้ตัด token ที่ออกก่อนเปลี่ยนรหัสผ่าน, jti ใช้ยกเลิกรายใบตอน logout"""
    now = datetime.now(timezone.utc)
    payload = {
        **data,
        "type": "access",
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": int(now.timestamp()),
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def verify_access_token(token: str) -> Dict[str, Any]:
    """คืน payload — token ผิด/หมดอายุ/ไม่ใช่ access token → ValueError"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.PyJWTError as e:
        raise ValueError(f"Invalid token: {e}")
    if payload.get("type") != "access":
        raise ValueError("Not an access token")
    return payload


# ─── ชื่อไฟล์จากผู้ใช้ ───────────────────────────────────────────────────────────

def safe_path(base_dir: Path, relative_path: str) -> Path:
    """path เต็มของไฟล์ที่ต้องอยู่ใต้ base_dir เท่านั้น (กัน "../../etc/passwd")"""
    base = base_dir.resolve()
    target = (base / relative_path).resolve()
    if target != base and base not in target.parents:
        raise HTTPException(status_code=400, detail="รูปแบบชื่อไฟล์ไม่ปลอดภัย (Path Traversal Detected)")
    return target


def safe_filename(filename: str) -> str:
    """ตัดโฟลเดอร์ออก เหลือแค่ชื่อไฟล์ ("a/../b.pdf" → "b.pdf")"""
    name = Path(filename.replace("\\", "/")).name.strip()
    if not name or name in (".", ".."):
        raise HTTPException(status_code=400, detail="ชื่อไฟล์ไม่ถูกต้อง")
    return name
