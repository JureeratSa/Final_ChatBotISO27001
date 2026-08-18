"""
TUH Chatbot AI — Security Module (Cybersecurity Engineer)
รับผิดชอบ: JWT Token, Password Hashing, Token Verification
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import hashlib
import hmac
import secrets
import base64

from jose import JWTError, jwt
import bcrypt
from app.core.config import settings

# ─── Password Utilities ────────────────────────────────────────────────────────

def hash_password(plain_password: str) -> str:
    """Hash รหัสผ่านด้วย bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """ตรวจสอบรหัสผ่านกับ hash ที่เก็บไว้"""
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception:
        return False


def verify_legacy_password(plain_password: str, salt_hex: str, hash_hex: str) -> bool:
    """
    ตรวจสอบรหัสผ่านรูปแบบเก่า (pbkdf2_hmac) สำหรับ migrate ข้อมูล admin เดิม
    ใช้ชั่วคราวระหว่างการ migrate เท่านั้น
    """
    try:
        salt = bytes.fromhex(salt_hex)
        key = hashlib.pbkdf2_hmac(
            'sha256',
            plain_password.encode('utf-8'),
            salt,
            100000
        )
        return key.hex() == hash_hex
    except Exception:
        return False


# ─── JWT Token Utilities ───────────────────────────────────────────────────────

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """สร้าง JWT Access Token (อายุ 15 นาที)"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: Dict[str, Any]) -> str:
    """สร้าง JWT Refresh Token (อายุ 7 วัน)"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """Decode และตรวจสอบ JWT Token (raise exception หากไม่ valid)"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}")


def verify_access_token(token: str) -> Dict[str, Any]:
    """ตรวจสอบ Access Token โดยเฉพาะ"""
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise ValueError("Not an access token")
    return payload


def verify_refresh_token(token: str) -> Dict[str, Any]:
    """ตรวจสอบ Refresh Token โดยเฉพาะ"""
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise ValueError("Not a refresh token")
    return payload


def generate_token_pair(username: str) -> Dict[str, str]:
    """สร้าง Access + Refresh Token คู่สำหรับ login"""
    data = {"sub": username}
    access_token = create_access_token(data)
    refresh_token = create_refresh_token(data)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }
