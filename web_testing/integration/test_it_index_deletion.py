"""
Integration Test — Index Deletion Mechanism (IT-02, ส่วนเสริม)
เทส Admin.emb.delete_document_from_index() ตรงๆ (ไม่ผ่าน HTTP endpoint, ไม่ใช่ async) — พิสูจน์ว่า
ฟังก์ชันที่ปิดช่องว่าง "ลบเอกสารแล้ว ChromaDB ยังไม่ถูกลบจริง" ทำงานถูกต้องจริง ด้วย BM25 pickle +
ChromaDB collection ของจริง (ไม่ mock) แต่ชี้ไปที่ tmp_path เท่านั้น

**คำเตือนสำคัญ**: เครื่องนี้มี ChromaDB/BM25 ของจริงอยู่ 2 ชุด (ชุดที่ตั้งใน
CHROMA_DB_DIR ของ Backend/.env ซึ่ง HybridRetriever ใช้จริง กับ "<repo>/index_db/"
ที่เป็น default เวลาไม่ระบุ index_dir) ทั้งสองมีข้อมูลจริงอยู่ — เทสนี้จึงต้องส่ง index_dir และ
chroma_dir แบบระบุตรงๆ เสมอ (ชี้ไปที่ tmp_path) ห้ามเรียกฟังก์ชันแบบไม่ระบุพารามิเตอร์เหล่านี้ที่นี่
เด็ดขาด เพราะจะไป resolve เป็น path จริงที่มีข้อมูลจริงอยู่ (ดู web_testing/integration/
test_it_documents.py ซึ่งเทสฝั่ง HTTP endpoint ด้วยการ mock ฟังก์ชันนี้แทน)
"""
import pickle


def test_IT02_delete_document_from_index_removes_matching_chunks_only(tmp_path):
    import chromadb

    index_dir = tmp_path / "index_db"
    index_dir.mkdir()
    chroma_dir = index_dir / "chroma_db"

    # ─ เตรียม BM25 pickle จำลอง มี chunk จาก 2 ไฟล์ปน ─
    chunks = [
        {"chunk_id": 1, "content": "นโยบายการลาป่วยของโรงพยาบาล", "metadata": {"source": "annual_report.pdf", "page": 1}},
        {"chunk_id": 2, "content": "รายงานงบประมาณประจำปี", "metadata": {"source": "annual_report.pdf", "page": 2}},
        {"chunk_id": 3, "content": "ขั้นตอนการขอฟอร์มเบิกค่ารักษา", "metadata": {"source": "welfare.pdf", "page": 1}},
    ]
    bm25_path = index_dir / "bm25.pkl"
    with open(bm25_path, "wb") as f:
        pickle.dump({"bm25_index": None, "chunks": chunks}, f)

    # ─ เตรียม ChromaDB collection จำลอง มี document จาก 2 ไฟล์ปนเช่นกัน ─
    client = chromadb.PersistentClient(path=str(chroma_dir))
    collection = client.create_collection("tuh_collection")
    collection.add(
        ids=["1", "2", "3"],
        embeddings=[[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]],
        metadatas=[c["metadata"] for c in chunks],
        documents=[c["content"] for c in chunks],
    )
    assert collection.count() == 3
    del client, collection  # ปิด handle ก่อนให้ delete_document_from_index() เปิดของตัวเอง

    from Admin.emb import delete_document_from_index

    removed = delete_document_from_index(
        "annual_report.pdf", index_dir=str(index_dir), chroma_dir=str(chroma_dir)
    )

    # BM25: เหลือแค่ chunk ของ welfare.pdf
    assert removed == 2
    with open(bm25_path, "rb") as f:
        remaining = pickle.load(f)["chunks"]
    assert [c["metadata"]["source"] for c in remaining] == ["welfare.pdf"]

    # ChromaDB: chunk ของ annual_report.pdf ต้องหายไปจริง เหลือแค่ของ welfare.pdf
    verify_client = chromadb.PersistentClient(path=str(chroma_dir))
    verify_collection = verify_client.get_collection("tuh_collection")
    assert verify_collection.count() == 1
    remaining_docs = verify_collection.get()
    assert remaining_docs["metadatas"][0]["source"] == "welfare.pdf"


def test_IT02_delete_document_from_index_no_ops_safely_when_nothing_indexed_yet(tmp_path):
    """EG — เรียกลบก่อนที่จะมี BM25/ChromaDB อยู่เลย (เอกสารแรกสุดของระบบที่ยังไม่เคย build index)
    ต้องไม่ error ไม่ใช่แค่ happy path"""
    from Admin.emb import delete_document_from_index

    index_dir = tmp_path / "empty_index_db"
    removed = delete_document_from_index(
        "never-indexed.pdf", index_dir=str(index_dir), chroma_dir=str(index_dir / "chroma_db")
    )
    assert removed == 0


def test_IT02_delete_document_from_index_syncs_already_loaded_retriever_in_memory(tmp_path):
    """ถ้ามี HybridRetriever โหลดอยู่ในหน่วยความจำแล้ว (เซิร์ฟเวอร์กำลังรันอยู่จริง) ต้อง sync
    bm25/bm25_chunks ของ instance นั้นด้วย ไม่ใช่แค่เขียนไฟล์ pickle เฉยๆ — ไม่งั้นแชทที่กำลัง
    ทำงานอยู่จะยังเห็นข้อมูลเก่าจนกว่าจะรีสตาร์ตเซิร์ฟเวอร์"""
    import chromadb
    from Admin.emb import HybridRetriever, delete_document_from_index

    index_dir = tmp_path / "index_db"
    index_dir.mkdir()
    chroma_dir = index_dir / "chroma_db"

    chunks = [
        {"chunk_id": 1, "content": "นโยบายการลาป่วย", "metadata": {"source": "annual_report.pdf", "page": 1}},
        {"chunk_id": 2, "content": "ขั้นตอนขอฟอร์มเบิกค่ารักษา", "metadata": {"source": "welfare.pdf", "page": 1}},
    ]
    with open(index_dir / "bm25.pkl", "wb") as f:
        pickle.dump({"bm25_index": None, "chunks": chunks}, f)

    client = chromadb.PersistentClient(path=str(chroma_dir))
    client.create_collection("tuh_collection")
    del client

    # จำลอง retriever ที่ "โหลดอยู่แล้ว" (ไม่ได้เรียก .load() จริงเพื่อเลี่ยงโหลดโมเดล embedding)
    fake_retriever = HybridRetriever(index_dir=str(index_dir))
    fake_retriever.is_loaded = True
    fake_retriever.bm25_chunks = chunks
    fake_retriever.bm25 = "ของเดิมก่อนลบ (placeholder เทียบว่าถูกแทนที่จริง)"

    delete_document_from_index(
        "annual_report.pdf", index_dir=str(index_dir), chroma_dir=str(chroma_dir), retriever=fake_retriever
    )

    assert [c["metadata"]["source"] for c in fake_retriever.bm25_chunks] == ["welfare.pdf"]
    assert fake_retriever.bm25 != "ของเดิมก่อนลบ (placeholder เทียบว่าถูกแทนที่จริง)"
