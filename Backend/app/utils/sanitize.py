"""
TUH Chatbot AI — HTML Sanitization Utility (XSS Defense)
ป้องกันช่องโหว่ Stored Cross-Site Scripting (XSS) จากเนื้อหาที่แอดมินกรอกผ่าน Rich Text Editor (CKEditor)
เช่น ข้อความประกาศข่าวสาร (Announcements) ก่อนบันทึกลงฐานข้อมูล และก่อนแสดงผลบนหน้าบ้าน
"""
import nh3

# รายการ Tag ที่อนุญาต (Whitelist) ตาม Toolbar ที่ใช้งานใน CKEditor
_ALLOWED_TAGS = {
    "p", "br", "strong", "b", "em", "i", "u", "s", "strike",
    "ul", "ol", "li",
    "a",
    "table", "thead", "tbody", "tr", "th", "td",
    "span", "div",
}

# รายการ Attribute ที่ปลอดภัยและอนุญาตให้ใช้งาน
_ALLOWED_ATTRIBUTES = {
    "a": {"href", "target"},
    "span": {"style"},
    "div": {"style"},
    "td": {"colspan", "rowspan"},
    "th": {"colspan", "rowspan"},
}


def sanitize_html(raw_html: str) -> str:
    """
    ทำความสะอาดโค้ด HTML ด้วยไลบรารี nh3 (Rust-based Sanitizer)
    - ตัดแท็กอันตรายเช่น <script>, <iframe>, <object>, <embed> ทิ้งทั้งหมด
    - ลบ Inline Event Handlers เช่น onclick=, onerror=, onload=
    - กรอง URL Schema ให้อนุญาตเฉพาะ http://, https://, และ mailto: (บล็อก javascript: URLs)
    - เพิ่ม rel="noopener noreferrer" ให้อัตโนมัติสำหรับลิงก์ภายนอก

    Args:
        raw_html (str): ข้อความ HTML ดิบจาก Client
    Returns:
        str: ข้อความ HTML ที่ปลอดภัยพร้อมจัดเก็บลงฐานข้อมูล
    """
    if not raw_html:
        return raw_html
    return nh3.clean(
        raw_html,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRIBUTES,
        url_schemes={"http", "https", "mailto"},
        link_rel="noopener noreferrer",
    )

