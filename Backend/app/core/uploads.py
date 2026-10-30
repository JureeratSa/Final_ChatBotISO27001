"""
TUH Chatbot AI — อ่านไฟล์อัปโหลดแบบจำกัดขนาด + ตรวจว่าเป็น PDF จริง (security audit M2, M3)
เดิมอ่าน body ทั้งก้อนเข้าหน่วยความจำโดยไม่มีเพดาน และเช็คแค่นามสกุล .pdf (แบบฟอร์มไม่เช็คเลย)
— ไฟล์ใหญ่มากทำให้ backend หน่วยความจำหมด และไฟล์ที่ไม่ใช่ PDF (เช่น .html) ถูกเก็บแล้วเสิร์ฟต่อได้
"""
from typing import Optional

from fastapi import HTTPException, Request, UploadFile, status

PDF_MAGIC = b"%PDF-"
_CHUNK = 1024 * 1024


def _too_large(max_bytes: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        detail=f"ไฟล์ใหญ่เกิน {max_bytes // (1024 * 1024)} MB",
    )


async def read_request_body(request: Request, max_bytes: int) -> bytes:
    """อ่าน body ดิบทีละชิ้น หยุดทันทีเมื่อเกินเพดาน (ไม่อ่านไฟล์ใหญ่ทั้งก้อนเข้าหน่วยความจำก่อนเช็ค)"""
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > max_bytes:
        raise _too_large(max_bytes)
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > max_bytes:
            raise _too_large(max_bytes)
        chunks.append(chunk)
    return b"".join(chunks)


async def read_upload_file(file: UploadFile, max_bytes: int) -> bytes:
    chunks, size = [], 0
    while True:
        chunk = await file.read(_CHUNK)
        if not chunk:
            break
        size += len(chunk)
        if size > max_bytes:
            raise _too_large(max_bytes)
        chunks.append(chunk)
    return b"".join(chunks)


def require_pdf(content: bytes, filename: Optional[str] = None) -> None:
    """นามสกุล .pdf และเนื้อไฟล์ขึ้นต้นด้วย %PDF- (กันไฟล์อื่นที่เปลี่ยนชื่อมาเป็น .pdf)"""
    if filename is not None and not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="รองรับเฉพาะไฟล์ PDF เท่านั้น")
    # มาตรฐานอนุญาตให้มีขยะก่อน header ได้เล็กน้อย — หาในช่วง 1 KB แรก
    if PDF_MAGIC not in content[:1024]:
        raise HTTPException(status_code=400, detail="ไฟล์นี้ไม่ใช่ PDF (เนื้อไฟล์ไม่ตรงกับรูปแบบ PDF)")
