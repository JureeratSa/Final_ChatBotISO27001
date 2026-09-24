"""
TUH Chatbot AI — Security Module (Cybersecurity & Cryptography)
รับผิดชอบ:
1. การแฮชและตรวจสอบรหัสผ่านด้วย bcrypt (Salted Hash)
2. การสร้างและตรวจสอบ JWT Token (HMAC-SHA256)
3. การป้องกันช่องโหว่ Path Traversal (CWE-22) ในการเข้าถึงไฟล์ระบบ
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from pathlib import Path
import hashlib
import hmac
import secrets
import base64

from jose import JWTError, jwt
import bcrypt
from app.core.config import settings

# ─── 1. Password Utilities (ระบบรหัสผ่าน) ────────────────────────────────────────

def hash_password(plain_password: str) -> str:
    """
    สร้าง Hash รหัสผ่านด้วยอัลกอริทึม bcrypt
    Args:
        plain_password (str): รหัสผ่านแบบข้อความธรรมดา
    Returns:
        str: รหัสผ่านที่ผ่านการ Salt และ Hash เรียบร้อยแล้ว
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    ตรวจสอบความถูกต้องของรหัสผ่านเทียบกับ Hash ที่เก็บในฐานข้อมูล
    Args:
        plain_password (str): รหัสผ่านที่ผู้ใช้ป้อนเข้ามา
        hashed_password (str): Hash ที่เก็บอยู่ในฐานข้อมูล
    Returns:
        bool: True ถ้ารหัสผ่านถูกต้อง, False ถ้าไม่ถูกต้อง
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception:
        return False


def verify_legacy_password(plain_password: str, salt_hex: str, hash_hex: str) -> bool:
    """
    ตรวจสอบรหัสผ่านรูปแบบเก่า (PBKDF2-HMAC-SHA256)
    ใช้สำหรับการยืนยันรหัสผ่านระหว่างการ Migrate ข้อมูลจากระบบ v1
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


# ─── 2. JWT Token Utilities (ระบบ Token ยืนยันตัวตน) ──────────────────────────

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    สร้าง JWT Access Token (มีอายุสั้น เช่น 15 นาที) สำหรับแนบใน Header ทุก Request
    Args:
        data (dict): Payload ข้อมูล (เช่น {"sub": username})
        expires_delta (timedelta, optional): กำหนดอายุ Token เอง
    Returns:
        str: JWT Token สตริงที่ลงลายมือชื่อดิจิทัลแล้ว
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    สร้าง JWT Refresh Token (มีอายุยาว เช่น 7 วัน) สำหรับใช้ขอ Access Token ใหม่
    Args:
        data (dict): Payload ข้อมูล (เช่น {"sub": username})
    Returns:
        str: JWT Refresh Token สตริง
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """
    ถอดรหัสและตรวจสอบความถูกต้องของ JWT Token
    Raises:
        ValueError: ถ้า Token หมดอายุหรือ Signature ไม่ถูกต้อง
    Returns:
        dict: Payload ข้อมูลที่อยู่ใน Token
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}")


def verify_access_token(token: str) -> Dict[str, Any]:
    """
    ตรวจสอบ Access Token โดยเฉพาะ (ต้องมี type == 'access')
    """
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise ValueError("Not an access token")
    return payload


def verify_refresh_token(token: str) -> Dict[str, Any]:
    """
    ตรวจสอบ Refresh Token โดยเฉพาะ (ต้องมี type == 'refresh')
    """
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise ValueError("Not a refresh token")
    return payload


def generate_token_pair(username: str) -> Dict[str, str]:
    """
    สร้างคู่ Token (Access + Refresh Token) ส่งให้ Client ตอน Login สำเร็จ
    """
    data = {"sub": username}
    access_token = create_access_token(data)
    refresh_token = create_refresh_token(data)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


# ─── 3. Path Traversal Defenses (ป้องกันการโจมตีไฟล์ระบบ) ──────────────────────

def safe_path(base_dir: Path, relative_path: str) -> Path:
    """
    ตรวจสอบและแปลง Relative Path ให้เป็น Absolute Path ภายใต้ base_dir เท่านั้น
    เพื่อป้องกัน Path Traversal Attack (CWE-22) เช่น '../../windows/system32'
    
    Args:
        base_dir (Path): โฟลเดอร์ต้นทางที่อนุญาต (เช่น /app/uploads)
        relative_path (str): Path ที่รับมาจากคำขอของผู้ใช้
    Returns:
        Path: Absolute Path ที่ปลอดภัย
    Raises:
        HTTPException(400): ถ้า Path หลุดออกนอก base_dir
    """
    from fastapi import HTTPException
    base_abs = base_dir.resolve()
    target_abs = (base_abs / relative_path).resolve()
    
    # ตรวจสอบว่า target_abs ต้องเป็นโฟลเดอร์ย่อยของ base_abs จริงๆ
    if target_abs != base_abs and base_abs not in target_abs.parents:
        raise HTTPException(status_code=400, detail="รูปแบบชื่อไฟล์ไม่ปลอดภัย (Path Traversal Detected)")
    return target_abs


def safe_filename(filename: str) -> str:
    """
    ตัด Directory Separator ทั้งหมดออกจากชื่อไฟล์ที่รับจาก Client เหลือเฉพาะ Base File Name
    ป้องกันการแทรก Path มาในชื่อไฟล์ที่อัปโหลด
    """
    from fastapi import HTTPException
    name = Path(filename.replace("\\", "/")).name.strip()
    if not name or name in (".", ".."):
        raise HTTPException(status_code=400, detail="ชื่อไฟล์ไม่ถูกต้อง")
    return name

