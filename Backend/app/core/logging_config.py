"""
TUH Chatbot AI — Logging Configuration
เดิมทั้งโปรเจกต์ใช้ print() ล้วน (20+ จุด) ทำให้ไม่มี timestamp, log level, หรือชื่อ module
กำกับเลย กรองด้วยเครื่องมือ log ปกติไม่ได้ และแยกไม่ออกว่าอันไหนคือ error จริงๆ กับข้อความแจ้งเฉยๆ
เรียก setup_logging() ครั้งเดียวตอน import app.main แล้วใช้ logging.getLogger(__name__) ในทุกไฟล์
"""
import logging
import sys

from app.core.config import settings

_configured = False


def setup_logging() -> None:
    global _configured
    if _configured:
        return
    _configured = True

    level = logging.DEBUG if settings.DEBUG else logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        fmt="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)

    # sqlalchemy engine logging เป็น DEBUG มันจะท่วม log ปกติ — ปล่อยให้ settings.DEBUG (echo=True) คุมแทน
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
