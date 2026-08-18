"""
TUH Chatbot AI — Pydantic Schemas
Request/Response models สำหรับ API endpoints
"""
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, field_validator


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


class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    id: int
    username: str
    display_name: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Settings Schemas ──────────────────────────────────────────────────────────

class FAQ(BaseModel):
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


class SettingsUpdate(BaseModel):
    model_name: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_k: Optional[int] = None
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
    query: str
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
    comment: Optional[str] = None
    query: Optional[str] = None
    answer: Optional[str] = None
    history_id: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: str
    rating: str
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

    class Config:
        from_attributes = True


class UnansweredUpdate(BaseModel):
    status: str  # Pending | Resolved


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
    pinned: bool = False

    class Config:
        from_attributes = True


class AnnouncementCreate(BaseModel):
    title: str
    content: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    pinned: bool = False


class AnnouncementUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    pinned: Optional[bool] = None


# ─── Rebuild Schema ────────────────────────────────────────────────────────────

class RebuildStatus(BaseModel):
    status: str  # idle | processing | success | error
    message: str
    duration: Optional[float] = None
