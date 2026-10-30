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

    # Database — ไม่มีค่า default ของ host/user/password: ต้องตั้งใน .env เสมอ
    # DB_ENGINE: "mysql" = TiDB Cloud (ใช้งานอยู่) | "mssql" = Microsoft SQL Server (เตรียมไว้ย้ายไป — ดู docs/SQLSERVER_MIGRATION.md)
    DB_ENGINE: str = "mysql"
    DB_HOST: str
    DB_PORT: int = 4000          # TiDB = 4000, SQL Server ปกติ = 1433
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str = "chatbot"
    # เฉพาะ SQL Server — ชื่อ ODBC driver ที่ติดตั้งในเครื่อง/อิมเมจ และการเข้ารหัสการเชื่อมต่อ
    DB_ODBC_DRIVER: str = "ODBC Driver 18 for SQL Server"
    DB_ENCRYPT: bool = True
    # True = ยอมรับใบรับรองที่ไม่ได้ออกโดย CA ที่เครื่องเชื่อ (เช่น self-signed ของ SQL Server ภายใน) — ใช้เท่าที่จำเป็น
    DB_TRUST_SERVER_CERTIFICATE: bool = False

    def _mssql_url(self, driver: str) -> str:
        from sqlalchemy.engine import URL
        return URL.create(
            f"mssql+{driver}",
            username=self.DB_USER,
            password=self.DB_PASSWORD,   # URL.create escape อักขระพิเศษในรหัสผ่านให้เอง
            host=self.DB_HOST,
            port=self.DB_PORT,
            database=self.DB_NAME,
            query={
                "driver": self.DB_ODBC_DRIVER,
                "Encrypt": "yes" if self.DB_ENCRYPT else "no",
                "TrustServerCertificate": "yes" if self.DB_TRUST_SERVER_CERTIFICATE else "no",
            },
        ).render_as_string(hide_password=False)

    @property
    def DATABASE_URL(self) -> str:
        if self.DB_ENGINE == "mssql":
            return self._mssql_url("aioodbc")
        return (
            f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def DATABASE_URL_SYNC(self) -> str:
        """สำหรับ Alembic / sync operations"""
        if self.DB_ENGINE == "mssql":
            return self._mssql_url("pyodbc")
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
    # ชื่อเครื่องเซิร์ฟเวอร์ที่ผู้ใช้ใช้เปิดเว็บแทน IP (คั่นด้วย ,) เช่น chatbot-server,chatbot-server.hospital.local
    # อนุญาตเฉพาะ port 5173/5174/8080 แบบเดียวกับวง IP 172.30.x.x (ดู app/main.py)
    CORS_EXTRA_HOSTS: str = ""

    # AI / LLM — ใช้ endpoint ของ GDCC (LiteLLM, รูปแบบ OpenAI /v1/chat/completions) ตั้งแต่ 2026-10
    # LITELLM_URL = base URL ที่ลงท้ายด้วย /v1 ; ชื่อโมเดลต้องตรงกับที่ endpoint นั้นให้บริการ
    LITELLM_URL: Optional[str] = None
    LITELLM_API_KEY: Optional[str] = None
    DEFAULT_LLM_MODEL: str = "google/gemma-4-31B-it"

    # ── ของเดิม (OpenRouter) เลิกใช้แล้ว เก็บไว้อ้างอิง ยังไม่ลบ ──
    # GEMINI_API_KEY: Optional[str] = None
    # OPENROUTER_API_KEY: Optional[str] = None
    # DEFAULT_LLM_MODEL: str = "google/gemma-4-26b-a4b-it"

    @property
    def LLM_API_KEY(self) -> str:
        """API key สำหรับเรียก LLM (LITELLM_API_KEY ใน .env)"""
        return self.LITELLM_API_KEY or ""
        # ของเดิม (OpenRouter):
        # return self.GEMINI_API_KEY or self.OPENROUTER_API_KEY or ""

    @property
    def LLM_CHAT_URL(self) -> str:
        """URL เต็มของ chat completions — ทุกจุดที่เรียก LLM ใช้ค่านี้ที่เดียว ("" ถ้ายังไม่ตั้ง LITELLM_URL)"""
        base = (self.LITELLM_URL or "").strip().rstrip("/")
        return f"{base}/chat/completions" if base else ""

    # File Storage (ปรับใช้ path ให้สามารถรันได้ทั้ง local และ docker)
    #
    # หมายเหตุ: เดิม 3 property นี้เช็ค `.exists()` ก่อนตัดสินใจว่าจะใช้ path แบบ
    # relative กับ repo หรือ fallback ไปที่ /app/... แบบ hardcode — ปัญหาคือโฟลเดอร์
    # uploads/ และ index_db/ ถูก .gitignore ไว้ ในเครื่อง/CI ที่ checkout สดๆ ยังไม่มี
    # โฟลเดอร์นี้อยู่จริง เลยตกไป fallback เป็น "/app/uploads" ซึ่งเป็น path เฉพาะ
    # ตอนรันใน Docker container เท่านั้น พอโค้ดที่เรียกใช้ (เช่น
    # app/routers/admin.py ตอน import module) สั่ง mkdir(parents=True) จะพัง
    # ด้วย PermissionError เพราะ process ทั่วไปไม่มีสิทธิ์สร้างโฟลเดอร์ที่ root ('/app')
    # แก้โดยคำนวณ path จากตำแหน่งไฟล์จริงเสมอ ไม่พึ่ง .exists() — ให้ mkdir()
    # ฝั่งเรียกใช้เป็นคนสร้างโฟลเดอร์เองตามปกติ ส่วน "/app/..." เหลือไว้เป็น
    # fallback สุดท้ายกรณีคำนวณ path จากไฟล์นี้ไม่ได้จริงๆ เท่านั้น
    @property
    def UPLOADS_DIR(self) -> str:
        from pathlib import Path
        try:
            base_dir = Path(__file__).parents[3]
            return str((base_dir / "uploads").resolve())
        except Exception:
            return "/app/uploads"

    @property
    def INDEX_DB_DIR(self) -> str:
        from pathlib import Path
        try:
            base_dir = Path(__file__).parents[3]
            return str((base_dir / "index_db").resolve())
        except Exception:
            return "/app/index_db"

    @property
    def ADMIN_DIR(self) -> str:
        from pathlib import Path
        try:
            base_dir = Path(__file__).parents[3]
            return str((base_dir / "Admin").resolve())
        except Exception:
            return "/app/Admin"

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 30
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    # เชื่อ X-Forwarded-For เฉพาะเมื่อมี reverse proxy ของเราอยู่หน้า backend — ไม่งั้น client ปลอม IP ได้
    TRUST_PROXY_HEADERS: bool = False
    # กันเดารหัสผ่าน (ดู app/core/rate_limit.py LoginThrottle)
    LOGIN_MAX_FAILURES_PER_IP_USER: int = 5
    LOGIN_MAX_FAILURES_PER_USER: int = 10
    LOGIN_FAILURE_WINDOW_MINUTES: int = 15

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
