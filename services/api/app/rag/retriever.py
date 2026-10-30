"""
Hybrid Retriever — ค้นหา chunk ที่เกี่ยวกับคำถาม ด้วย 2 วิธีแล้วรวมคะแนน

1. Dense (ความหมาย): แปลงคำถามเป็นเวกเตอร์ด้วย BAAI/bge-m3 แล้วหา chunk ที่ใกล้ที่สุดใน ChromaDB
2. Lexical (คำตรงตัว): ตัดคำไทยด้วย PyThaiNLP แล้วให้คะแนนด้วย BM25
3. รวมผลด้วย Weighted Reciprocal Rank Fusion: คะแนน = น้ำหนัก × 1/(60 + อันดับ)
   น้ำหนัก BM25 = 0.6, Dense = 0.4 แล้วเรียงใหม่จากคะแนนรวม

ดัชนีทั้งสองสร้างพร้อมกันโดย rag/indexer.py — chunk_id ของสองฝั่งต้องมาจากรอบเดียวกันเสมอ
"""
import logging
import os
import pickle

from app.core.config import settings

# ใช้โมเดลที่ดาวน์โหลดไว้แล้วเท่านั้น ไม่ต่ออินเทอร์เน็ตตอนโหลด
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_HUB_OFFLINE"] = "1"

from pythainlp.tokenize import word_tokenize  # noqa: E402
from rank_bm25 import BM25Okapi  # noqa: E402

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "BAAI/bge-m3"
COLLECTION_NAME = "tuh_collection"
DENSE_WEIGHT = 0.4
LEXICAL_WEIGHT = 0.6

# ขยายคำค้นด้วยคำพ้องความหมาย (เฉพาะฝั่ง BM25 ซึ่งต้องเจอคำตรงตัว)
SYNONYMS = {
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


def bm25_path() -> str:
    return os.path.join(settings.INDEX_DB_DIR, "bm25.pkl")


def tokenize(text: str):
    return word_tokenize(text, keep_whitespace=False)


def weighted_rrf_score(rank: int, weight: float, rrf_k: int = 60) -> float:
    return weight * (1.0 / (rrf_k + rank))


def delete_document_from_index(filename: str, retriever=None) -> int:
    """ลบ chunk ของเอกสารนี้ออกจาก BM25 และ ChromaDB ทันที (ไม่ต้อง rebuild ทั้งคลัง)
    คืนจำนวน chunk ที่ลบออกจาก BM25 — ถ้าส่ง retriever ที่โหลดอยู่มา จะอัปเดตในหน่วยความจำด้วย"""
    removed = 0
    if os.path.exists(bm25_path()):
        with open(bm25_path(), "rb") as f:
            data = pickle.load(f)
        chunks = data.get("chunks") or []
        remaining = [c for c in chunks if (c.get("metadata") or {}).get("source") != filename]
        removed = len(chunks) - len(remaining)
        if removed:
            new_bm25 = BM25Okapi([tokenize(c["content"]) for c in remaining]) if remaining else None
            with open(bm25_path(), "wb") as f:
                pickle.dump({"bm25_index": new_bm25, "chunks": remaining}, f)
            if retriever is not None and retriever.is_loaded:
                retriever.bm25 = new_bm25
                retriever.bm25_chunks = remaining

    if os.path.exists(settings.CHROMA_DIR):
        try:
            import chromadb
            client = chromadb.PersistentClient(path=settings.CHROMA_DIR)
            client.get_collection(COLLECTION_NAME).delete(where={"source": filename})
        except Exception as e:
            logger.warning("ลบ vector ของ %s ออกจาก ChromaDB ไม่สำเร็จ: %s", filename, e)
    return removed


class HybridRetriever:
    def __init__(self):
        self.model = None                # SentenceTransformer (bge-m3)
        self.bm25 = None
        self.bm25_chunks = None          # list ของ chunk ทั้งหมด (ลำดับตรงกับ BM25)
        self.chroma_collection = None
        self.dense_enabled = True        # False = ChromaDB ใช้ไม่ได้ ค้นด้วย BM25 อย่างเดียว
        self.is_loaded = False

    def load(self):
        if self.is_loaded:
            return

        if not os.path.exists(bm25_path()):
            raise FileNotFoundError(f"ไม่พบดัชนี BM25 ที่ {bm25_path()} — สั่ง rebuild ในหน้าแอดมินก่อน")
        with open(bm25_path(), "rb") as f:
            data = pickle.load(f)
        self.bm25 = data["bm25_index"]
        self.bm25_chunks = data["chunks"]
        logger.info("โหลดดัชนี BM25 แล้ว (%d chunk)", len(self.bm25_chunks or []))

        try:
            import chromadb
            from sentence_transformers import SentenceTransformer
            client = chromadb.PersistentClient(path=settings.CHROMA_DIR)
            self.chroma_collection = client.get_collection(COLLECTION_NAME)
            n_dense, n_lex = self.chroma_collection.count(), len(self.bm25_chunks or [])
            if n_lex and n_dense != n_lex:
                logger.warning("ChromaDB มี %d chunk แต่ BM25 มี %d — ดัชนีไม่ใช่ชุดเดียวกัน ควรสั่ง rebuild",
                               n_dense, n_lex)
            self.model = SentenceTransformer(EMBEDDING_MODEL)
            self.dense_enabled = True
            logger.info("โหลด ChromaDB แล้ว (%s)", settings.CHROMA_DIR)
        except Exception as e:
            logger.warning("โหลด ChromaDB ไม่สำเร็จ (%s) — ค้นด้วย BM25 อย่างเดียว", e)
            self.dense_enabled = False

        self.is_loaded = True

    def _search_dense(self, query, top_k):
        vector = self.model.encode([query], convert_to_numpy=True, normalize_embeddings=True)[0].tolist()
        found = self.chroma_collection.query(query_embeddings=[vector], n_results=top_k)
        if not found or not found.get("ids") or not found["ids"][0]:
            return []
        rows = zip(found["ids"][0], found["distances"][0], found["metadatas"][0], found["documents"][0])
        results = []
        for rank, (chunk_id, distance, meta, content) in enumerate(rows, start=1):
            # cosine distance ของ Chroma อยู่ช่วง 0 (ใกล้สุด) – 2 (ไกลสุด) → แปลงเป็นความคล้าย 0–1
            score = 1.0 - (distance / 2.0) if distance is not None else 0.5
            results.append({
                "chunk_id": int(chunk_id) if str(chunk_id).isdigit() else chunk_id,
                "content": content,
                "metadata": meta,
                "score": float(score),
                "rank": rank,
            })
        return results

    def _search_lexical(self, query, top_k):
        expanded = query
        for word, synonyms in SYNONYMS.items():
            if word in query:
                expanded += " " + " ".join(synonyms)
        scores = self.bm25.get_scores(tokenize(expanded))
        best = sorted(zip(self.bm25_chunks, scores), key=lambda x: x[1], reverse=True)[:top_k]
        return [
            {"chunk_id": c["chunk_id"], "content": c["content"], "metadata": c["metadata"],
             "score": float(s), "rank": rank}
            for rank, (c, s) in enumerate(best, start=1)
        ]

    def query(self, query_str, top_k=5, rrf_k=60):
        """คืน top_k chunk ที่เกี่ยวข้องที่สุด เรียงตามคะแนน RRF"""
        self.load()

        if not self.dense_enabled:
            return [
                {"chunk_id": r["chunk_id"], "content": r["content"], "metadata": r["metadata"],
                 "dense_rank": None, "dense_score": None,
                 "lexical_rank": r["rank"], "lexical_score": r["score"],
                 "rrf_score": 1.0 / (rrf_k + r["rank"]), "hybrid_rank": i}
                for i, r in enumerate(self._search_lexical(query_str, top_k), start=1)
            ]

        # ดึงจากแต่ละฝั่งมากกว่าที่ต้องการ แล้วค่อยตัดเหลือ top_k หลังรวมคะแนน
        pool_size = max(top_k * 2, 20)
        scores, chunks = {}, {}
        for results, prefix, weight in ((self._search_dense(query_str, pool_size), "dense", DENSE_WEIGHT),
                                        (self._search_lexical(query_str, pool_size), "lexical", LEXICAL_WEIGHT)):
            for item in results:
                cid = item["chunk_id"]
                if cid not in scores:
                    scores[cid] = 0.0
                    chunks[cid] = {"chunk_id": cid, "content": item["content"], "metadata": item["metadata"],
                                   "dense_rank": None, "dense_score": None,
                                   "lexical_rank": None, "lexical_score": None}
                scores[cid] += weighted_rrf_score(item["rank"], weight, rrf_k)
                chunks[cid][f"{prefix}_rank"] = item["rank"]
                chunks[cid][f"{prefix}_score"] = item["score"]

        ranked = sorted(scores, key=lambda cid: scores[cid], reverse=True)[:top_k]
        results = []
        for i, cid in enumerate(ranked, start=1):
            item = chunks[cid]
            item["rrf_score"] = scores[cid]
            item["hybrid_rank"] = i
            results.append(item)
        return results
