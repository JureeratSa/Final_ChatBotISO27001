"""ทำความสะอาดข้อความภาษาไทยที่ดึงจาก PDF ก่อนแบ่ง chunk"""
import re

THAI_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")


def replace_thai_numbers(text):
    """แปลงเลขไทยเป็นเลขอารบิก และรวมสระอำที่ PDF แยกออกเป็น "ํ า" กลับเป็น "ำ"
    (ให้ค้นด้วยตัวเลขอารบิกเจอ และตัดคำได้ถูก)"""
    if not isinstance(text, str):
        return text
    text = text.translate(THAI_DIGITS)
    return re.sub(r'\s+([่-๋]?)\s*า', r'\1ำ', text)
