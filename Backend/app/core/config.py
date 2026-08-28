"""
TUH Chatbot AI — Core Configuration
ไฟล์กำหนดค่าหลักของระบบ โหลดจาก Environment Variables
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App Info
    APP_NAME: str = "TUH Chatbot AI"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # TiDB Cloud (MySQL) Database
    DB_HOST: str = "gateway01.ap-southeast-1.prod.aws.tidbcloud.com"
    DB_PORT: int = 4000
    DB_USER: str = "2LejCpHSLet7wXP.root"
    DB_PASSWORD: str = "eg8UcQJpbxenLaeN"
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

    # JWT Auth
    JWT_SECRET_KEY: str = "tuh-chatbot-super-secret-key-change-in-production-2026"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

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

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
