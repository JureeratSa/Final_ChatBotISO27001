"""
TUH Chatbot AI — HTML Sanitization Utility
ป้องกัน Stored XSS จากเนื้อหาที่แอดมินกรอกผ่าน CKEditor (เช่น ประกาศ/announcements)
ก่อนเก็บลง DB และก่อนแสดงผลด้วย dangerouslySetInnerHTML ฝั่ง frontend
"""
import nh3

# Whitelist เท่าที่ CKEditor toolbar ของระบบอนุญาตให้ใช้งานจริง (ดู CKEditorWrapper ใน AdminWeb)
_ALLOWED_TAGS = {
    "p", "br", "strong", "b", "em", "i", "u", "s", "strike",
    "ul", "ol", "li",
    "a",
    "table", "thead", "tbody", "tr", "th", "td",
    "span", "div",
}
_ALLOWED_ATTRIBUTES = {
    "a": {"href", "target"},
    "span": {"style"},
    "div": {"style"},
    "td": {"colspan", "rowspan"},
    "th": {"colspan", "rowspan"},
}


def sanitize_html(raw_html: str) -> str:
    """ทำความสะอาด HTML: ตัด <script>, event handler (onerror, onclick ฯลฯ), javascript: URL ออกทั้งหมด"""
    if not raw_html:
        return raw_html
    return nh3.clean(
        raw_html,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRIBUTES,
        url_schemes={"http", "https", "mailto"},
        link_rel="noopener noreferrer",
    )
