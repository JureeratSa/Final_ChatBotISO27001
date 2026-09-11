"""
Unit tests: app/utils/sanitize.py
ครอบคลุมการกัน Stored XSS จากเนื้อหา CKEditor (ประกาศ) ก่อนเก็บลง DB
"""
from app.utils.sanitize import sanitize_html


def test_strips_script_tag():
    assert "<script" not in sanitize_html("<p>hi</p><script>alert(1)</script>")


def test_strips_event_handler_attributes():
    out = sanitize_html('<img src=x onerror="alert(1)">')
    assert "onerror" not in out


def test_strips_javascript_url_scheme():
    out = sanitize_html('<a href="javascript:alert(1)">click</a>')
    assert "javascript:" not in out


def test_keeps_allowed_formatting_tags():
    out = sanitize_html("<p><strong>bold</strong> and <em>italic</em></p>")
    assert "<strong>bold</strong>" in out
    assert "<em>italic</em>" in out


def test_allows_safe_http_link():
    out = sanitize_html('<a href="https://example.com">link</a>')
    assert 'href="https://example.com"' in out


def test_none_and_empty_are_noop():
    assert sanitize_html(None) is None
    assert sanitize_html("") == ""
