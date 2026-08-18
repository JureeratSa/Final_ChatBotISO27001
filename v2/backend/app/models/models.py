"""
TUH Chatbot AI — SQLAlchemy Models
ตาราง: users (Admin Accounts), documents, settings, feedback, unanswered, history, forms, announcements
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String, Text, Float, Integer, Boolean, DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


# ─── Users (Admin Accounts) ────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False, default="Admin")
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="admin")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ─── Documents ─────────────────────────────────────────────────────────────────

class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Processing")
    # status: Active | Inactive | Processing | Error
    pages: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # bytes
    exclude_pages: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # comma-separated
    chunking_duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    embedding_duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    upload_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ─── Settings ──────────────────────────────────────────────────────────────────

class SystemSettings(Base):
    __tablename__ = "settings"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, default="config")
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, default="google/gemini-2.5-flash")
    temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.4)
    max_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=1000)
    top_k: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    embedding_tech: Mapped[str] = mapped_column(String(50), nullable=False, default="bge-m3")
    system_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    welcome_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    chat_greeting: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    custom_faqs: Mapped[Optional[str]] = mapped_column(Text, nullable=True)     # JSON string
    predefined_faqs: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    last_build_duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ─── Chat History ──────────────────────────────────────────────────────────────

class ChatHistory(Base):
    __tablename__ = "history"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    query: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_time: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    chunk_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # comma-separated
    api_model: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    referenced_docs: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationship to feedback
    feedbacks: Mapped[list["Feedback"]] = relationship("Feedback", back_populates="history_entry")


# ─── Feedback ──────────────────────────────────────────────────────────────────

class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    rating: Mapped[str] = mapped_column(String(50), nullable=False)  # like | dislike
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    query: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    history_id: Mapped[Optional[str]] = mapped_column(
        String(255), ForeignKey("history.id", ondelete="SET NULL"), nullable=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    history_entry: Mapped[Optional["ChatHistory"]] = relationship("ChatHistory", back_populates="feedbacks")


# ─── Unanswered Queries ────────────────────────────────────────────────────────

class UnansweredQuery(Base):
    __tablename__ = "unanswered"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Pending")
    # status: Pending | Resolved
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ─── Forms (สำหรับแบบฟอร์มดาวน์โหลด) ──────────────────────────────────────────

class Form(Base):
    __tablename__ = "forms"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    page: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    download_link: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)


# ─── Announcements ─────────────────────────────────────────────────────────────

class Announcement(Base):
    __tablename__ = "announcements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_date: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    end_date: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
