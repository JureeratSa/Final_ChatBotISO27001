"""
Unit tests: app/services/pdf_highlight.py
ไฮไลท์ข้อความของ chunk ที่ใช้ตอบลงใน PDF (ลิงก์แหล่งอ้างอิง ?hl=<chunk_id,...>)
"""
import fitz

from app.services import pdf_highlight


def test_parse_chunk_ids_dedupes_ignores_junk_and_caps():
    assert pdf_highlight.parse_chunk_ids("125,80,125,abc") == [125, 80]
    assert pdf_highlight.parse_chunk_ids("") == []
    many = ",".join(str(i) for i in range(50))
    assert len(pdf_highlight.parse_chunk_ids(many)) == pdf_highlight.MAX_CHUNKS


class _FakeRetriever:
    bm25_chunks = [
        {"chunk_id": 1, "content": "a", "metadata": {"source": "A.pdf", "page": 1}},
        {"chunk_id": 2, "content": "b", "metadata": {"source": "B.pdf", "page": 1}},
    ]


def test_find_chunks_only_returns_chunks_of_the_requested_document(monkeypatch):
    monkeypatch.setattr(pdf_highlight, "get_retriever", lambda: _FakeRetriever())
    # ขอ chunk 2 ผ่านไฟล์ A.pdf ต้องไม่ได้ (chunk 2 เป็นของ B.pdf)
    assert [c["chunk_id"] for c in pdf_highlight.find_chunks("A.pdf", [1, 2])] == [1]
    assert pdf_highlight.find_chunks("A.pdf", [2]) == []


def test_find_chunks_without_loaded_retriever_returns_empty(monkeypatch):
    monkeypatch.setattr(pdf_highlight, "get_retriever", lambda: None)
    assert pdf_highlight.find_chunks("A.pdf", [1]) == []


def test_highlight_pdf_adds_annotations_for_chunk_lines(tmp_path):
    path = tmp_path / "doc.pdf"
    doc = fitz.open()
    p1 = doc.new_page()
    p1.insert_text((72, 72), "Passwords must be at least eight characters")
    p1.insert_text((72, 100), "Unrelated sentence on the same page")
    p2 = doc.new_page()
    p2.insert_text((72, 72), "Change passwords every ninety days")
    doc.save(path)
    doc.close()

    chunk = {"chunk_id": 9, "metadata": {"source": "doc.pdf", "page": 1},
             "content": "Passwords must be at least eight characters\nChange passwords every ninety days"}
    out = fitz.open(stream=pdf_highlight.highlight_pdf(str(path), [chunk]), filetype="pdf")
    # บรรทัดแรกอยู่หน้า 1 บรรทัดที่สองต่อไปหน้า 2 → ไฮไลท์หน้าละ 1 จุด
    assert len(list(out[0].annots())) == 1
    assert len(list(out[1].annots())) == 1
    # ไฟล์ต้นฉบับบนดิสก์ต้องไม่ถูกแก้
    assert len(list(fitz.open(path)[0].annots())) == 0
