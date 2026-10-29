"""
CORS: เปิด UserWeb/AdminWeb จากเครื่องอื่นใน LAN ด้วย IP วง 172.30.x.x หรือชื่อเครื่องเซิร์ฟเวอร์ (CORS_EXTRA_HOSTS)
เดิมรองรับแค่ IP — เปิดด้วยชื่อเครื่องแล้ว login ไม่ได้ ("Failed to fetch") เพราะ preflight ตอบ 400
"""
import importlib
import re

import pytest

import app.main as main_module
from app.core.config import settings


@pytest.fixture
def origin_regex(monkeypatch):
    monkeypatch.setattr(settings, "CORS_EXTRA_HOSTS", "chatbot-server, chatbot-server.hospital.local")
    module = importlib.reload(main_module)
    yield re.compile(module.allowed_origin_regex)
    monkeypatch.undo()
    importlib.reload(main_module)


@pytest.mark.parametrize("origin", [
    "http://172.30.10.20:5174",
    "http://chatbot-server:5173",
    "http://CHATBOT-SERVER.hospital.local:5174",   # ตัวพิมพ์ใหญ่/เล็กต่างจากที่ตั้งไว้ก็ต้องผ่าน
    "http://chatbot-server:8080",
])
def test_allowed(origin_regex, origin):
    assert origin_regex.fullmatch(origin)


@pytest.mark.parametrize("origin", [
    "http://chatbot-server:9999",                  # port อื่น
    "http://chatbot-server.evil.com:5173",         # ต่อท้ายชื่อเครื่อง
    "http://evil-chatbot-server:5173",
    "https://172.30.1.1.evil.com:5173",
    "http://10.0.0.5:5173",
])
def test_rejected(origin_regex, origin):
    assert not origin_regex.fullmatch(origin)
