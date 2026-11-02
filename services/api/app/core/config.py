"""
ค่าตั้งของระบบทั้งหมด อ่านจาก environment variable / ไฟล์ services/api/.env

ค่าลับ (DB_PASSWORD, JWT_SECRET_KEY, API key) ไม่มีค่า default ในโค้ด — ต้องตั้งใน .env เท่านั้น
"""
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

# โฟลเดอร์ services/api (ใน Docker คือ /app)
SERVICE_DIR = Path(__file__).resolve().parents[2]
# รากของโปรเจกต์ — ตอนรัน dev ข้อมูล (uploads/, index_db/, sample_chunks.json) อยู่ที่นี่
PROJECT_DIR = SERVICE_DIR.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(SERVICE_DIR / ".env"), extra="ignore")

    APP_NAME: str = "TUH Chatbot AI"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False

    # ─── ฐานข้อมูล ───────────────────────────────────────────────────────────
    # "mssql" = SQL Server (ใช้งานจริงตั้งแต่ 2026-11-02), "mysql" = TiDB Cloud (เผื่อย้อนกลับ) — docs/SQLSERVER_MIGRATION.md
    DB_ENGINE: str = "mysql"
    DB_HOST: str
    DB_PORT: int = 4000                      # TiDB = 4000, SQL Server = 1433
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str = "chatbot"
    DB_ODBC_DRIVER: str = "ODBC Driver 18 for SQL Server"   # ใช้เฉพาะ SQL Server
    DB_ENCRYPT: bool = True
    DB_TRUST_SERVER_CERTIFICATE: bool = False

    # ─── Login / JWT ─────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    INITIAL_ADMIN_USERNAME: str = "admin"    # สร้างบัญชีนี้ตอนฐานข้อมูลยังไม่มีผู้ใช้เลย
    INITIAL_ADMIN_PASSWORD: Optional[str] = None
    LOGIN_MAX_FAILURES_PER_IP_USER: int = 5  # ล็อกชั่วคราวเมื่อเดารหัสผิดเกินนี้ (ดู core/rate_limit.py)
    LOGIN_MAX_FAILURES_PER_USER: int = 10
    LOGIN_FAILURE_WINDOW_MINUTES: int = 15

    # ─── CORS / proxy / rate limit ──────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:5173"
    CORS_EXTRA_HOSTS: str = ""               # ชื่อเครื่องเซิร์ฟเวอร์ คั่นด้วย , (ใช้กับ dev server)
    TRUST_PROXY_HEADERS: bool = False        # True เมื่ออยู่หลัง reverse proxy ของเราเท่านั้น
    RATE_LIMIT_REQUESTS: int = 30
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    MAX_DOCUMENT_UPLOAD_MB: int = 50
    MAX_FORM_UPLOAD_MB: int = 20

    # ─── LLM (GDCC LiteLLM, รูปแบบ OpenAI) และ OCR ───────────────────────────
    LITELLM_URL: Optional[str] = None        # base URL ที่ลงท้ายด้วย /v1
    LITELLM_API_KEY: Optional[str] = None
    DEFAULT_LLM_MODEL: str = "google/gemma-4-31B-it"
    TYPHOON_OCR_URL: Optional[str] = None    # ไม่ตั้ง = หน้า PDF ที่เป็นภาพสแกนจะไม่มีข้อความ
    TYPHOON_OCR_API_KEY: Optional[str] = None
    TYPHOON_OCR_MODEL: str = "typhoon-ocr-1-5"
    TESSERACT_CMD: Optional[str] = None      # ไม่ตั้ง = หาใน PATH (ใช้หาตำแหน่งบรรทัดเพื่อไฮไลท์)

    # ─── ที่เก็บไฟล์ ─────────────────────────────────────────────────────────
    DATA_DIR: Path = PROJECT_DIR             # Docker ตั้งเป็น /app (uploads/ และ index_db/ เป็น volume)
    CHROMA_DB_DIR: Optional[str] = None      # ไม่ตั้ง = <INDEX_DB_DIR>/chroma_db

    @property
    def LLM_API_KEY(self) -> str:
        return self.LITELLM_API_KEY or ""

    @property
    def LLM_CHAT_URL(self) -> str:
        base = (self.LITELLM_URL or "").strip().rstrip("/")
        return f"{base}/chat/completions" if base else ""

    @property
    def UPLOADS_DIR(self) -> str:
        return str(Path(self.DATA_DIR) / "uploads")

    @property
    def INDEX_DB_DIR(self) -> str:
        return str(Path(self.DATA_DIR) / "index_db")

    @property
    def CHROMA_DIR(self) -> str:
        return self.CHROMA_DB_DIR or str(Path(self.INDEX_DB_DIR) / "chroma_db")

    @property
    def CHUNKS_FILE(self) -> str:
        """สำเนาข้อความ chunk ทั้งหมดของดัชนีล่าสุด (ให้หน้าประวัติเปิดดู chunk ที่บอทใช้ตอบ)
        อยู่คู่กับ bm25.pkl เพราะสร้างจาก rebuild รอบเดียวกัน"""
        return str(Path(self.INDEX_DB_DIR) / "sample_chunks.json")

    @property
    def DATABASE_URL(self) -> str:
        """URL ที่แอปใช้ (async)"""
        if self.DB_ENGINE == "mssql":
            return self._mssql_url("aioodbc")
        return f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def DATABASE_URL_SYNC(self) -> str:
        """URL แบบ sync สำหรับ Alembic และงานที่รันใน thread (rebuild)"""
        if self.DB_ENGINE == "mssql":
            return self._mssql_url("pyodbc")
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def DB_ENGINE_OPTIONS(self) -> dict:
        """ส่งให้ create_engine / create_async_engine ทุกที่
        SQL Server: ปิด setinputsizes — ไม่งั้น String ถูกส่งเป็น VARCHAR แล้วภาษาไทยที่บันทึกทีละแถวกลายเป็น ????
        (collation ของ DB ไม่ใช่ภาษาไทย ทดสอบแล้ว 2026-11-02)"""
        return {"use_setinputsizes": False} if self.DB_ENGINE == "mssql" else {}

    def _mssql_url(self, driver: str) -> str:
        from sqlalchemy.engine import URL
        return URL.create(
            f"mssql+{driver}",
            username=self.DB_USER,
            password=self.DB_PASSWORD,
            host=self.DB_HOST,
            port=self.DB_PORT,
            database=self.DB_NAME,
            query={
                "driver": self.DB_ODBC_DRIVER,
                "Encrypt": "yes" if self.DB_ENCRYPT else "no",
                "TrustServerCertificate": "yes" if self.DB_TRUST_SERVER_CERTIFICATE else "no",
            },
        ).render_as_string(hide_password=False)


settings = Settings()
