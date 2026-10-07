"""
TUH Chatbot AI — Hybrid Retrieval Engine (ChromaDB Vector + BM25 Lexical + Weighted RRF)
หัวใจหลักของระบบ RAG:
1. Dense Retrieval: ใช้โมเดล BAAI/bge-m3 (1024 มิติ) บันทึกลง ChromaDB เพื่อค้นหาเชิงความหมาย (Semantic Search)
2. Lexical Retrieval: ใช้ PyThaiNLP (newmm) ตัดคำภาษาไทยเพื่อสร้าง BM25 Index ค้นหาคำศัพท์เฉพาะทาง
3. Fusion Engine: ผสานผลลัพธ์ด้วย Weighted Reciprocal Rank Fusion (Dense 0.4 / Lexical 0.6)
"""
import os
import sys
import json
import pickle
import argparse

# ปิดเสียงคำแจ้งเตือนและข้อความล็อกต่าง ๆ ของ Hugging Face และ PyTorch
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_HUB_OFFLINE"] = "1"

try:
    from rank_bm25 import BM25Okapi
    from pythainlp.tokenize import word_tokenize
    HAS_LEXICAL = True
except ImportError:
    HAS_LEXICAL = False


def resolve_chroma_dir(index_dir: str) -> str:
    """ที่เก็บ ChromaDB ของทั้งระบบ (retriever, ลบเอกสาร, rebuild ใช้ฟังก์ชันนี้ร่วมกัน)
    1. env var CHROMA_DB_DIR  2. CHROMA_DB_DIR ใน Backend/.env  3. <index_dir>/chroma_db
    เดิม hardcode path ใต้โฟลเดอร์ผู้ใช้ของเครื่องพัฒนาไว้บน Windows — เครื่องอื่นที่ไม่มี path นั้น
    จะหา ChromaDB ไม่เจอแล้วตกไปใช้ BM25 อย่างเดียวแบบเงียบๆ"""
    path = os.getenv("CHROMA_DB_DIR")
    if not path:
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Backend", ".env")
        if os.path.exists(env_file):
            try:
                from dotenv import dotenv_values
                path = dotenv_values(env_file).get("CHROMA_DB_DIR")
            except ImportError:
                pass
    return path or os.path.join(index_dir, "chroma_db")


def build_indices():
    """
    ฟังก์ชันสำหรับอ่านไฟล์ sample_chunks.json แล้วนำมาสร้างดัชนีค้นหา:
    1. สร้าง ChromaDB Collection ('tuh_collection') ด้วย Dense Embedding (BAAI/bge-m3)
    2. สร้าง BM25 Okapi Index บันทึกเป็นไฟล์ bm25.pkl
    """
    # ตรวจสอบการติดตั้งไลบรารีที่จำเป็น
    missing = []
    if not HAS_LEXICAL:
        missing.extend(["rank-bm25", "pythainlp"])
        
    if missing:
        print("ข้อผิดพลาด: ตรวจพบไลบรารีที่จำเป็นไม่ครบถ้วน!")
        print(f"กรุณาติดตั้งคำสั่ง: pip install {' '.join(missing)}")
        sys.exit(1)

    admin_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(admin_dir)
    chunks_path = os.path.join(base_dir, "sample_chunks.json")
    index_dir = os.path.join(base_dir, "index_db")
    db_settings_path = os.path.join(base_dir, "user", "backend", "db", "db_settings.json")


    print(f"กำลังโหลดข้อมูล chunks จาก: {chunks_path}")
    if not os.path.exists(chunks_path):
        print(f"ข้อผิดพลาด: ไม่พบไฟล์ข้อมูล chunks ที่ {chunks_path}")
        return

    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    if not chunks:
        print("ข้อผิดพลาด: ไฟล์ chunks ว่างเปล่า ไม่มีข้อมูล")
        return

    # โหลดการตั้งค่าเทคโนโลยี
    config = {}
    if os.path.exists(db_settings_path):
        try:
            with open(db_settings_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception:
            pass

    tech = config.get("embedding_tech", "local_chroma")

    print(f"กำลังสกัดเวกเตอร์ด้วยเทคโนโลยี: {tech}")
    os.makedirs(index_dir, exist_ok=True)
    texts = [chunk["content"] for chunk in chunks]

    # --- [ 1. สร้างดัชนีเวกเตอร์ด้วย ChromaDB ] ---
    try:
        import chromadb
    except ImportError:
        print("ไม่พบไลบรารี chromadb กำลังดำเนินการติดตั้งผ่าน pip...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "chromadb"])
        import chromadb

    from sentence_transformers import SentenceTransformer
    dense_model = SentenceTransformer("BAAI/bge-m3")
    embeddings = dense_model.encode(texts, show_progress_bar=True, convert_to_numpy=True, normalize_embeddings=True)

    chroma_dir = resolve_chroma_dir(index_dir)
    chroma_client = chromadb.PersistentClient(path=chroma_dir)
    # เคลียร์คอลเลกชันเดิม
    try:
        chroma_client.delete_collection("tuh_collection")
    except Exception:
        pass
    collection = chroma_client.create_collection("tuh_collection")

    ids = [str(chunk["chunk_id"]) for chunk in chunks]
    metadatas = [chunk["metadata"] for chunk in chunks]

    collection.add(
        ids=ids,
        embeddings=embeddings.tolist(),
        metadatas=metadatas,
        documents=texts
    )
    print(f"บันทึกดัชนี Chroma DB สำเร็จที่: {chroma_dir}")

    # --- [ 2. สร้างดัชนีข้อความด้วย BM25 ] ---
    print("\n ทำ index BM25 ")
    print(" ตัดคำภาษาไทยด้วย PyThaiNLP")
    tokenized_corpus = [word_tokenize(text, keep_whitespace=False) for text in texts]

    # คำนวณสถิติความถี่คำสำหรับ BM25Okapi
    bm25 = BM25Okapi(tokenized_corpus)

    # บันทึกโครงสร้างดัชนีและก้อนข้อความ (Pickle)
    bm25_path = os.path.join(index_dir, "bm25.pkl")
    bm25_data = {
        "bm25_index": bm25,
        "chunks": chunks
    }

    with open(bm25_path, "wb") as f:
        pickle.dump(bm25_data, f)
    print(f"💾 บันทึกดัชนี BM25 สำเร็จที่: {bm25_path}")
    print("\n🎉 จัดทำดัชนี RAG เสร็จสิ้นเรียบร้อยพร้อมใช้งาน!")


def delete_document_from_index(filename: str, index_dir=None, chroma_dir=None, retriever=None) -> int:
    """
    ลบ chunk ทั้งหมดของเอกสาร filename ออกจากดัชนี BM25 (ไฟล์ bm25.pkl บนดิสก์ + instance ที่
    โหลดอยู่ในหน่วยความจำของเซิร์ฟเวอร์ถ้ามี ผ่านพารามิเตอร์ retriever) และ ChromaDB (ลบตรงด้วย
    metadata.source ผ่าน collection.delete()) ทันที ไม่ต้องรอ rebuild ทั้งคลังใหม่และไม่ต้องโหลด
    โมเดล embedding เลย (การลบไม่ต้องเข้ารหัสข้อความใหม่)

    เดิมการลบเอกสารเชื่อมกับ ChromaDB ผ่านการสั่ง rebuild ทั้งคลังใหม่เท่านั้น (ดู
    Admin/rebuild_db.py) ซึ่งอ่านสถานะเอกสาร "Active" จากไฟล์ JSON เดิมที่แยกจากฐานข้อมูลจริง —
    ผลคือลบเอกสารแล้ว vector ยังค้างอยู่ในดัชนีจนกว่าจะมีคนสั่ง rebuild เองอีกที ฟังก์ชันนี้ปิด
    ช่องว่างนั้นโดยลบตรงจุดทันทีที่ลบเอกสาร เรียกจาก Backend/app/routers/admin.py
    (delete_document / delete_document_post)

    คืนค่าจำนวน chunk ที่ลบออกจาก BM25 (ใช้ยืนยันผลได้ตรงๆ)

    chroma_dir: ให้ระบุตรงๆ ได้ (ใช้ในเทส ชี้ไปที่ไดเรกทอรีชั่วคราวแทน path จริงของเซิร์ฟเวอร์)
    ถ้าไม่ระบุ จะ resolve แบบเดียวกับ HybridRetriever.load() ทุกประการ (รวม path hardcode บน
    Windows) เพื่อให้ลบตรง Chroma directory เดียวกับที่ retriever ตัวจริงใช้งานอยู่จริง
    """
    admin_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(admin_dir)
    if index_dir is None:
        index_dir = os.path.join(base_dir, "index_db")
    bm25_path = os.path.join(index_dir, "bm25.pkl")

    removed = 0

    # ─ BM25: อ่าน-กรอง-เขียนทับไฟล์ pickle เสมอ ให้ instance ที่โหลดใหม่ในอนาคตตรงด้วย ─
    if HAS_LEXICAL and os.path.exists(bm25_path):
        with open(bm25_path, "rb") as f:
            bm25_data = pickle.load(f)
        chunks = bm25_data.get("chunks") or []
        remaining = [c for c in chunks if (c.get("metadata") or {}).get("source") != filename]
        removed = len(chunks) - len(remaining)
        if removed:
            new_bm25 = None
            if remaining:
                tokenized_corpus = [word_tokenize(c["content"], keep_whitespace=False) for c in remaining]
                new_bm25 = BM25Okapi(tokenized_corpus)
            with open(bm25_path, "wb") as f:
                pickle.dump({"bm25_index": new_bm25, "chunks": remaining}, f)
            # sync เข้า instance ที่โหลดอยู่ในหน่วยความจำของเซิร์ฟเวอร์ (ถ้ามี) ไม่งั้นแชทที่
            # กำลังทำงานอยู่จะยังเห็นข้อมูลเก่าจนกว่าจะรีสตาร์ตเซิร์ฟเวอร์
            if retriever is not None and getattr(retriever, "is_loaded", False):
                retriever.bm25 = new_bm25
                retriever.bm25_chunks = remaining

    # ─ ChromaDB: persistent client ชี้ path เดียวกับที่ HybridRetriever.load() ใช้ ─
    chroma_path = chroma_dir if chroma_dir is not None else resolve_chroma_dir(index_dir)
    if os.path.exists(chroma_path):
        try:
            import chromadb
            client = chromadb.PersistentClient(path=chroma_path)
            collection = client.get_collection("tuh_collection")
            collection.delete(where={"source": filename})
        except Exception as e:
            print(f"คำเตือน: ลบ vector ออกจาก ChromaDB ไม่สำเร็จ ({e})")

    return removed


def weighted_rrf_score(rank: int, weight: float, rrf_k: int = 60) -> float:
    """คำนวณคะแนน Weighted Reciprocal Rank Fusion (RRF) ของผลลัพธ์หนึ่งรายการ ตามสูตร
    weight * (1 / (rrf_k + rank)) — ใช้กับทั้งฝั่ง dense (ChromaDB, weight=0.4) และ
    lexical (BM25, weight=0.6) ก่อนรวมคะแนนของแต่ละ chunk_id เข้าด้วยกันใน
    HybridRetriever.query() แยกออกมาจาก merge_results() closure เดิมเพื่อให้ unit test
    สูตรได้ตรงๆ โดยไม่ต้องโหลดโมเดล/ดัชนีจริง (ดู UT-09 ใน web_testing/unit/test_ut_rag_logic.py)
    สูตรและพฤติกรรมเดิมทุกกรณี ไม่ได้แก้ logic
    """
    return weight * (1.0 / (rrf_k + rank))


class HybridRetriever:
    """
    คลาส Retriever สำหรับการค้นหาแบบ Hybrid (Dense Vector + Lexical Search)
    โดยประยุกต์ใช้สูตรประมวลผลร่วมแบบถ่วงน้ำหนัก Reciprocal Rank Fusion (RRF)
    """
    
    def __init__(self, index_dir=None):
        admin_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.dirname(admin_dir)
        
        if index_dir is None:
            self.index_dir = os.path.join(base_dir, "index_db")
        else:
            self.index_dir = index_dir

        self.bm25_path = os.path.join(self.index_dir, "bm25.pkl")

        self.model = None
        self.bm25 = None
        self.bm25_chunks = None
        self.is_loaded = False
        self.dense_enabled = True
        self.embedding_tech = "local_chroma"
        self.chroma_client = None
        self.chroma_collection = None

    def load(self):
        """โหลดไฟล์ดัชนีค้นหาเข้าสู่หน่วยความจำ (Lazy Load)"""
        if self.is_loaded:
            return

        # 1. โหลดข้อมูลดัชนีคำสำคัญ BM25 (โหลดเร็ว น้ำหนักเบา)
        print("กำลังโหลดดัชนี BM25...")
        if not os.path.exists(self.bm25_path):
            raise FileNotFoundError(f"ไม่พบดัชนี BM25 ที่ {self.bm25_path} กรุณารันเพื่อประกอบสร้างดัชนีก่อน")
            
        with open(self.bm25_path, "rb") as f:
            bm25_data = pickle.load(f)
            self.bm25 = bm25_data["bm25_index"]
            self.bm25_chunks = bm25_data["chunks"]
        print(" โหลดดัชนี BM25 สำเร็จ")

        # โหลดการตั้งค่าระบบ AI
        admin_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.dirname(admin_dir)
        db_settings_path = os.path.join(base_dir, "user", "backend", "db", "db_settings.json")
        config = {}
        if os.path.exists(db_settings_path):
            try:
                with open(db_settings_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except Exception:
                pass
        self.embedding_tech = config.get("embedding_tech", "local_chroma")

        # 2. โหลดโมเดลเวกเตอร์หนาแน่นและ ChromaDB
        print(f"กำลังโหลดดัชนีเวกเตอร์สำหรับเทคโนโลยี: {self.embedding_tech}")

        chroma_path = resolve_chroma_dir(self.index_dir)
        print(f" ที่เก็บ ChromaDB: {chroma_path}")
        if os.path.exists(chroma_path):
            try:
                import chromadb
                self.chroma_client = chromadb.PersistentClient(path=chroma_path)
                self.chroma_collection = self.chroma_client.get_collection("tuh_collection")
                # ChromaDB กับ BM25 ต้องสร้างจากชุด chunk เดียวกัน ไม่งั้นเลข chunk_id ชี้คนละเนื้อหา
                # (เช่นไปเปิด ChromaDB ชุดเก่าใน index_db/chroma_db เพราะไม่ได้ตั้ง CHROMA_DB_DIR)
                n_dense, n_lex = self.chroma_collection.count(), len(self.bm25_chunks or [])
                if n_lex and n_dense != n_lex:
                    print(f" คำเตือน: ChromaDB มี {n_dense} chunk แต่ BM25 มี {n_lex} chunk — "
                          f"อาจเปิด ChromaDB ผิดชุด ตรวจ CHROMA_DB_DIR ใน Backend/.env หรือสั่ง rebuild")

                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer("BAAI/bge-m3")
                self.dense_enabled = True
                print(" โหลดดัชนีเวกเตอร์ Chroma DB สำเร็จ (เปิดใช้การค้นหาเวกเตอร์หนาแน่น)")
            except Exception as e:
                print(f" คำเตือน: โหลด Chroma DB ล้มเหลว ({e}) ระบบจะทำงานในโหมด Lexical/BM25 เท่านั้น")
                self.dense_enabled = False
        else:
            print(" คำเตือน: ไม่พบโฟลเดอร์ Chroma DB ดัชนีเวกเตอร์หนาแน่นจะออฟไลน์")
            self.dense_enabled = False

        self.is_loaded = True

    def _search_dense(self, query, top_k):
        """ค้นหาข้อมูลโดยหาค่าเวกเตอร์คำจำกัดความเชิงความหมายใกล้เคียง (Semantic Search) บน Chroma DB"""
        # เข้ารหัส Query ด้วย BGE-M3
        query_vector = self.model.encode([query], convert_to_numpy=True, normalize_embeddings=True)[0].tolist()

        # ค้นหาใน Chroma
        results_chroma = self.chroma_collection.query(
            query_embeddings=[query_vector],
            n_results=top_k
        )

        results = []
        if results_chroma and "ids" in results_chroma and len(results_chroma["ids"][0]) > 0:
            ids = results_chroma["ids"][0]
            distances = results_chroma["distances"][0]
            metadatas = results_chroma["metadatas"][0]
            documents = results_chroma["documents"][0]

            for rank, (chunk_id, dist, meta, content) in enumerate(zip(ids, distances, metadatas, documents), start=1):
                # Cosine distance ใน Chroma ปกติมีค่า 0 (ใกล้สุด) ถึง 2 (ไกลสุด)
                # แปลงเป็น similarity score: 1.0 - (dist / 2.0)
                score = 1.0 - (dist / 2.0) if dist is not None else 0.5
                results.append({
                    "chunk_id": int(chunk_id) if str(chunk_id).isdigit() else chunk_id,
                    "content": content,
                    "metadata": meta,
                    "score": float(score),
                    "rank": rank
                })
        return results

    def _search_lexical(self, query, top_k):
        """ค้นหาข้อความแบบอิงคำตรงความถี่คำ (Lexical Keyword Search) บน BM25"""
        # ขยายคำสั่งสืบค้น (Query Expansion) เพื่อรองรับคำพ้องความหมาย (Synonyms) สำหรับการวิเคราะห์แบบ Lexical
        expanded_query = query
        synonyms = {
            "สามี": ["คู่สมรส", "ครอบครัว"],
            "ภรรยา": ["คู่สมรส", "ครอบครัว"],
            "แฟน": ["คู่สมรส", "ครอบครัว"],
            "พ่อ": ["บิดา", "ครอบครัว"],
            "แม่": ["มารดา", "ครอบครัว"],
            "ลูก": ["บุตร", "ครอบครัว"],
            "เบิก": ["สิทธิเบิก", "มีสิทธิได้รับ"],
            "คู่สมรส": ["สามี", "ภรรยา"],
            "บิดา": ["พ่อ"],
            "มารดา": ["แม่"],
            "บุตร": ["ลูก"],
        }
        for word, syns in synonyms.items():
            if word in query:
                expanded_query += " " + " ".join(syns)

        tokenized_query = word_tokenize(expanded_query, keep_whitespace=False)
        scores = self.bm25.get_scores(tokenized_query)
        
        chunk_scores = list(zip(self.bm25_chunks, scores))
        sorted_chunks = sorted(chunk_scores, key=lambda x: x[1], reverse=True)[:top_k]
        
        results = []
        for rank, (chunk, score) in enumerate(sorted_chunks, start=1):
            results.append({
                "chunk_id": chunk["chunk_id"],
                "content": chunk["content"],
                "metadata": chunk["metadata"],
                "score": float(score),
                "rank": rank
            })
        return results

    def query(self, query_str, top_k=5, rrf_k=60):
        """
        ประมวลผลคำค้นหาจากระบบ Hybrid
        โดยทำการผสานระหว่างเวกเตอร์และคำค้นตรงแบบเรียงตามคะแนนอันดับ RRF
        """
        self.load()

        # ค้นหาได้เฉพาะ BM25
        if not self.dense_enabled:
            print(f" ค้นหาเฉพาะแบบคำสำคัญ (BM25): '{query_str}'")
            lexical_results = self._search_lexical(query_str, top_k)
            
            results = []
            for idx, item in enumerate(lexical_results, start=1):
                results.append({
                    "chunk_id": item["chunk_id"],
                    "content": item["content"],
                    "metadata": item["metadata"],
                    "dense_rank": None,
                    "dense_score": None,
                    "lexical_rank": item["rank"],
                    "lexical_score": item["score"],
                    "rrf_score": 1.0 / (rrf_k + item["rank"]),
                    "hybrid_rank": idx
                })
            return results

        # ค้นหาแบบ Hybrid RRF
        pool_size = max(top_k * 2, 20)
        
        dense_results = self._search_dense(query_str, pool_size)
        lexical_results = self._search_lexical(query_str, pool_size)

        rrf_scores = {}
        chunk_map = {}

        # การผสานอันดับด้วยคะแนนถ่วงน้ำหนัก (BM25 = 0.6, Dense = 0.4)
        def merge_results(results, key_prefix, weight):
            for item in results:
                cid = item["chunk_id"]
                rank = item["rank"]
                
                if cid not in rrf_scores:
                    rrf_scores[cid] = 0.0
                    chunk_map[cid] = {
                        "chunk_id": item["chunk_id"],
                        "content": item["content"],
                        "metadata": item["metadata"],
                        "dense_rank": None,
                        "dense_score": None,
                        "lexical_rank": None,
                        "lexical_score": None
                    }
                
                rrf_scores[cid] += weighted_rrf_score(rank, weight, rrf_k)
                chunk_map[cid][f"{key_prefix}_rank"] = rank
                chunk_map[cid][f"{key_prefix}_score"] = item["score"]

        merge_results(dense_results, "dense", 0.4)
        merge_results(lexical_results, "lexical", 0.6)

        # หมายเหตุ (2026-10-07): เอากลไก boost +10 คำสวัสดิการ/phrase match ออกแล้ว — คำว่า "ยา"
        # ไปตรงกับ "โรงพยาบาล" แบบ substring ทำให้ 26/80 คำถามทดสอบโดน boost แล้วถูกตัดเหลือเฉพาะ
        # chunk ที่มี "ยา" (165/310) ความแม่นตกจาก ~92% เหลือ ~81% และดัชนีปัจจุบันมีแต่เอกสาร ISO
        # ไม่มีเอกสารสวัสดิการให้ boost อยู่แล้ว ถ้าจะกลับมาใช้ ให้เทียบเป็นคำเต็ม (ตัดคำด้วย PyThaiNLP)

        # จัดลำดับใหม่ทั้งหมดจากคะแนน RRF สูงสุด
        sorted_cids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

        hybrid_results = []
        for idx, cid in enumerate(sorted_cids[:top_k], start=1):
            item = chunk_map[cid]
            item["rrf_score"] = rrf_scores[cid]
            item["hybrid_rank"] = idx
            hybrid_results.append(item)

        return hybrid_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ระบบค้นหา Hybrid RAG Search (ChromaDB + BM25)")
    parser.add_argument("--build", action="store_true", help="ประมวลผลดัชนีเวกเตอร์และคำค้นจาก sample_chunks.json")
    parser.add_argument("--query", type=str, help="คำค้นหาภาษาไทยสำหรับการทดสอบ")
    parser.add_argument("--top_k", type=int, default=5, help="จำนวนผลลัพธ์ที่จะแสดง (ดีฟอลต์: 5)")
    args = parser.parse_args()

    if args.build:
        build_indices()
    elif args.query:
        retriever = HybridRetriever()
        try:
            results = retriever.query(args.query, top_k=args.top_k)
            print(f"\n🔍 ผลลัพธ์การค้นหาสำหรับคำถาม: '{args.query}'")
            print("=" * 80)
            for idx, res in enumerate(results, 1):
                print(f"ลำดับที่ {idx} | คะแนนผสาน RRF: {res['rrf_score']:.6f}")
                print(f"Chunk ID: {res['chunk_id']} | เอกสารต้นทาง: {res['metadata']['source']} | หน้า: {res['metadata']['page']}")
                print(f"เวกเตอร์ (ChromaDB) - อันดับ: {res['dense_rank']} | คะแนน: {f'{res['dense_score']:.4f}' if res['dense_score'] is not None else 'N/A'}")
                print(f"คำตรง (BM25)    - อันดับ: {res['lexical_rank']} | คะแนน: {f'{res['lexical_score']:.4f}' if res['lexical_score'] is not None else 'N/A'}")
                print("-" * 80)
                
                preview = res['content'].replace('\n', ' ')
                if len(preview) > 180:
                    preview = preview[:180] + "..."
                print(f"เนื้อหา: {preview}")
                print("=" * 80)
        except Exception as e:
            print(f" ค้นหาล้มเหลว: {e}")
    else:
        parser.print_help()
