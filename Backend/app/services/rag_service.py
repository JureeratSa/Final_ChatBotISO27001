"""
TUH Chatbot AI — RAG Service
คง Logic เดิมทั้งหมด: HybridRetriever (ChromaDB + BM25 + Weighted RRF)
Wraps existing Admin/emb.py as an async-compatible service
"""
import os
import re
import sys
import json
import time
import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)


# ─── Global Retriever State ───────────────────────────────────────────────────

_retriever = None
_retriever_loaded = False

def get_retriever():
    """ดึง HybridRetriever instance (singleton)"""
    global _retriever
    return _retriever


def load_retriever():
    """โหลด HybridRetriever จาก index_db ที่มีอยู่"""
    global _retriever, _retriever_loaded
    try:
        # เพิ่ม path ของ Admin directory
        admin_dir = str(Path(settings.ADMIN_DIR).parent)
        if admin_dir not in sys.path:
            sys.path.insert(0, admin_dir)

        from Admin.emb import HybridRetriever
        retriever = HybridRetriever()
        retriever.load()
        _retriever = retriever
        _retriever_loaded = True
        logger.info("[RAG] HybridRetriever loaded successfully")
        return True
    except Exception as e:
        logger.warning("[RAG] Warning: Could not load HybridRetriever: %s", e)
        _retriever = None
        _retriever_loaded = False
        return False


def reload_retriever():
    """โหลด retriever ใหม่หลัง rebuild index"""
    return load_retriever()


# ─── Profanity & Chit-chat Detection (คง Logic เดิม) ─────────────────────────

def contains_profanity(text: str) -> bool:
    if not text:
        return False
    text_lower = text.lower()
    temp_text = re.sub(r'[\s\.\-\_\,\#\*\(\)\{\}\[\]\?\!\/\\\+\=\~\`\"\':\;\u200b]+', '', text_lower)
    temp_text = temp_text.replace("เหี้ยม", "")
    exceptions_gu = ["กูเกิ้ล", "กูเกิล", "กูรู", "กูเกิลแมพ", "กูเกิ้ลแมพ"]
    for exc in exceptions_gu:
        temp_text = temp_text.replace(exc, "")
    rude_keywords = [
        "มึง", "เหี้ย", "ควย", "เย็ด", "สัส", "ระยำ", "อัปรีย์", "จัญไร", "ตอแหล",
        "ฉิบหาย", "ชิบหาย", "เสือก", "ไอ้สัตว์", "อีสัตว์", "อีสัด", "กู"
    ]
    for word in rude_keywords:
        if word in temp_text:
            return True
    return False


def is_chit_chat(text: str) -> bool:
    if not text:
        return False
    q = text.strip().lower()
    clean_q = re.sub(r'[^\u0e01-\u0e5b\w\s]', '', q).strip()
    roots = [
        "ขอบคุณ", "ขอบใจ", "สวัสดี", "ยินดี", "ขอบคุน", "ขอบคุญ",
        "thank", "thx", "ty", "hello", "hi", "hey", "bye",
        "แต๊ง", "แต้ง", "แตงกิ้ว", "กิ้ว", "โอเค", "ok", "okay"
    ]
    if len(clean_q) <= 25:
        for r in roots:
            if r in clean_q:
                return True
    return False


# ─── Fallback Answer ──────────────────────────────────────────────────────────

def get_fallback_vector_answer(results: List[Dict]) -> str:
    """คำตอบสำรองเมื่อ AI ออฟไลน์"""
    if results:
        top_res = results[0]
        top_content = (
            top_res['metadata'].get('raw_table')
            if top_res['metadata'].get('type') == 'table' and 'raw_table' in top_res['metadata']
            else top_res['content']
        )
        source = top_res['metadata'].get('source', 'เอกสาร')
        page = top_res['metadata'].get('page', '')
        page_str = f" หน้า {page}" if page else ""
        return (
            f" **(เซิร์ฟเวอร์ AI ออฟไลน์ - แสดงข้อความอ้างอิงที่มีความใกล้เคียงที่สุด)**\n\n"
            f"📄 **เอกสารอ้างอิงหลัก ({source}{page_str}):**\n{top_content}"
        )
    return "สวัสดีครับ ขณะนี้ระบบ AI ออฟไลน์ กรุณาติดต่อเจ้าหน้าที่โดยตรงครับ"


# ─── HTTP POST Utility ────────────────────────────────────────────────────────

def make_http_post(url: str, payload: dict, headers: dict = None, timeout: int = 15) -> dict:
    import urllib.request
    if headers is None:
        headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


# ─── Context Cleaner ──────────────────────────────────────────────────────────

def clean_appended_metadata(text: str) -> str:
    if not text:
        return text
    markers = [
        "\n\n🔗 **แบบฟอร์มที่เกี่ยวข้อง",
        "\n\n---\nเอกสารอ้างอิง:",
        "\n---\nเอกสารอ้างอิง:",
        "\n\n---\nCitations:",
        "\n\nเอกสารอ้างอิง:",
        "\n\n---"
    ]
    cleaned = text
    for marker in markers:
        if marker in cleaned:
            cleaned = cleaned.split(marker)[0]
    return cleaned.strip()


# ─── Main RAG Query Function ───────────────────────────────────────────────────

async def query_rag(
    query: str,
    results: List[Dict],
    config: Dict,
    history: List,
    forms: List = None
) -> Tuple[str, bool, str]:
    """
    สร้างคำตอบด้วย OpenRouter API (หรือ Ollama fallback)
    Returns: (answer_text, used_rag_bool, model_name)
    """
    # ─ ตรวจ Profanity ─
    if contains_profanity(query):
        return (
            "ขออภัยครับ ไม่สามารถตอบคำถามที่ใช้ภาษาไม่สุภาพได้ กรุณาใช้ภาษาที่สุภาพครับ",
            False,
            "profanity_filter"
        )

    # ─ ตรวจ Chit-chat ─
    if is_chit_chat(query):
        return (
            "ขอบคุณครับ! มีคำถามเกี่ยวกับสวัสดิการหรือข้อมูลโรงพยาบาลธรรมศาสตร์ฯ สามารถสอบถามได้เลยนะครับ 😊",
            False,
            "chit_chat"
        )

    # ─ สร้าง Context จาก RAG results ─
    context = ""
    if results:
        context_parts = []
        # ใส่เลข [n] หน้าแต่ละชิ้น ให้ LLM บอกกลับมาได้ว่าใช้ชิ้นไหนตอบจริง (ดู split_used_sources)
        for n, r in enumerate(results, start=1):
            source = r['metadata'].get('source', 'เอกสารอ้างอิง')
            page = r['metadata'].get('page', '')
            page_str = f" หน้า {page}" if page else ""
            content = (
                r['metadata'].get('raw_table', r['content'])
                if r['metadata'].get('type') == 'table'
                else r['content']
            )
            context_parts.append(f"[{n}] แหล่งที่มา: {source}{page_str}\nเนื้อหา: {content}")
        context = "\n---\n".join(context_parts)

    # ─ System Prompt ─
    system_prompt = config.get("system_prompt", _default_system_prompt())

    # ─ เพิ่ม Forms ใน System Prompt ─
    if forms:
        forms_info = "รายชื่อแบบฟอร์มสวัสดิการที่ระบบสนับสนุนการดาวน์โหลดตรง:\n"
        for f in forms:
            name = getattr(f, 'name', '') or f.get('name', '') if isinstance(f, dict) else f.name
            if name:
                forms_info += f"- {name}\n"
        system_prompt += f"\n\n{forms_info}"

    system_prompt += "\n\n- หากคุณใช้ข้อมูลจาก 'ข้อมูลอ้างอิง (Context)' ให้เขียนคำตอบขึ้นต้นด้วย `[USE_RAG]` เสมอ"

    # ─ Build Messages ─
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        role = "user" if (msg.sender if hasattr(msg, 'sender') else msg.get("sender")) == "user" else "assistant"
        text = msg.text if hasattr(msg, 'text') else msg.get("text", "")
        if role == "assistant":
            text = clean_appended_metadata(text)
        messages.append({"role": role, "content": text})

    user_content = f"ข้อมูลอ้างอิง (Context):\n{context}\n\nคำถามจากผู้ใช้: {query}"
    user_content += "\n\nหากคุณใช้ข้อมูลจาก Context ให้ขึ้นต้นคำตอบด้วย [USE_RAG] ทันที"
    if results:
        user_content += (
            "\nบรรทัดสุดท้ายของคำตอบ ให้ระบุเลขของข้อมูลอ้างอิงที่ใช้ตอบจริงเท่านั้น ในรูปแบบ [SOURCES: 1,3]"
            " ถ้าไม่ได้ใช้ข้อมูลอ้างอิงข้อใดเลยให้เขียน [SOURCES: none]"
        )
    messages.append({"role": "user", "content": user_content})

    # ─ Call OpenRouter API ─
    api_key = config.get("gemini_api_key", "") or settings.LLM_API_KEY or ""
    model_name = config.get("model_name") or settings.DEFAULT_LLM_MODEL
    temperature = float(config.get("temperature", 0.4))
    max_tokens = max(int(config.get("max_tokens", 1000)), 1000)

    ans = None
    model_used = model_name

    if api_key:
        for attempt in range(2):
            try:
                url = "https://openrouter.ai/api/v1/chat/completions"
                payload = {
                    "model": model_name,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                    "HTTP-Referer": "http://localhost:8000",
                    "X-Title": "TUH Chatbot v2"
                }
                # รัน HTTP call ใน thread pool (non-blocking)
                loop = asyncio.get_event_loop()
                res_data = await loop.run_in_executor(None, make_http_post, url, payload, headers, 30)
                choices = res_data.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "")
                    if content.strip():
                        ans = content
                        break
            except Exception as e:
                logger.error("[OpenRouter Error attempt %d] %s", attempt + 1, e)
                if attempt == 1:
                    ans = get_fallback_vector_answer(results)
                    model_used = "fallback"
                await asyncio.sleep(1)
    else:
        # Ollama fallback
        try:
            loop = asyncio.get_event_loop()
            payload = {"model": "qwen2.5:3b", "messages": messages, "stream": False}
            res_data = await loop.run_in_executor(None, make_http_post, "http://localhost:11434/api/chat", payload, None, 30)
            ans = res_data.get("message", {}).get("content", "")
            model_used = "qwen2.5:3b"
        except Exception as e:
            ans = get_fallback_vector_answer(results)
            model_used = "fallback"

    if not ans or ans.strip() == "":
        ans = get_fallback_vector_answer(results)
        model_used = "fallback"

    # ─ ตรวจสอบ [USE_RAG] flag ─
    used_rag = False
    if ans:
        first_150 = ans[:150].upper()
        if "[USE_RAG]" in first_150:
            ans = re.sub(r'(?i)\[USE_RAG\]', '', ans).strip()
            used_rag = True
        elif "เซิร์ฟเวอร์ AI ออฟไลน์" in ans:
            used_rag = True

    return ans, used_rag, model_used


# ─── Custom/Predefined FAQ Matcher (ใช้ร่วมกันทั้ง /api/chat และ /api/search — DRY) ─
# เดิม loop จับคู่ FAQ นี้เขียนซ้ำเกือบทุกตัวอักษรใน routers/chat.py กับ routers/public.py
# และหลังรวม custom_faqs + predefined_faqs เป็น loop เดียว โค้ดเดิม hardcode source label
# เป็น "custom_faq" เสมอ ทำให้คำถามที่จริงๆ ตรงกับ predefined_faqs (ปุ่มคำถามด่วน) ถูกบันทึก
# ผิดประเภทใน ChatHistory.api_model ไปด้วย — ฟังก์ชันนี้คืน source label ที่ถูกต้องตามลิสต์
# ที่จับคู่เจอจริง
def find_matching_faq(
    query: str, custom_faqs: List[Dict], predefined_faqs: List[Dict]
) -> Optional[Tuple[str, str]]:
    """หาคำถามที่ตรงกับ Custom FAQ หรือ Predefined FAQ (เฉพาะข้อที่ตั้งคำตอบตายตัวไว้ —
    answer ไม่ว่างเปล่า เพราะ FaqsPage ของ AdminWeb ให้เว้นคำตอบว่างไว้ได้ตั้งใจ หมายถึง
    "ให้ AI ค้นจาก PDF เอง" สำหรับ FAQ ข้อนั้น) เช็ค custom_faqs ก่อนตามลำดับเดิม
    คืน (answer, source_label) โดย source_label เป็น "custom_faq" หรือ "predefined_faq"
    ตามลิสต์ที่จับคู่เจอจริง — คืน None ถ้าไม่ตรงข้อไหนเลย
    """
    q_lower = query.lower()
    for source_label, faq_list in (("custom_faq", custom_faqs), ("predefined_faq", predefined_faqs)):
        for faq in faq_list:
            faq_q = faq.get("question", "").strip().lower()
            faq_a = faq.get("answer", "").strip()
            if faq_q and faq_a and faq_q in q_lower:
                return faq_a, source_label
    return None


# ─── Citation Relevance Gate (ใช้ร่วมกันทั้ง /api/chat และ /api/search — DRY) ──
# เดิมทั้งสอง endpoint เช็คแค่ "rag_results ไม่ว่าง" ก่อนแนบ citation ซึ่งเกือบไม่มีความหมาย
# เพราะ HybridRetriever.query() ไม่มี relevance threshold คืน top_k เสมอไม่ว่าคำถามจะเกี่ยวกับ
# เอกสารที่มีจริงหรือไม่ (ดู Admin/emb.py) ทำให้คำถามที่ LLM ตอบจากความรู้ทั่วไปล้วนๆ ก็ยังโดน
# แนบลิงก์ PDF ที่ไม่เกี่ยวข้องไปด้วยทุกครั้ง — ใช้ used_rag (LLM ประกาศเองว่าใช้ context) เป็น
# สัญญาณหลักก่อนเหมือนเดิม ถ้าไม่มี (LLM ลืมใส่ tag) ค่อย fallback ไปเช็ค dense similarity
# score ของผลลัพธ์อันดับต้นแทนการเชื่อ top_k เฉยๆ
def has_reliable_context(rag_results: List[Dict], used_rag: bool, min_dense_score: float = 0.42) -> bool:
    """True ถ้า rag_results น่าเชื่อถือพอจะแนบเป็น citation ให้ผู้ใช้จริง
    หมายเหตุ: min_dense_score=0.42 เป็นค่าเริ่มต้นแบบ conservative ยังไม่ได้ทดสอบกับชุดคำถามจริง
    ควรปรับจูนตอนขั้นตอนทดสอบ (เทียบกับ testchatbotSPO/) ถ้าพบว่า citation หายบ่อยไปหรือโผล่ผิดบ่อยไป
    """
    if not rag_results:
        return False
    if used_rag:
        return True
    top_dense = max((r.get("dense_score") or 0.0 for r in rag_results), default=0.0)
    return top_dense >= min_dense_score


# ─── Citation Builder (ใช้ร่วมกันทั้ง /api/chat และ /api/search — DRY) ──────────

_SOURCES_TAG = re.compile(r"\[\s*SOURCES?\s*:\s*([^\]]*)\]", re.IGNORECASE)


def split_used_sources(answer: str, rag_results: List[Dict]) -> Tuple[str, List[Dict]]:
    """ตัด tag [SOURCES: 1,3] ที่ LLM ต่อท้ายคำตอบออก แล้วคืน (คำตอบที่สะอาด, rag_results
    เฉพาะชิ้นที่ LLM บอกว่าใช้ตอบจริง) — ใช้แทนการแนบทุกเอกสารที่ retriever ค้นเจอเป็น citation
    ซึ่งเดิมทำให้เอกสารที่ค้นเจอแต่ไม่ได้ใช้ (เช่น Baseline Configuration ในคำถามเรื่องรหัสผ่าน)
    โผล่เป็นแหล่งอ้างอิงด้วย
    - ไม่มี tag (LLM ลืม / fallback answer / Ollama) → คืน rag_results ทั้งหมดเหมือนพฤติกรรมเดิม
    - [SOURCES: none] หรือไม่มีเลข → คืนลิสต์ว่าง (ไม่แนบ citation)
    - มีเลขแต่ไม่มีเลขไหนอยู่ในช่วง 1..len(rag_results) → ถือว่า LLM สับสน คืนทั้งหมด
    """
    if not answer:
        return answer, rag_results
    matches = list(_SOURCES_TAG.finditer(answer))
    if not matches:
        return answer, rag_results
    cleaned = _SOURCES_TAG.sub("", answer).strip()
    nums = {int(n) for n in re.findall(r"\d+", matches[-1].group(1))}
    if not nums:
        return cleaned, []
    used = [r for i, r in enumerate(rag_results or [], start=1) if i in nums]
    return cleaned, (used or rag_results)


async def build_citations(db, rag_results: List[Dict]) -> List[Dict[str, Any]]:
    """สร้างรายการเอกสารอ้างอิง (citations) จาก rag_results โดย group ตาม source
    (รวมเลขหน้าทั้งหมดของ source เดียวกัน) และ map display_name จากตาราง Document
    เดิม logic นี้อยู่ซ้ำกันคนละที่ใน routers/chat.py กับ routers/public.py — ย้ายมารวม
    ไว้ที่เดียวกันไม่ให้ผลลัพธ์เพี้ยนกันระหว่าง endpoint /api/chat กับ /api/search
    """
    from urllib.parse import quote
    from sqlalchemy import select
    from app.models.models import Document

    if not rag_results:
        return []

    docs_result = await db.execute(select(Document))
    docs = docs_result.scalars().all()
    filename_to_display = {d.filename: d.display_name for d in docs if d.display_name}

    grouped: Dict[str, set] = {}
    for res in rag_results:
        source = res["metadata"].get("source", "เอกสาร")
        page = res["metadata"].get("page")
        if source not in grouped:
            grouped[source] = set()
        if page:
            try:
                grouped[source].add(int(page))
            except (ValueError, TypeError):
                pass

    citations: List[Dict[str, Any]] = []
    for source, pages in grouped.items():
        display = filename_to_display.get(source, source.replace(".pdf", "").replace("_", " "))
        pdf_url = (
            f"/api/documents/serve/{quote(source)}#page={min(pages)}"
            if pages else f"/api/documents/serve/{quote(source)}"
        )
        citations.append({
            "source": source,
            "pages": sorted(pages),
            "display_name": display,
            "url": pdf_url,
        })
    return citations


def is_unanswered_response(answer: str, model_used: str) -> bool:
    """heuristic เดียวกันที่ใช้ทั้งใน chat.py/public.py เพื่อตัดสินว่าคำตอบนี้ถือเป็น
    'ตอบไม่ได้/ปฏิเสธ' หรือไม่ (ไว้ใช้ทั้งตอนบันทึก unanswered log และตอนตัดสินใจว่า
    ควรแนบ citations ให้คำตอบนี้หรือไม่ — ถ้าตอบไม่ได้จริง ไม่ควรมี citation แนบมาด้วย)"""
    return model_used not in ("profanity_filter", "chit_chat") and (
        model_used == "fallback"
        or any(k in answer for k in ["ไม่พบข้อมูล", "ไม่มีข้อมูล", "ขออภัย", "ไม่สามารถตอบได้"])
    )


def _default_system_prompt() -> str:
    return """คุณคือ "ขาหมู" ผู้ช่วยแชทบอทอัจฉริยะ (ผู้ชาย) ของโรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ (TUH)
ตอบคำถามบุคลากรเกี่ยวกับสวัสดิการและ ISO อย่างสุภาพและตรงประเด็น
- แทนตัวเองว่า "ผม" และลงท้ายด้วย "ครับ" เสมอ
- ห้ามกล่าวคำทักทายซ้ำในระหว่างบทสนทนา
- หากไม่พบข้อมูล แจ้งสุภาพและแนะนำติดต่อ 9000 (สวัสดิการ) หรือ 8470 (ISO)"""
