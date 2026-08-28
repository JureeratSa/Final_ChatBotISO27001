"""
TUH Chatbot AI — RAG Service
คง Logic เดิมทั้งหมด: HybridRetriever (FAISS + BM25 + Weighted RRF)
Wraps existing Admin/emb.py as an async-compatible service
"""
import os
import re
import sys
import json
import time
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from app.core.config import settings


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
        print("[RAG] HybridRetriever loaded successfully")
        return True
    except Exception as e:
        print(f"[RAG] Warning: Could not load HybridRetriever: {e}")
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
        for r in results:
            source = r['metadata'].get('source', 'เอกสารอ้างอิง')
            page = r['metadata'].get('page', '')
            page_str = f" หน้า {page}" if page else ""
            content = (
                r['metadata'].get('raw_table', r['content'])
                if r['metadata'].get('type') == 'table'
                else r['content']
            )
            context_parts.append(f"แหล่งที่มา: {source}{page_str}\nเนื้อหา: {content}")
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
                print(f"[OpenRouter Error attempt {attempt+1}] {e}")
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


def _default_system_prompt() -> str:
    return """คุณคือ "ขาหมู" ผู้ช่วยแชทบอทอัจฉริยะ (ผู้ชาย) ของโรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ (TUH)
ตอบคำถามบุคลากรเกี่ยวกับสวัสดิการและ ISO อย่างสุภาพและตรงประเด็น
- แทนตัวเองว่า "ผม" และลงท้ายด้วย "ครับ" เสมอ
- ห้ามกล่าวคำทักทายซ้ำในระหว่างบทสนทนา
- หากไม่พบข้อมูล แจ้งสุภาพและแนะนำติดต่อ 9000 (สวัสดิการ) หรือ 8470 (ISO)"""
