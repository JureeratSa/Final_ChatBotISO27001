"""
TUH Chatbot AI — SQLAlchemy Models
โครงสร้างตารางฐานข้อมูลทั้งหมดในระบบ TiDB Cloud (MySQL-compatible)
ประกอบด้วย 8 ตารางหลัก:
1. users: บัญชีผู้ดูแลระบบ (Admin Accounts) และสิทธิ์การใช้งาน
2. documents: ข้อมูลเอกสารสวัสดิการสำหรับระบบ RAG
3. settings: การตั้งค่าพารามิเตอร์ AI และสถานะระบบ
4. history: ประวัติการสนทนาระหว่างผู้ใช้กับ Chatbot
5. feedback: คะแนนความพึงพอใจและข้อเสนอแนะจากผู้ใช้
6. unanswered: รายการคำถามที่บอทหาคำตอบไม่พบ
7. forms: รายการแบบฟอร์มสวัสดิการสำหรับดาวน์โหลด
8. announcements: ข่าวประชาสัมพันธ์และ Pop-up หน้าเว็บ
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String, Text, Float, Integer, Boolean, DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.core.config import settings


# ─── 1. Users (Admin Accounts) ──────────────────────────────────────────────────

class User(Base):
    """
    ตาราง users: จัดเก็บบัญชีผู้ดูแลระบบ (Admin)
    - รองรับการแบ่ง Role: 'System Administrator' (สิทธิ์สูงสุด) และ 'Moderator'
    - ใช้ hash_password (bcrypt) สำหรับจัดเก็บ password_hash ปลอดภัย
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="รหัสผู้ใช้ (Primary Key)")
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True, comment="ชื่อผู้ใช้สำหรับเข้าสู่ระบบ")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, comment="รหัสผ่านที่ผ่านการแฮชด้วย bcrypt")
    display_name: Mapped[str] = mapped_column(String(100), nullable=False, default="Admin", comment="ชื่อแสดงผลของแอดมิน")
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="admin", comment="ระดับสิทธิ์ (System Administrator / Moderator)")
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="แผนก/ฝ่ายที่สังกัด")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment="สถานะเปิด/ปิดการใช้งานบัญชี")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="วันเวลาที่สร้างบัญชี")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="วันเวลาที่แก้ไขข้อมูลล่าสุด"
    )


# ─── 2. Documents ───────────────────────────────────────────────────────────────

class Document(Base):
    """
    ตาราง documents: จัดเก็บข้อมูลไฟล์เอกสารสวัสดิการและระเบียบต่างๆ
    - ใช้สำหรับสร้าง Vector Index และ Hybrid Search
    - สถานะ (status):
        * 'Processing' = กำลังประมวลผล / รอดำเนินการ
        * 'Step_Raw_Text' = ดึงข้อความดิบแล้ว รอการ Clean
        * 'Step_Cleaned' = ทำความสะอาดข้อความแล้ว รอการตัด Chunk
        * 'Step_Chunk_Preview' = ตัด Chunk แล้ว รอแอดมินตรวจและอนุมัติ
        * 'Active' = อนุมัติใช้งานจริง นำเข้าสู่ระบบค้นหา RAG
        * 'Inactive' = ปิดการใช้งาน ไม่นำมาค้นหา
        * 'Error' = เกิดข้อผิดพลาดในการประมวลผล
    """
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="รหัสเอกสาร (Primary Key)")
    filename: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True, comment="ชื่อไฟล์เอกสาร (เช่น welfare_manual.pdf)")
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="ชื่อแสดงผลที่เข้าใจง่าย")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Processing", comment="สถานะเอกสารใน Pipeline")
    pages: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="จำนวนหน้าทั้งหมดของไฟล์ PDF")
    size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="ขนาดไฟล์ (Bytes)")
    exclude_pages: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="หน้าที่ต้องการยกเว้นไม่ประมวลผล (คั่นด้วยจุลภาค เช่น 1,3,5)")
    chunking_duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="เวลาที่ใช้ในการตัด Chunk (วินาที)")
    embedding_duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="เวลาที่ใช้ในการทำ Embedding (วินาที)")
    upload_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="วันเวลาที่อัปโหลด")
    uploaded_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="ชื่อผู้อัปโหลด (สำหรับแสดงผลแบบ Cache)")
    uploaded_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="รหัสผู้ใช้งานที่อัปโหลด (Foreign Key เชื่อมกับ users.id)"
    )

    uploader: Mapped[Optional["User"]] = relationship("User", foreign_keys=[uploaded_by_id])


# ─── 3. System Settings ────────────────────────────────────────────────────────

class SystemSettings(Base):
    """
    ตาราง settings: จัดเก็บค่าคอนฟิกกลางของระบบ AI และสถานะการ Rebuild Index
    - มีแถวข้อมูลเดียวเสมอ (id = 'config')
    - ควบคุม System Prompt, Temperature, Model Name, และ FAQ หน้าแรก
    """
    __tablename__ = "settings"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, default="config", comment="รหัสคอนฟิก (ใช้ 'config' เสมอ)")
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, default=settings.DEFAULT_LLM_MODEL, comment="ชื่อโมเดล LLM เช่น google/gemma-4-26b-a4b-it")
    temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.4, comment="ระดับความสร้างสรรค์ของ AI (0.0 - 1.0)")
    max_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=1000, comment="จำนวน Token สูงสุดที่ให้ AI ตอบ")
    top_k: Mapped[int] = mapped_column(Integer, nullable=False, default=3, comment="จำนวน Chunk ที่ดึงมาเป็น Context ใน RAG")
    embedding_tech: Mapped[str] = mapped_column(String(50), nullable=False, default="local_chroma", comment="เทคโนโลยี Vector DB ที่ใช้งาน")
    system_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="คำสั่งควบคุมบุคลิกและบทบาทของ AI (System Prompt)")
    welcome_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="ข้อความต้อนรับเมื่อเปิดหน้าแชท")
    chat_greeting: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="ข้อความตอบรับคำทักทายอัตโนมัติ")
    custom_faqs: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="รายการ Custom FAQ ที่แอดมินกำหนดคำตอบไว้ (JSON String)")
    predefined_faqs: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="รายการ FAQ ปุ่มคำถามด่วนหน้าแรก (JSON String)")
    last_build_duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="เวลาที่ใช้ในการ Rebuild Vector DB ครั้งล่าสุด (วินาที)")
    gemini_api_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="API Key สำหรับเรียก LLM (ถ้าต้องการ override)")
    rebuild_status: Mapped[str] = mapped_column(String(50), nullable=False, default="idle", comment="สถานะ Rebuild: 'idle' | 'processing' | 'success' | 'failed'")
    rebuild_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="ข้อความอธิบายสถานะ Rebuild ล่าสุด")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="วันเวลาที่แก้ไขการตั้งค่าล่าสุด"
    )


# ─── 4. Chat History ───────────────────────────────────────────────────────────

class ChatHistory(Base):
    """
    ตาราง history: เก็บบันทึกประวัติการถาม-ตอบทั้งหมด
    - เก็บเวลาตอบสนอง (response_time) และโมเดลที่ใช้ตอบ
    - เก็บ chunk_ids และ referenced_docs สำหรับลิงก์ไปยังหน้า PDF ต้นฉบับ
    """
    __tablename__ = "history"

    id: Mapped[str] = mapped_column(String(255), primary_key=True, comment="รหัสประวัติ (UUID / Timestamp)")
    query: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="ข้อความคำถามจากผู้ใช้")
    answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="ข้อความคำตอบจากบอท")
    response_time: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="ระยะเวลาที่ใช้ในการประมวลผลคำตอบ (วินาที)")
    chunk_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="รหัส Chunks ที่ถูกดึงมาใช้อ้างอิง (คั่นด้วยจุลภาค)")
    api_model: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="ชื่อโมเดล AI หรือที่มาของคำตอบ (เช่น custom_faq, gemma)")
    referenced_docs: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="รายการเอกสารและเลขหน้าที่ใช้อ้างอิง (JSON String)")
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="วันเวลาที่เกิดบทสนทนา")

    # ความสัมพันธ์แบบ 1-to-Many ไปยังตาราง Feedback
    feedbacks: Mapped[list["Feedback"]] = relationship("Feedback", back_populates="history_entry")


# ─── 5. Feedback ───────────────────────────────────────────────────────────────

class Feedback(Base):
    """
    ตาราง feedback: เก็บคะแนนความพึงพอใจและข้อเสนอแนะจากผู้ใช้
    - rating: 'like' (ชอบ) หรือ 'dislike' (ไม่ชอบ)
    - stars: 1-5 คะแนนจากแบบประเมินความพึงพอใจทั่วไป
    """
    __tablename__ = "feedback"

    id: Mapped[str] = mapped_column(String(255), primary_key=True, comment="รหัส Feedback")
    rating: Mapped[str] = mapped_column(String(50), nullable=False, comment="ผลการประเมิน ('like' หรือ 'dislike')")
    stars: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="คะแนนดาวความพึงพอใจ (1 ถึง 5)")
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="ข้อเสนอแนะเพิ่มเติมหรือเหตุผลการกด Dislike")
    query: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="คำถามที่เกี่ยวข้องกับข้อเสนอแนะนี้")
    answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="คำตอบที่เกี่ยวข้องกับข้อเสนอแนะนี้")
    history_id: Mapped[Optional[str]] = mapped_column(
        String(255), ForeignKey("history.id", ondelete="SET NULL"), nullable=True, comment="รหัสประวัติแชทที่เกี่ยวข้อง (Foreign Key)"
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="วันเวลาที่บันทึกผลประเมิน")

    history_entry: Mapped[Optional["ChatHistory"]] = relationship("ChatHistory", back_populates="feedbacks")


# ─── 6. Unanswered Queries ────────────────────────────────────────────────────

class UnansweredQuery(Base):
    """
    ตาราง unanswered: บันทึกคำถามที่ระบบตอบไม่ได้ หรือหาเอกสารอ้างอิงไม่เจอ
    - count: นับความถี่หากมีคำถามเดียวกันถูกถามซ้ำ
    - status: 'Pending' (รอดำเนินการ), 'Resolved' (แก้ไขแล้ว) หรือ 'Ignored' (ไม่แก้ไข)
    - resolution_type: วิธีที่แอดมินใช้แก้ ('custom_faq' / 'document_upload' / 'chunk_edit')
    - ignore_reason / note: เหตุผลที่ไม่แก้ไข + หมายเหตุอิสระ เก็บไว้ทำสถิติภายหลัง
    """
    __tablename__ = "unanswered"

    id: Mapped[str] = mapped_column(String(255), primary_key=True, comment="รหัสรายการคำถามค้างตอบ")
    query: Mapped[str] = mapped_column(Text, nullable=False, comment="ข้อความคำถามที่ตอบไม่ได้")
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="จำนวนครั้งที่คำถามนี้ถูกถามซ้ำ")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Pending", comment="สถานะ ('Pending' / 'Resolved' / 'Ignored')")
    resolution_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="วิธีแก้ไข ('custom_faq' / 'document_upload' / 'chunk_edit')"
    )
    ignore_reason: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="เหตุผลที่ไม่แก้ไข ('spam' / 'chit_chat' / 'out_of_scope' / 'other')"
    )
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="หมายเหตุจากแอดมินตอนปิดรายการ")
    resolved_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="รหัสผู้ใช้งานที่ปิดรายการ (Foreign Key เชื่อมกับ users.id)"
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="วันเวลาที่ปิดรายการ (Resolved/Ignored)"
    )
    resolver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[resolved_by_id])
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="วันเวลาที่ถูกถามครั้งแรก")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="วันเวลาที่ถูกถามล่าสุด"
    )


# ─── 7. Forms ──────────────────────────────────────────────────────────────────

class Form(Base):
    """
    ตาราง forms: จัดเก็บรายการแบบฟอร์มสวัสดิการสำหรับดาวน์โหลด
    - รองรับการระบุเลขหน้า PDF ที่ตัดแยกไว้เฉพาะสำหรับแบบฟอร์มนั้นๆ
    """
    __tablename__ = "forms"

    id: Mapped[str] = mapped_column(String(255), primary_key=True, comment="รหัสแบบฟอร์ม")
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="ชื่อแบบฟอร์ม (เช่น แบบคำขอรับเงินช่วยเหลือ)")
    filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="ชื่อไฟล์ PDF ต้นฉบับ")
    page: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="หน้าที่ระบุในเอกสาร (เช่น '15-16')")
    download_link: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="URL สำหรับดาวน์โหลดไฟล์แบบฟอร์ม")

    @property
    def link(self) -> Optional[str]:
        return self.download_link


# ─── 8. Announcements ─────────────────────────────────────────────────────────

class Announcement(Base):
    """
    ตาราง announcements: จัดเก็บข่าวประชาสัมพันธ์และประกาศสำคัญ
    - รองรับการปักหมุด (pinned) และกำหนดช่วงเวลาเริ่มต้น-สิ้นสุด
    - เนื้อหา (content) ต้องผ่าน sanitize_html ก่อนบันทึกเพื่อความปลอดภัย
    """
    __tablename__ = "announcements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="รหัสประกาศ (Primary Key)")
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="หัวข้อประกาศ")
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="เนื้อหาประกาศ (HTML Format ที่ผ่าน Sanitization)")
    start_date: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="วันที่เริ่มต้นแสดงประกาศ")
    end_date: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="วันที่สิ้นสุดการแสดงประกาศ")
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="หมวดหมู่ประกาศ")
    created_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="ชื่อผู้สร้างประกาศ (Cache)")
    created_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="รหัสผู้ใช้งานที่สร้างประกาศ (Foreign Key)"
    )
    pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="สถานะการปักหมุดประกาศ (แสดงด้านบนสุด)")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="วันเวลาที่สร้างประกาศ")

    creator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by_id])

