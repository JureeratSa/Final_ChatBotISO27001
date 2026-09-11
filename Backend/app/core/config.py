"""
TUH Chatbot AI — Core Configuration
ไฟล์กำหนดค่าหลักของระบบ โหลดจาก Environment Variables

หมายเหตุความปลอดภัย: ค่าที่เป็นความลับ (DB_PASSWORD, JWT_SECRET_KEY ฯลฯ) ไม่มีค่า default
ในโค้ดโดยเจตนา — ต้องกำหนดผ่าน .env หรือ environment variable เท่านั้น ห้าม hardcode ค่าจริงไว้ในไฟล์นี้
เพราะไฟล์นี้ถูก track ใน git (เคยมีรหัสผ่าน production หลุดมาก่อนเพราะ hardcode ไว้ตรงนี้)
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from pathlib import Path


class Settings(BaseSettings):
    # App Info
    APP_NAME: str = "TUH Chatbot AI"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # TiDB Cloud (MySQL) Database — ไม่มีค่า default: ต้องตั้งใน .env เสมอ
    DB_HOST: str
    DB_PORT: int = 4000
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str = "chatbot"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def DATABASE_URL_SYNC(self) -> str:
        """สำหรับ Alembic / sync operations"""
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # JWT Auth — ไม่มีค่า default: ต้องตั้งใน .env เสมอ (สร้างด้วย `python -c "import secrets; print(secrets.token_urlsafe(64))"`)
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Initial Admin Bootstrap — ใช้ตอน DB ว่างเปล่าครั้งแรกเท่านั้น
    # ถ้าไม่ตั้งค่านี้ ระบบจะสุ่มรหัสผ่านให้และ print ออก console ครั้งเดียวตอน startup
    # (ไม่ใช้ default แบบ hardcode เช่น admin1234 อีกต่อไป)
    INITIAL_ADMIN_USERNAME: str = "admin"
    INITIAL_ADMIN_PASSWORD: Optional[str] = None

    # CORS
    FRONTEND_URL: str = "http://localhost:5173"

    # AI / LLM
    GEMINI_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    DEFAULT_LLM_MODEL: str = "xiaomi/mimo-v2.5-pro"

    @property
    def LLM_API_KEY(self) -> str:
        """ดึง API key สำหรับ LLM — ใช้ GEMINI_API_KEY หรือ OPENROUTER_API_KEY ตัวใดก็ได้ที่มีค่า"""
        return self.GEMINI_API_KEY or self.OPENROUTER_API_KEY or ""

    # File Storage (ปรับใช้ path ให้สามารถรันได้ทั้ง local และ docker)
    @property
    def UPLOADS_DIR(self) -> str:
        from pathlib import Path
        try:
            base_dir = Path(__file__).parents[3]
            uploads_path = base_dir / "uploads"
            if uploads_path.exists():
                return str(uploads_path.resolve())
        except Exception:
            pass
        return "/app/uploads"

    @property
    def INDEX_DB_DIR(self) -> str:
        from pathlib import Path
        try:
            base_dir = Path(__file__).parents[3]
            index_path = base_dir / "index_db"
            if index_path.exists():
                return str(index_path.resolve())
        except Exception:
            pass
        return "/app/index_db"

    @property
    def ADMIN_DIR(self) -> str:
        from pathlib import Path
        try:
            base_dir = Path(__file__).parents[3]
            admin_path = base_dir / "Admin"
            if admin_path.exists():
                return str(admin_path.resolve())
        except Exception:
            pass
        return "/app/Admin"

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 30
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    _backend_dir = Path(__file__).parents[2]
    _root_dir = Path(__file__).parents[3]
    model_config = SettingsConfigDict(
        env_file=[
            str(_backend_dir / ".env"),
            str(_root_dir / ".env"),
            ".env"
        ],
        extra="ignore"
    )


settings = Settings()
