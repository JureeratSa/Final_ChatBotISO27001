"""
Unit Test — Auth (UT-01 ถึง UT-05)
อ้างอิง: แผนทดสอบเว็บ T3 — เรียกฟังก์ชันใน app.core.security / app.schemas.schemas ตรงๆ
ไม่พึ่งฐานข้อมูลหรือ HTTP request
"""
from datetime import timedelta

import pytest
from pydantic import ValidationError

from app.core.security import (
    hash_password,
    create_access_token,
    create_refresh_token,
    verify_access_token,
    verify_refresh_token,
)
from app.schemas.schemas import UserCreate


# ─── UT-01: Hash รหัสผ่านใหม่ด้วยอัลกอริทึมที่ปลอดภัย ─────────────────────────

def test_UT01_hash_password_is_not_plaintext():
    hashed = hash_password("MyS3cret!")
    assert hashed != "MyS3cret!"
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")


# ─── UT-02: ตรวจความแข็งแรงรหัสผ่านใหม่ (EP — กลุ่มผ่าน/ไม่ผ่าน) ──────────────

def test_UT02_weak_password_is_rejected():
    """รหัสผ่านสั้นกว่า MIN_PASSWORD_LENGTH (8 ตัว) ต้องถูกปฏิเสธตั้งแต่ระดับ schema"""
    with pytest.raises(ValidationError):
        UserCreate(username="staff01", password="short1", display_name="ทดสอบ", role="admin")


def test_UT02_strong_password_is_accepted():
    user = UserCreate(username="staff01", password="Str0ngPass!", display_name="ทดสอบ", role="admin")
    assert user.password == "Str0ngPass!"


# ─── UT-03: สร้างและถอดรหัส JWT access token ──────────────────────────────────

def test_UT03_access_token_roundtrip():
    token = create_access_token({"sub": "staff01"})
    payload = verify_access_token(token)
    assert payload["sub"] == "staff01"
    assert payload["type"] == "access"


# ─── UT-04: ตรวจสอบ JWT ที่หมดอายุพอดีเวลา (BVA — ขอบเขตก่อน/หลัง exp) ───────

def test_UT04_expired_token_is_rejected():
    """token ที่หมดอายุไปแล้วแม้แค่ 1 วินาที ต้องถูกปฏิเสธ"""
    token = create_access_token({"sub": "staff01"}, expires_delta=timedelta(seconds=-1))
    with pytest.raises(ValueError):
        verify_access_token(token)


def test_UT04_not_yet_expired_token_is_accepted():
    """token ที่ยังไม่หมดอายุ (เหลืออีก 5 วินาที) ต้องผ่าน — ฝั่งตรงข้ามของ boundary เดียวกัน"""
    token = create_access_token({"sub": "staff01"}, expires_delta=timedelta(seconds=5))
    payload = verify_access_token(token)
    assert payload["sub"] == "staff01"


# ─── UT-05: ใช้ refresh token แทนที่ access token (EG — สลับประเภท token) ─────

def test_UT05_refresh_token_rejected_as_access_token():
    token = create_refresh_token({"sub": "staff01"})
    with pytest.raises(ValueError):
        verify_access_token(token)


def test_UT05_access_token_rejected_as_refresh_token():
    token = create_access_token({"sub": "staff01"})
    with pytest.raises(ValueError):
        verify_refresh_token(token)
