import os
import sys
import json
import pickle
import argparse

# ปิดเสียงคำแจ้งเตือนและข้อความล็อกต่าง ๆ ของ Hugging Face และ PyTorch
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_HUB_OFFLINE"] = "1"

# --- [ ตรวจสอบไลบรารีภายนอกสำหรับระบบ Hybrid Retrieval ] ---
try:
    import faiss
    from sentence_transformers import SentenceTransformer
    HAS_DENSE = True
except ImportError:
    HAS_DENSE = False

try:
    from rank_bm25 import BM25Okapi
    from pythainlp.tokenize import word_tokenize
    HAS_LEXICAL = True
except ImportError:
    HAS_LEXICAL = False


def build_indices():
    """
    ฟังก์ชันสำหรับอ่านไฟล์ chunks แล้วนำมาสร้างดัชนีค้นหา:
    1. Vector Index โมเดล BAAI/bge-m3 และ FAISS
    2. คำสำคัญ BM25 Index ใช้ PyThaiNLP
    """
    # ตรวจสอบการติดตั้งไลบรารีที่จำเป็น
    missing = []
    if not HAS_DENSE:
        missing.extend(["faiss-cpu", "sentence-transformers"])
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

    print(f"กำลังโหลดข้อมูล chunks จาก: {chunks_path}")
    if not os.path.exists(chunks_path):
        print(f"ข้อผิดพลาด: ไม่พบไฟล์ข้อมูล chunks ที่ {chunks_path}")
        return

    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    if not chunks:
        print("ข้อผิดพลาด: ไฟล์ chunks ว่างเปล่า ไม่มีข้อมูล")
        return

    print(f"โหลดสำเร็จ: ทั้งหมด {len(chunks)} chunks")
    os.makedirs(index_dir, exist_ok=True)

    texts = [chunk["content"] for chunk in chunks]

    # --- [ 1. สร้างดัชนีเวกเตอร์ด้วย FAISS ] ---
    print("\n  โมเดล BAAI/bge-m3 ")
    model_name = "BAAI/bge-m3"
    dense_model = SentenceTransformer(model_name)

    print(" Embeddings ")
    embeddings = dense_model.encode(texts, show_progress_bar=True, convert_to_numpy=True, normalize_embeddings=True)
    print(" Normalization ")
    faiss.normalize_L2(embeddings)
    dimension = embeddings.shape[1]
    faiss_index = faiss.IndexFlatIP(dimension)
    faiss_index.add(embeddings)
    faiss_index_path = os.path.join(index_dir, "faiss.index")
    faiss_meta_path = os.path.join(index_dir, "faiss_metadata.json")
    faiss.write_index(faiss_index, faiss_index_path)
    with open(faiss_meta_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    print(f"บันทึกดัชนี FAISS สำเร็จที่: {index_dir}")

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

        self.faiss_index_path = os.path.join(self.index_dir, "faiss.index")
        self.faiss_meta_path = os.path.join(self.index_dir, "faiss_metadata.json")
        self.bm25_path = os.path.join(self.index_dir, "bm25.pkl")

        self.model = None
        self.faiss_index = None
        self.faiss_chunks = None
        self.bm25 = None
        self.bm25_chunks = None
        self.is_loaded = False
        self.dense_enabled = True

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

        # 2. โหลดโมเดลเวกเตอร์หนาแน่นและข้อมูล FAISS
        print(" โหลด FAISS และ SentenceTransformer")
        if HAS_DENSE and os.path.exists(self.faiss_index_path) and os.path.exists(self.faiss_meta_path):
            try:
                self.model = SentenceTransformer("BAAI/bge-m3")
                self.faiss_index = faiss.read_index(self.faiss_index_path)
                with open(self.faiss_meta_path, "r", encoding="utf-8") as f:
                    self.faiss_chunks = json.load(f)
                self.dense_enabled = True
                print(" โหลดดัชนีเวกเตอร์ FAISS สำเร็จ (เปิดใช้การค้นหาเวกเตอร์หนาแน่น)")
            except Exception as e:
                print(f" คำเตือน: โหลด FAISS ล้มเหลว ({e}) ระบบจะทำงานในโหมด Lexical/BM25 เท่านั้น")
                self.dense_enabled = False
        else:
            print(" คำเตือน: ไลบรารีเวกเตอร์หนาแน่นไม่พบหรือไฟล์ดัชนีไม่มี ระบบจะสลับไปทำงานเฉพาะ BM25 เท่านั้น")
            self.dense_enabled = False

        self.is_loaded = True

    def _search_dense(self, query, top_k):
        """ค้นหาข้อมูลโดยหาค่าเวกเตอร์คำจำกัดความเชิงความหมายใกล้เคียง (Semantic Search) บน FAISS"""
        query_vector = self.model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
        faiss.normalize_L2(query_vector)

        scores, indices = self.faiss_index.search(query_vector, top_k)
        
        results = []
        for rank, (score, idx) in enumerate(zip(scores[0], indices[0]), start=1):
            if idx != -1:
                chunk = self.faiss_chunks[idx]
                results.append({
                    "chunk_id": chunk["chunk_id"],
                    "content": chunk["content"],
                    "metadata": chunk["metadata"],
                    "score": float(score),
                    "rank": rank
                })
        return results

    def _search_lexical(self, query, top_k):
        """ค้นหาข้อความแบบอิงคำตรงความถี่คำ (Lexical Keyword Search) บน BM25"""
        tokenized_query = word_tokenize(query, keep_whitespace=False)
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
                
                rrf_scores[cid] += weight * (1.0 / (rrf_k + rank))
                chunk_map[cid][f"{key_prefix}_rank"] = rank
                chunk_map[cid][f"{key_prefix}_score"] = item["score"]

        merge_results(dense_results, "dense", 0.4)
        merge_results(lexical_results, "lexical", 0.6)

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
    parser = argparse.ArgumentParser(description="ระบบค้นหา Hybrid RAG Search (FAISS + BM25)")
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
                print(f"เวกเตอร์ (FAISS) - อันดับ: {res['dense_rank']} | คะแนน: {f'{res['dense_score']:.4f}' if res['dense_score'] is not None else 'N/A'}")
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
