"""
Unit Test — Input/File Security (UT-06 ถึง UT-08)
อ้างอิง: แผนทดสอบเว็บ T3 — เรียก app.utils.sanitize / app.core.security ตรงๆ
"""
import pytest
from fastapi import HTTPException

from app.utils.sanitize import sanitize_html
from app.core.security import safe_path, safe_filename


# ─── UT-06: กรอง <script> และ event handler ออกจากข้อความก่อน render ─────────

def test_UT06_strips_script_tag():
    out = sanitize_html("<p>ประกาศ</p><script>alert(1)</script>")
    assert "<script" not in out


def test_UT06_strips_event_handler_attribute():
    out = sanitize_html('<img src=x onerror="alert(1)">')
    assert "onerror" not in out


# ─── UT-07: อนุญาต HTML tag ที่ปลอดภัยตาม allowlist (EP — กลุ่มที่ควรผ่าน) ───

def test_UT07_keeps_allowed_formatting_tags():
    out = sanitize_html("<p><strong>ด่วน</strong> และ <em>สำคัญ</em></p>")
    assert "<strong>ด่วน</strong>" in out
    assert "<em>สำคัญ</em>" in out


def test_UT07_allows_safe_http_link():
    out = sanitize_html('<a href="https://hospital.tu.ac.th">รายละเอียด</a>')
    assert 'href="https://hospital.tu.ac.th"' in out


# ─── UT-08: ชื่อไฟล์ที่มี ../ หรือ path หลุด base directory (EG) ──────────────

def test_UT08_safe_path_blocks_traversal(tmp_path):
    base_dir = tmp_path / "uploads"
    base_dir.mkdir()
    with pytest.raises(HTTPException):
        safe_path(base_dir, "../../etc/passwd")


def test_UT08_safe_path_allows_file_inside_base(tmp_path):
    base_dir = tmp_path / "uploads"
    base_dir.mkdir()
    result = safe_path(base_dir, "policy.pdf")
    assert result == (base_dir / "policy.pdf").resolve()


def test_UT08_safe_filename_strips_path_components():
    assert safe_filename("../../evil/../policy.pdf") == "policy.pdf"


def test_UT08_safe_filename_rejects_dot_only_name():
    with pytest.raises(HTTPException):
        safe_filename("..")
