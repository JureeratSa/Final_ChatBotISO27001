"""
Unit tests: app/core/security.py
ครอบคลุม Password hashing, JWT token lifecycle, และ Path Traversal guard (safe_path)
ไม่แตะ DB / network — รันเร็วและ deterministic
"""
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi import HTTPException

from app.core.security import (
    hash_password,
    verify_password,
    verify_legacy_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_access_token,
    verify_refresh_token,
    safe_path,
    safe_filename,
)


# ─── Password hashing ───────────────────────────────────────────────────────────

def test_hash_password_is_not_plaintext():
    hashed = hash_password("MyS3cret!")
    assert hashed != "MyS3cret!"
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")


def test_verify_password_correct():
    hashed = hash_password("MyS3cret!")
    assert verify_password("MyS3cret!", hashed) is True


def test_verify_password_incorrect():
    hashed = hash_password("MyS3cret!")
    assert verify_password("WrongPassword", hashed) is False


def test_verify_password_against_garbage_hash_does_not_raise():
    """hash เสีย/ไม่ใช่ bcrypt format ต้องคืน False ไม่ใช่ throw (ป้องกัน 500 ตอน login)"""
    assert verify_password("anything", "not-a-real-bcrypt-hash") is False


def test_verify_legacy_password_roundtrip():
    import hashlib
    salt = bytes.fromhex("aa" * 16)
    key = hashlib.pbkdf2_hmac("sha256", "oldpass".encode("utf-8"), salt, 100000)
    assert verify_legacy_password("oldpass", salt.hex(), key.hex()) is True
    assert verify_legacy_password("wrongpass", salt.hex(), key.hex()) is False


# ─── JWT tokens ─────────────────────────────────────────────────────────────────

def test_access_token_roundtrip():
    token = create_access_token({"sub": "sysadmin"})
    payload = verify_access_token(token)
    assert payload["sub"] == "sysadmin"
    assert payload["type"] == "access"


def test_refresh_token_roundtrip():
    token = create_refresh_token({"sub": "sysadmin"})
    payload = verify_refresh_token(token)
    assert payload["sub"] == "sysadmin"
    assert payload["type"] == "refresh"


def test_refresh_token_rejected_as_access_token():
    """Refresh token ต้องใช้ยิง /login endpoint ที่ต้องการ access token ไม่ได้"""
    refresh = create_refresh_token({"sub": "sysadmin"})
    with pytest.raises(ValueError):
        verify_access_token(refresh)


def test_access_token_rejected_as_refresh_token():
    access = create_access_token({"sub": "sysadmin"})
    with pytest.raises(ValueError):
        verify_refresh_token(access)


def test_expired_access_token_is_rejected():
    expired = create_access_token({"sub": "sysadmin"}, expires_delta=timedelta(seconds=-1))
    with pytest.raises(ValueError):
        verify_access_token(expired)


def test_tampered_token_is_rejected():
    token = create_access_token({"sub": "sysadmin"})
    tampered = token[:-4] + "abcd"
    with pytest.raises(ValueError):
        decode_token(tampered)


def test_garbage_token_is_rejected():
    with pytest.raises(ValueError):
        decode_token("not.a.jwt")


# ─── Path Traversal protection (CWE-22) ─────────────────────────────────────────

def test_safe_path_allows_file_inside_base(tmp_path: Path):
    (tmp_path / "report.pdf").write_bytes(b"%PDF-1.4")
    result = safe_path(tmp_path, "report.pdf")
    assert result == (tmp_path / "report.pdf").resolve()


@pytest.mark.parametrize(
    "malicious_relative_path",
    [
        "../../../../etc/passwd",
        "..\\..\\..\\windows\\win.ini",
        "../secret/config.env",
        "sub/../../outside.txt",
    ],
)
def test_safe_path_blocks_traversal(tmp_path: Path, malicious_relative_path: str):
    with pytest.raises(HTTPException) as exc_info:
        safe_path(tmp_path, malicious_relative_path)
    assert exc_info.value.status_code == 400


def test_safe_path_blocks_absolute_path_escape(tmp_path: Path):
    """Path.resolve() ของ absolute path จะ escape ออกจาก base_dir ไปเลย ต้องถูกบล็อก"""
    outside = tmp_path.parent / "outside-secret.txt"
    with pytest.raises(HTTPException):
        safe_path(tmp_path, str(outside))


def test_safe_path_blocks_sibling_directory_with_shared_prefix(tmp_path: Path):
    """
    Regression test: เดิม safe_path ใช้ str(target).startswith(str(base)) ซึ่ง bypass ได้
    เพราะ "/app/uploads_evil" ก็ startswith "/app/uploads" ทั้งที่เป็นคนละโฟลเดอร์กันเลย
    ต้องใช้ is_relative_to()/parents แทนถึงจะจับ sibling directory แบบนี้ได้
    """
    base_dir = tmp_path / "uploads"
    base_dir.mkdir()
    sibling_dir = tmp_path / "uploads_evil"
    sibling_dir.mkdir()
    (sibling_dir / "secret.txt").write_text("leaked")

    with pytest.raises(HTTPException):
        safe_path(base_dir, "../uploads_evil/secret.txt")


# ─── Filename sanitization ──────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "raw_filename,expected",
    [
        ("report.pdf", "report.pdf"),
        ("../../etc/passwd.pdf", "passwd.pdf"),
        ("..\\..\\windows\\win.ini.pdf", "win.ini.pdf"),
        ("/absolute/path/file.pdf", "file.pdf"),
    ],
)
def test_safe_filename_strips_path_components(raw_filename: str, expected: str):
    assert safe_filename(raw_filename) == expected


@pytest.mark.parametrize("bad_filename", ["", ".", "..", "   "])
def test_safe_filename_rejects_empty_or_dot(bad_filename: str):
    with pytest.raises(HTTPException):
        safe_filename(bad_filename)
