"""
TUH Chatbot AI — Pydantic Schemas
Request/Response models สำหรับ API endpoints
"""
from datetime import datetime
from typing import Optional, List, Any, Literal
from pydantic import BaseModel, Field, field_validator, model_validator

MIN_PASSWORD_LENGTH = 8


def _validate_password_strength(value: str) -> str:
    """นโยบายรหัสผ่านขั้นต่ำ: ยาวอย่างน้อย 8 ตัว (เดิม 4 ตัวสั้นเกินไป เดาง่าย)"""
    if value is None:
        return value
    if len(value) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"รหัสผ่านต้องมีความยาวอย่างน้อย {MIN_PASSWORD_LENGTH} ตัวอักษร")
    return value


# ─── Auth Schemas ──────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    username: str
    display_name: str
    role: str


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ─── User Schemas ──────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str
    password: str
    display_name: str = "Admin"
    role: str = "admin"
    department: Optional[str] = None

    _validate_password = field_validator("password")(_validate_password_strength)


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

    class Config:
        from_attributes = True


# ─── Settings Schemas ──────────────────────────────────────────────────────────

class FAQ(BaseModel):
    # id/icon ต้องมีไว้เสมอ — เดิมมีแค่ question/answer ทำให้ทุกครั้งที่ AdminWeb save settings
    # (ผ่าน /api/admin/settings ซึ่ง parse body ผ่าน FAQ model นี้) id/icon ที่ frontend ส่งมา
    # ถูกตัดทิ้งเงียบๆ (Pydantic ไม่เก็บ field ที่ไม่ได้ประกาศไว้) พอโหลดกลับมาใหม่ทุกรายการเลย
    # ไม่มี id (เป็น None หมด) ทำให้ AdminWeb (App.jsx handleSavePredefinedFaq ที่ match ด้วย
    # `faq.id === selectedPredefinedFaq.id`) จับคู่ None === None ว่าตรงกับทุกแถว เวลาแก้ไข FAQ
    # ข้อเดียวเลยไปทับคำถาม/คำตอบของทุกข้อในรายการพร้อมกันหมด (ข้อมูลเดิมของข้ออื่นหายไม่สามารถกู้คืนได้)
    id: Optional[str] = None
    icon: Optional[str] = None
    question: str
    answer: str


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
    # เดิมไม่มี bound เลย ตั้ง temperature=999 หรือ top_k=100000 จาก UI ได้ (ค้าง LLM/retriever
    # หรือทำให้ context ยาวจนเกิน token limit ของโมเดล) — ใส่ขอบเขตที่สมเหตุสมผลไว้กันไว้
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

    class Config:
        from_attributes = True


class DocumentUpdate(BaseModel):
    status: Optional[str] = None
    exclude_pages: Optional[List[int]] = None
    display_name: Optional[str] = None


# ─── Chat Schemas ──────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    sender: str  # "user" | "bot"
    text: str


class ChatRequest(BaseModel):
    # จำกัดความยาวคำถาม กัน payload ใหญ่ผิดปกติไปดันต้นทุน LLM API หรือ context เกิน token limit
    query: str = Field(..., max_length=2000)
    history: List[ChatMessage] = []
    session_id: Optional[str] = None


class CitationInfo(BaseModel):
    source: str
    pages: List[int]
    display_name: Optional[str] = None
    url: Optional[str] = None


class FormLink(BaseModel):
    name: str
    download_link: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    citations: List[CitationInfo] = []
    form_links: List[FormLink] = []
    used_rag: bool = False
    response_time: float = 0.0
    model: str = ""
    history_id: Optional[str] = None


# ─── Feedback Schemas ──────────────────────────────────────────────────────────

class FeedbackSubmit(BaseModel):
    msgId: str
    rating: str  # like | dislike
    stars: Optional[int] = None  # 1-5 จากแบบสอบถามความพึงพอใจภาพรวม
    comment: Optional[str] = None
    query: Optional[str] = None
    answer: Optional[str] = None
    history_id: Optional[str] = None


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

class UnansweredSubmit(BaseModel):
    query: str


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

    class Config:
        from_attributes = True


class UnansweredUpdate(BaseModel):
    """
    status=Pending  → ย้อนสถานะ ล้างข้อมูลการปิดรายการทั้งหมด
    status=Resolved → resolution_type ไม่บังคับ (เผื่อ client เดิมที่ส่งแค่ status)
    status=Ignored  → ต้องระบุ ignore_reason
    """
    status: Literal["Pending", "Resolved", "Ignored"]
    resolution_type: Optional[Literal["custom_faq", "document_upload", "chunk_hint"]] = None
    ignore_reason: Optional[Literal["spam", "chit_chat", "out_of_scope", "other"]] = None
    note: Optional[str] = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def _check_status_fields(self):
        if self.status == "Ignored" and not self.ignore_reason:
            raise ValueError("ต้องระบุเหตุผล (ignore_reason) เมื่อเลือกไม่แก้ไข")
        if self.status != "Resolved" and self.resolution_type:
            raise ValueError("resolution_type ใช้ได้เฉพาะ status=Resolved")
        if self.status != "Ignored" and self.ignore_reason:
            raise ValueError("ignore_reason ใช้ได้เฉพาะ status=Ignored")
        return self


# ─── RAG Teaching (Chunk Hints) Schemas ────────────────────────────────────────

class RagTestSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)


class RagChunkSearchRequest(BaseModel):
    keyword: str = Field(min_length=1, max_length=200)
    source: Optional[str] = None


class ChunkRef(BaseModel):
    source: str = Field(min_length=1, max_length=255)
    chunk_hash: str = Field(min_length=64, max_length=64)


class ChunkHintSuggestRequest(ChunkRef):
    query: str = Field(default="", max_length=1000)


class ChunkHintSave(ChunkRef):
    questions: List[str] = Field(min_length=1, max_length=10)
    unanswered_id: Optional[str] = None
    verify_query: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("questions")
    @classmethod
    def _check_questions(cls, v):
        for q in v:
            if not (q or "").strip():
                raise ValueError("คำถามตัวอย่างต้องไม่ว่าง")
            if len(q) > 300:
                raise ValueError("คำถามตัวอย่างยาวเกิน 300 ตัวอักษร")
        return v


# ─── History Schemas ───────────────────────────────────────────────────────────

class HistoryResponse(BaseModel):
    id: str
    query: Optional[str] = None
    answer: Optional[str] = None
    response_time: Optional[float] = None
    chunk_ids: List[int] = []
    api_model: Optional[str] = None
    referenced_docs: List[str] = []
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

    class Config:
        from_attributes = True


class FormCreate(BaseModel):
    name: str
    filename: Optional[str] = None
    page: Optional[str] = None
    download_link: Optional[str] = None


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


class AnnouncementCreate(BaseModel):
    title: str
    content: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    category: Optional[str] = None
    pinned: bool = False


class AnnouncementUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    category: Optional[str] = None
    pinned: Optional[bool] = None


# ─── Rebuild Schema ────────────────────────────────────────────────────────────

class RebuildStatus(BaseModel):
    status: str  # idle | processing | success | error
    message: str
    duration: Optional[float] = None
