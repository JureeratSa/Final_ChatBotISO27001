"""รูปแบบข้อมูลที่ API รับเข้า/ส่งออก (Pydantic) — ตรวจความถูกต้องของ input ก่อนถึงโค้ดใน endpoint"""
from datetime import datetime, timezone
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator

from app.services.password_policy import validate_password


def _validate_password_strength(value: str) -> str:
    """นโยบายรหัสผ่านแอดมิน (ความยาว + ตัวพิมพ์ใหญ่/เล็ก/ตัวเลข/สัญลักษณ์ + ห้ามรหัสเดาง่าย)
    — กฎเต็มอยู่ที่ app/services/password_policy.py"""
    if value is None:
        return value
    return validate_password(value)


# ─── User Schemas ──────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str
    password: str
    display_name: str = "Admin"
    role: str = "admin"
    department: Optional[str] = None

    _validate_password = field_validator("password")(_validate_password_strength)

    @model_validator(mode="after")
    def _password_not_username(self):
        validate_password(self.password, self.username)
        return self


class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    is_active: Optional[bool] = None

    _validate_password = field_validator("password")(_validate_password_strength)


class UserResponse(BaseModel):
    id: int
    username: str
    display_name: str
    role: str
    department: Optional[str] = None
    is_active: bool
    created_at: datetime

    # ฐานข้อมูลคืนเวลา UTC แบบไม่มี timezone — ติด UTC ให้ เบราว์เซอร์จะแปลงเป็นเวลาไทยเอง
    @field_validator("created_at")
    @classmethod
    def _created_at_utc(cls, value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    class Config:
        from_attributes = True


# ─── Settings Schemas ──────────────────────────────────────────────────────────

class FAQ(BaseModel):
    # ต้องประกาศ id/icon ไว้ — Pydantic ทิ้ง field ที่ไม่ได้ประกาศ ถ้าไม่มี id
    # AdminWeb จะแยกไม่ออกว่าแก้ FAQ ข้อไหน (จับคู่ด้วย id)
    id: Optional[str] = None
    icon: Optional[str] = None
    question: str
    answer: str


class CustomFaqCreate(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    answer: str = Field(..., min_length=1, max_length=10000)


class SettingsResponse(BaseModel):
    model_name: str
    temperature: float
    max_tokens: int
    top_k: int
    embedding_tech: str
    system_prompt: Optional[str] = None
    welcome_message: Optional[str] = None
    chat_greeting: Optional[str] = None
    custom_faqs: List[FAQ] = []
    predefined_faqs: List[FAQ] = []
    last_build_duration: Optional[float] = None
    gemini_api_key: Optional[str] = None  # masked on response
    success: bool = True


class SettingsUpdate(BaseModel):
    model_name: Optional[str] = None
    # จำกัดช่วงค่า กันตั้งค่าเกินจนบอทค้างหรือ context ยาวเกินที่โมเดลรับได้
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=8000)
    top_k: Optional[int] = Field(None, ge=1, le=20)
    system_prompt: Optional[str] = None
    welcome_message: Optional[str] = None
    chat_greeting: Optional[str] = None
    custom_faqs: Optional[List[FAQ]] = None
    predefined_faqs: Optional[List[FAQ]] = None
    gemini_api_key: Optional[str] = None


# ─── Document Schemas ──────────────────────────────────────────────────────────

class DocumentResponse(BaseModel):
    filename: str
    display_name: Optional[str] = None
    status: str
    pages: Optional[int] = None
    size: Optional[int] = None
    exclude_pages: List[int] = []
    chunking_duration: Optional[float] = None
    embedding_duration: Optional[float] = None
    upload_date: str
    uploaded_by: Optional[str] = None
    department: Optional[str] = None

    class Config:
        from_attributes = True


# ─── Chat Schemas ──────────────────────────────────────────────────────────────

# ประวัติแชทมาจากเบราว์เซอร์ (UserWeb ส่ง 6 ข้อความล่าสุด) — ตัดให้เหลือขนาดที่ใช้จริง (ตัด ไม่ปฏิเสธ
# เพราะคำตอบของบอทที่ยาวผิดปกติไม่ควรทำให้แชทถัดไปพัง)
CHAT_HISTORY_MAX_MESSAGES = 20
CHAT_MESSAGE_MAX_CHARS = 4000


class ChatMessage(BaseModel):
    sender: Literal["user", "bot"]
    text: str

    @field_validator("text")
    @classmethod
    def _truncate_text(cls, value: str) -> str:
        return value[:CHAT_MESSAGE_MAX_CHARS]


class ChatRequest(BaseModel):
    # จำกัดความยาวคำถาม กัน payload ใหญ่ผิดปกติไปดันต้นทุน LLM API หรือ context เกิน token limit
    query: str = Field(..., max_length=2000)
    history: List[ChatMessage] = []
    session_id: Optional[str] = None

    @field_validator("history")
    @classmethod
    def _keep_recent_history(cls, value: List[ChatMessage]) -> List[ChatMessage]:
        return value[-CHAT_HISTORY_MAX_MESSAGES:]


# ─── Feedback Schemas ──────────────────────────────────────────────────────────

# คนทั่วไปส่งได้โดยไม่ต้องล็อกอิน — จำกัดชนิดและความยาวทุกช่อง
class FeedbackSubmit(BaseModel):
    msgId: str = Field(..., min_length=1, max_length=255)
    rating: Literal["like", "dislike", ""]  # "" = กดยกเลิกถูกใจ/ไม่ถูกใจ
    stars: Optional[int] = Field(None, ge=1, le=5)  # 1-5 จากแบบสอบถามความพึงพอใจภาพรวม
    comment: Optional[str] = Field(None, max_length=2000)
    query: Optional[str] = Field(None, max_length=4000)
    answer: Optional[str] = Field(None, max_length=20000)
    history_id: Optional[str] = Field(None, max_length=255)


class FeedbackResponse(BaseModel):
    id: str
    rating: str
    stars: Optional[int] = None
    comment: Optional[str] = None
    query: Optional[str] = None
    answer: Optional[str] = None
    timestamp: str
    history_id: Optional[str] = None

    class Config:
        from_attributes = True


# ─── Unanswered Schemas ────────────────────────────────────────────────────────

class UnansweredResponse(BaseModel):
    id: str
    query: str
    count: int
    status: str
    timestamp: str
    resolution_type: Optional[str] = None
    ignore_reason: Optional[str] = None
    note: Optional[str] = None
    resolved_by: Optional[str] = None  # display_name ของผู้ปิดรายการ
    resolved_at: Optional[str] = None
    search_keywords: List[str] = []
    department: Optional[str] = None

    class Config:
        from_attributes = True


class UnansweredUpdate(BaseModel):
    """
    status=Pending  → ย้อนสถานะ ล้างข้อมูลการปิดรายการทั้งหมด
    status=Resolved → resolution_type ไม่บังคับ (เผื่อ client เดิมที่ส่งแค่ status)
    status=Ignored  → ต้องระบุ ignore_reason
    resolution_type=search_keywords → ต้องมี search_keywords อย่างน้อย 1 คำ
    """
    status: Literal["Pending", "Resolved", "Ignored"]
    resolution_type: Optional[Literal["custom_faq", "document_upload", "search_keywords"]] = None
    ignore_reason: Optional[Literal["spam", "chit_chat", "out_of_scope", "other"]] = None
    note: Optional[str] = Field(default=None, max_length=1000)
    search_keywords: Optional[List[str]] = Field(default=None, max_length=10)

    @field_validator("search_keywords")
    @classmethod
    def _clean_keywords(cls, v):
        if v is None:
            return v
        cleaned, seen = [], set()
        for kw in v:
            kw = " ".join((kw or "").split())
            if len(kw) > 100:
                raise ValueError("คำค้นยาวเกิน 100 ตัวอักษร")
            if kw and kw.lower() not in seen:
                seen.add(kw.lower())
                cleaned.append(kw)
        return cleaned

    @model_validator(mode="after")
    def _check_status_fields(self):
        if self.status == "Ignored" and not self.ignore_reason:
            raise ValueError("ต้องระบุเหตุผล (ignore_reason) เมื่อเลือกไม่แก้ไข")
        if self.status != "Resolved" and self.resolution_type:
            raise ValueError("resolution_type ใช้ได้เฉพาะ status=Resolved")
        if self.status != "Ignored" and self.ignore_reason:
            raise ValueError("ignore_reason ใช้ได้เฉพาะ status=Ignored")
        if self.resolution_type == "search_keywords" and not self.search_keywords:
            raise ValueError("ต้องระบุคำค้นอย่างน้อย 1 คำ")
        if self.search_keywords and self.resolution_type != "search_keywords":
            raise ValueError("search_keywords ใช้ได้เฉพาะ resolution_type=search_keywords")
        return self


# ─── History Schemas ───────────────────────────────────────────────────────────

class HistoryResponse(BaseModel):
    id: str
    query: Optional[str] = None
    answer: Optional[str] = None
    response_time: Optional[float] = None
    chunk_ids: List[int] = []
    api_model: Optional[str] = None
    referenced_docs: List[str] = []
    cited_docs: Optional[List[str]] = None  # None = แถวเก่าก่อนมีคอลัมน์นี้ (ใช้ referenced_docs แทน)
    timestamp: str


# ─── Stats Schemas ─────────────────────────────────────────────────────────────

class StatsResponse(BaseModel):
    total_queries: int = 0
    total_likes: int = 0
    total_dislikes: int = 0
    total_unanswered: int = 0
    total_documents: int = 0
    active_documents: int = 0
    queries_today: int = 0
    avg_response_time: float = 0.0


# ─── Forms Schemas ─────────────────────────────────────────────────────────────

class FormResponse(BaseModel):
    id: str
    name: str
    filename: Optional[str] = None
    page: Optional[str] = None
    download_link: Optional[str] = None
    link: Optional[str] = None
    department: Optional[str] = None

    class Config:
        from_attributes = True


# ─── Announcements Schemas ─────────────────────────────────────────────────────

class AnnouncementResponse(BaseModel):
    id: int
    title: str
    content: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    category: Optional[str] = None
    created_by: Optional[str] = None
    pinned: bool = False

    class Config:
        from_attributes = True


# ─── Rebuild Schema ────────────────────────────────────────────────────────────

class RebuildStatus(BaseModel):
    status: str  # idle | processing | success | error
    message: str
    duration: Optional[float] = None
