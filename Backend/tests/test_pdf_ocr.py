"""
Tests: Admin/pdf_ocr.py — ดึงข้อความ PDF ทีละหน้า และ OCR เฉพาะหน้าที่เป็นภาพสแกน
ไม่เรียก Typhoon OCR จริง (แทน ocr_page_image ด้วยตัวปลอม)
"""
import json

import fitz
import pytest

from Admin import pdf_ocr

TEXT_PAGE = "Information security policy applies to all staff members."


def _make_pdf(path, pages):
    """pages: ข้อความของแต่ละหน้า — None = หน้าว่าง (จำลองหน้าสแกนที่ไม่มีชั้นข้อความ)"""
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        if text:
            page.insert_text((72, 72), text)
    doc.save(str(path))
    doc.close()


@pytest.fixture
def fake_ocr(monkeypatch):
    calls = []

    def _fake(png_bytes, cfg):
        calls.append(len(png_bytes))
        return f"OCR TEXT {len(calls)}"

    monkeypatch.setattr(pdf_ocr, "_ocr_config", lambda: {"TYPHOON_OCR_URL": "u", "TYPHOON_OCR_API_KEY": "k", "TYPHOON_OCR_MODEL": "m"})
    monkeypatch.setattr(pdf_ocr, "ocr_page_image", _fake)
    return calls


def test_text_pages_are_not_sent_to_ocr(tmp_path, fake_ocr):
    pdf = tmp_path / "a.pdf"
    _make_pdf(pdf, [TEXT_PAGE, TEXT_PAGE])
    pages = pdf_ocr.extract_pages(str(pdf))
    assert [p["is_scanned"] for p in pages] == [False, False]
    assert TEXT_PAGE in pages[0]["text"]
    assert fake_ocr == []


def test_scanned_pages_are_ocred_and_cached(tmp_path, fake_ocr):
    pdf = tmp_path / "mixed.pdf"
    _make_pdf(pdf, [TEXT_PAGE, None, None])
    pages = pdf_ocr.extract_pages(str(pdf))
    assert [p["is_scanned"] for p in pages] == [False, True, True]
    assert pages[1]["text"].startswith("OCR TEXT") and pages[2]["text"].startswith("OCR TEXT")
    assert len(fake_ocr) == 2

    # รอบสอง (เช่น rebuild หลังอัปโหลด) ใช้ cache — ไม่เรียก API ซ้ำ
    again = pdf_ocr.extract_pages(str(pdf))
    assert [p["text"] for p in again] == [p["text"] for p in pages]
    assert len(fake_ocr) == 2
    assert set(json.load(open(str(pdf) + ".ocr.json", encoding="utf-8"))["pages"]) == {"2", "3"}


def test_skip_pages_are_not_ocred(tmp_path, fake_ocr):
    pdf = tmp_path / "skip.pdf"
    _make_pdf(pdf, [None, None])
    pages = pdf_ocr.extract_pages(str(pdf), skip_pages=[1])
    assert pages[0]["text"].strip() == ""
    assert pages[1]["text"] == "OCR TEXT 1"
    assert len(fake_ocr) == 1


def test_failed_page_keeps_empty_text_and_is_retried_later(tmp_path, monkeypatch, fake_ocr):
    pdf = tmp_path / "fail.pdf"
    _make_pdf(pdf, [None])

    def _boom(png_bytes, cfg):
        raise RuntimeError("endpoint down")

    monkeypatch.setattr(pdf_ocr, "ocr_page_image", _boom)
    assert pdf_ocr.extract_pages(str(pdf))[0]["text"].strip() == ""

    monkeypatch.setattr(pdf_ocr, "ocr_page_image", lambda png, cfg: "RECOVERED")
    assert pdf_ocr.extract_pages(str(pdf))[0]["text"] == "RECOVERED"


def test_without_config_scanned_pages_stay_empty(tmp_path):
    # conftest ปิด _ocr_config ไว้แล้ว (คืน None)
    pdf = tmp_path / "noconf.pdf"
    _make_pdf(pdf, [None])
    page = pdf_ocr.extract_pages(str(pdf))[0]
    assert page["is_scanned"] is True and page["text"].strip() == ""
    assert not (tmp_path / "noconf.pdf.ocr.json").exists()


def test_clean_ocr_markdown_drops_page_numbers_and_figures_and_converts_tables():
    raw = (
        "<page_number>~ ๓ ~</page_number>\n"
        "๑.๑.๘ หมวกพยาบาล\n"
        "<figure>ภาพหมวกพยาบาลสีขาว</figure>\n"
        "<table><tr><th>ตำแหน่ง</th><th>ขนาด</th></tr><tr><td>ผู้อำนวยการ</td><td>๒.๕</td></tr></table>"
    )
    out = pdf_ocr.clean_ocr_markdown(raw)
    assert "page_number" not in out and "~ ๓ ~" not in out
    assert "ภาพหมวกพยาบาล" not in out
    assert "| ตำแหน่ง | ขนาด |" in out and "| ผู้อำนวยการ | ๒.๕ |" in out
    assert "๑.๑.๘ หมวกพยาบาล" in out


# ─── ตำแหน่งบรรทัด (Tesseract) + ไฮไลท์หน้าสแกน ─────────────────────────────────

FAKE_LINES = [
    {"t": "สวมหมวกพยาบาลสีขาว", "r": [100, 100, 300, 115]},
    {"t": "ติดแถบกำมะหยี่สีดำตามแนวยาว", "r": [100, 120, 320, 135]},
    {"t": "กางเกง", "r": [100, 140, 150, 155]},                     # สั้นเกิน ไม่ไฮไลท์
    {"t": "บรรทัดของหัวข้ออื่นที่ไม่อยู่ใน chunk นี้", "r": [100, 160, 320, 175]},
]


@pytest.fixture
def fake_tess(monkeypatch, fake_ocr):
    calls = []
    monkeypatch.setattr(pdf_ocr, "_tesseract_cmd", lambda: "tesseract")

    def _fake(png_bytes, dpi, cmd):
        calls.append(dpi)
        return FAKE_LINES

    monkeypatch.setattr(pdf_ocr, "ocr_page_lines", _fake)
    return calls


def test_scanned_page_lines_are_cached(tmp_path, fake_tess):
    pdf = tmp_path / "lines.pdf"
    _make_pdf(pdf, [TEXT_PAGE, None])
    pdf_ocr.extract_pages(str(pdf))
    pdf_ocr.extract_pages(str(pdf))
    assert fake_tess == [pdf_ocr.LINES_DPI]           # Tesseract รันครั้งเดียว เฉพาะหน้าสแกน
    assert pdf_ocr.load_page_lines(str(pdf)) == {2: FAKE_LINES}


def test_match_lines_finds_lines_inside_a_merged_paragraph():
    chunk = "*   สำหรับพยาบาลหญิง สวมหมวกพยาบาลสีขาว ติดแถบกำมะหยี่สีดำตามแนวยาว\nกางเกง"
    assert pdf_ocr.match_lines(chunk, FAKE_LINES) == [FAKE_LINES[0]["r"], FAKE_LINES[1]["r"]]


def test_highlight_pdf_marks_scanned_chunk_from_cached_lines(tmp_path, fake_tess):
    from app.services.pdf_highlight import highlight_pdf
    pdf = tmp_path / "hl.pdf"
    _make_pdf(pdf, [TEXT_PAGE, None])
    pdf_ocr.extract_pages(str(pdf))

    chunk = {"chunk_id": 1, "content": "สวมหมวกพยาบาลสีขาว ติดแถบกำมะหยี่สีดำตามแนวยาว",
             "metadata": {"source": "hl.pdf", "page": 2, "is_scanned": True}}
    out = fitz.open(stream=highlight_pdf(str(pdf), [chunk]), filetype="pdf")
    annots = [a.rect for a in out[1].annots()]
    assert len(annots) == 2
    assert all(abs(a.y0 - r["r"][1]) < 2 for a, r in zip(sorted(annots, key=lambda a: a.y0), FAKE_LINES[:2]))
    assert list(out[0].annots()) == []
