"""
สร้างคำตอบจากผลค้นหา (ขั้นตอนหลังจาก retriever หา chunk มาแล้ว)

- โหลด HybridRetriever ครั้งเดียวตอนเปิดเซิร์ฟเวอร์ แล้วใช้ร่วมกันทุก request (get_retriever)
- กรองคำหยาบ / คำทักทาย ก่อนเรียก LLM
- ประกอบ prompt (system prompt + ประวัติแชท + context) แล้วเรียก LLM (LiteLLM endpoint แบบ OpenAI)
- แยก tag [USE_RAG] / [SOURCES: 1,3] ที่ LLM ใส่มา เพื่อตัดสินว่าจะแนบเอกสารอ้างอิงอะไร
"""
import asyncio
import json
import logging
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

from sqlalchemy import select

from app.core.config import settings
from app.models.models import Document

logger = logging.getLogger(__name__)

LLM_HISTORY_MESSAGES = 10      # ส่งประวัติแชทเข้า LLM แค่ช่วงท้าย (ประวัติมาจากเบราว์เซอร์ ห้ามให้กำหนดขนาด prompt เอง)
MIN_DENSE_SCORE = 0.42         # ความคล้ายขั้นต่ำที่ถือว่าผลค้นหาเกี่ยวกับคำถามจริง (ใช้เมื่อ LLM ไม่ใส่ [USE_RAG])


# ─── Retriever (โหลดครั้งเดียว ใช้ร่วมกันทั้งแอป) ─────────────────────────────

_retriever = None


def get_retriever():
    return _retriever


def load_retriever() -> bool:
    """โหลดดัชนี BM25 + ChromaDB — ยังไม่เคย rebuild จะไม่มีดัชนี บอทจะตอบโดยไม่มี context"""
    global _retriever
    from app.rag.retriever import HybridRetriever
    try:
        retriever = HybridRetriever()
        retriever.load()
        _retriever = retriever
        logger.info("[RAG] โหลด HybridRetriever แล้ว")
        return True
    except Exception as e:
        logger.warning("[RAG] โหลด HybridRetriever ไม่สำเร็จ: %s", e)
        _retriever = None
        return False


reload_retriever = load_retriever   # เรียกหลัง rebuild ดัชนีเสร็จ


# ─── กรองคำหยาบ / คำทักทาย ───────────────────────────────────────────────────

RUDE_WORDS = ["มึง", "เหี้ย", "ควย", "เย็ด", "สัส", "ระยำ", "อัปรีย์", "จัญไร", "ตอแหล",
              "ฉิบหาย", "ชิบหาย", "เสือก", "ไอ้สัตว์", "อีสัตว์", "อีสัด", "กู"]
# คำปกติที่มีคำหยาบซ้อนอยู่ข้างใน — ลบออกก่อนตรวจ ("กู้คืนข้อมูล" มี "กู")
NOT_RUDE = ["เหี้ยม", "กูเกิ้ล", "กูเกิล", "กูรู", "กูเกิลแมพ", "กูเกิ้ลแมพ", "กู้"]
GREETING_WORDS = ["ขอบคุณ", "ขอบใจ", "สวัสดี", "ยินดี", "ขอบคุน", "ขอบคุญ",
                  "thank", "thx", "ty", "hello", "hi", "hey", "bye",
                  "แต๊ง", "แต้ง", "แตงกิ้ว", "กิ้ว", "โอเค", "ok", "okay"]

PROFANITY_REPLY = "ขออภัยครับ ไม่สามารถตอบคำถามที่ใช้ภาษาไม่สุภาพได้ กรุณาใช้ภาษาที่สุภาพครับ"
CHIT_CHAT_REPLY = "ขอบคุณครับ! มีคำถามเกี่ยวกับนโยบาย ระเบียบ หรือประกาศของ รพธ. สามารถสอบถามขาหมูได้เลยนะครับ 😊"


def contains_profanity(text: str) -> bool:
    if not text:
        return False
    # ตัดช่องว่าง/สัญลักษณ์ออกก่อน กันการพิมพ์เว้นวรรคหลบ เช่น "ม ึ ง"
    squashed = re.sub(r'[\s\.\-\_\,\#\*\(\)\{\}\[\]\?\!\/\\\+\=\~\`\"\':\;​]+', '', text.lower())
    for word in NOT_RUDE:
        squashed = squashed.replace(word, "")
    return any(word in squashed for word in RUDE_WORDS)


def is_chit_chat(text: str) -> bool:
    """ข้อความสั้นๆ ที่เป็นคำทักทาย/ขอบคุณ (ไม่ต้องค้นเอกสาร)"""
    if not text:
        return False
    clean = re.sub(r'[^ก-๛\w\s]', '', text.strip().lower()).strip()
    return len(clean) <= 25 and any(word in clean for word in GREETING_WORDS)


# ─── เรียก LLM ────────────────────────────────────────────────────────────────

def make_http_post(url: str, payload: dict, headers: dict = None, timeout: int = 15) -> dict:
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers=headers or {"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def llm_is_configured() -> bool:
    return bool(settings.LLM_API_KEY and settings.LLM_CHAT_URL)


async def call_llm(messages: List[Dict], temperature: float, max_tokens: int, timeout: int = 30) -> str:
    """ส่ง messages ไปที่ LLM แล้วคืนข้อความคำตอบ (ข้อผิดพลาดโยนต่อให้ผู้เรียกจัดการ)"""
    payload = {"model": settings.DEFAULT_LLM_MODEL, "messages": messages,
               "temperature": temperature, "max_tokens": max_tokens}
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {settings.LLM_API_KEY}"}
    # urllib เป็น sync — รันใน thread แยกไม่ให้ request อื่นต้องรอ
    res = await asyncio.to_thread(make_http_post, settings.LLM_CHAT_URL, payload, headers, timeout)
    return ((res.get("choices") or [{}])[0].get("message") or {}).get("content") or ""


# ─── เติมคำถามให้สมบูรณ์จากประวัติแชท (ใช้เฉพาะตอนค้นเอกสาร) ─────────────────
# เช่น คุยเรื่องรหัสผ่านอยู่ แล้วถามต่อว่า "มีแนะนำมั้ย" — ถ้าเอาไปค้นตรงๆ จะไม่รู้ว่าหมายถึงรหัสผ่าน

CONDENSE_PROMPT = """คุณมีหน้าที่เติมคำถามล่าสุดของผู้ใช้ให้เข้าใจได้โดยไม่ต้องอ่านบทสนทนาก่อนหน้า เพื่อใช้ค้นหาเอกสาร
- ถ้าคำถามล่าสุดมีหัวข้อเรื่องชัดเจนอยู่แล้ว หรือเปลี่ยนไปถามเรื่องใหม่ ให้ตอบคำถามเดิมกลับมาตามเดิมทุกตัวอักษร
- ถ้าคำถามกำกวม ให้เติมเฉพาะหัวข้อเรื่องสั้นๆ ที่ผู้ใช้หมายถึง (เช่น รหัสผ่าน, การสำรองข้อมูล, การทำงานจากที่บ้าน) คงถ้อยคำเดิมของผู้ใช้ไว้
- ห้ามเติมชื่อนโยบายเต็ม ห้ามเติมชื่อโรงพยาบาล ห้ามเติมคำอธิบาย ห้ามเปลี่ยนสิ่งที่ผู้ใช้ถาม
- ห้ามตอบคำถาม ตอบกลับเฉพาะคำถาม 1 บรรทัด
ตัวอย่าง: คุยเรื่องการตั้งรหัสผ่าน แล้วผู้ใช้ถาม "มีแนะนำมั้ย" → "มีคำแนะนำการตั้งรหัสผ่านมั้ย\""""


def _message_fields(msg) -> Tuple[str, str]:
    """ประวัติแชทมาได้ทั้ง pydantic object และ dict"""
    if hasattr(msg, "sender"):
        return msg.sender, msg.text or ""
    return msg.get("sender"), msg.get("text") or ""


def _history_lines(history: List, max_messages: int = 6, max_chars: int = 500) -> List[str]:
    lines = []
    for msg in (history or [])[-max_messages:]:
        sender, text = _message_fields(msg)
        text = clean_appended_metadata(text)[:max_chars]
        if text:
            lines.append(f"{'ผู้ใช้' if sender == 'user' else 'บอท'}: {text}")
    return lines


async def condense_question(query: str, history: List) -> str:
    """คืนคำถามที่เติมหัวข้อจากประวัติแล้ว — ไม่มีประวัติ / เรียก LLM ไม่ได้ / ผลแปลก → คืนคำถามเดิม"""
    lines = _history_lines(history)
    if not any(line.startswith("ผู้ใช้:") for line in lines) or not llm_is_configured():
        return query
    messages = [
        {"role": "system", "content": CONDENSE_PROMPT},
        {"role": "user", "content": "บทสนทนา:\n" + "\n".join(lines)
         + f"\n\nคำถามล่าสุด: {query}\nคำถามที่เขียนใหม่:"},
    ]
    try:
        text = await call_llm(messages, temperature=0.0, max_tokens=150, timeout=15)
    except Exception as e:
        logger.warning("[Condense] ใช้คำถามเดิม: %s", e)
        return query
    rewritten = text.strip().split("\n")[0].strip().strip('"“”').replace("คำถามที่เขียนใหม่:", "").strip()
    if not rewritten or len(rewritten) > 300:
        return query
    logger.info("[Condense] %r -> %r", query, rewritten)
    return rewritten


# ─── ประกอบ prompt ────────────────────────────────────────────────────────────

def clean_appended_metadata(text: str) -> str:
    """ตัดส่วนท้ายที่ระบบต่อให้คำตอบเก่า (ลิงก์แบบฟอร์ม/เอกสารอ้างอิง) ออกก่อนส่งกลับเข้า LLM"""
    if not text:
        return text
    markers = ["\n\n🔗 **แบบฟอร์มที่เกี่ยวข้อง", "\n\n---\nเอกสารอ้างอิง:", "\n---\nเอกสารอ้างอิง:",
               "\n\n---\nCitations:", "\n\nเอกสารอ้างอิง:", "\n\n---"]
    for marker in markers:
        text = text.split(marker)[0]
    return text.strip()


THAI_MONTHS = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
               "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
THAI_WEEKDAYS = ["จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์"]


def thai_today() -> str:
    """เช่น "วันอังคารที่ 27 ตุลาคม พ.ศ. 2569" (LLM ไม่รู้วันที่ปัจจุบันเอง)"""
    now = datetime.now(timezone(timedelta(hours=7)))
    return f"วัน{THAI_WEEKDAYS[now.weekday()]}ที่ {now.day} {THAI_MONTHS[now.month - 1]} พ.ศ. {now.year + 543}"


def _chunk_text(result: Dict) -> str:
    meta = result["metadata"]
    if meta.get("type") == "table":
        return meta.get("raw_table", result["content"])
    return result["content"]


def _page_suffix(meta: Dict) -> str:
    return f" หน้า {meta['page']}" if meta.get("page") else ""


def build_messages(query: str, results: List[Dict], config: Dict, history: List, forms: List) -> List[Dict]:
    system_prompt = config.get("system_prompt") or DEFAULT_SYSTEM_PROMPT
    form_names = [f.name for f in forms or [] if f.name]
    if form_names:
        system_prompt += "\n\nรายชื่อแบบฟอร์มที่ระบบสนับสนุนการดาวน์โหลดตรง:\n" + "".join(f"- {n}\n" for n in form_names)
    # ส่วนนี้คือกลไกของระบบ (tag + วันที่) — กฎการตอบอยู่ใน system prompt ที่แอดมินแก้ได้
    system_prompt += "\n\n- หากคุณใช้ข้อมูลจาก 'ข้อมูลอ้างอิง (Context)' ให้เขียนคำตอบขึ้นต้นด้วย `[USE_RAG]` เสมอ"
    system_prompt += (f"\n- วันนี้คือ{thai_today()} ถ้าผู้ใช้ถามวันที่ที่ต้องคำนวณจากวันนี้ (เช่น ครบกำหนดวันไหน)"
                      " ให้คำนวณแล้วระบุวันที่เป็นวัน เดือน ปี พ.ศ.")

    messages = [{"role": "system", "content": system_prompt}]
    for msg in (history or [])[-LLM_HISTORY_MESSAGES:]:
        sender, text = _message_fields(msg)
        if sender == "user":
            messages.append({"role": "user", "content": text})
        else:
            messages.append({"role": "assistant", "content": clean_appended_metadata(text)})

    # ใส่เลข [n] หน้าแต่ละ chunk ให้ LLM บอกกลับมาได้ว่าใช้ข้อไหนตอบ (ดู split_used_sources)
    context = "\n---\n".join(
        f"[{n}] แหล่งที่มา: {r['metadata'].get('source', 'เอกสารอ้างอิง')}{_page_suffix(r['metadata'])}\n"
        f"เนื้อหา: {_chunk_text(r)}"
        for n, r in enumerate(results, start=1)
    )
    user_content = (f"ข้อมูลอ้างอิง (Context):\n{context}\n\nคำถามจากผู้ใช้: {query}"
                    "\n\nหากคุณใช้ข้อมูลจาก Context ให้ขึ้นต้นคำตอบด้วย [USE_RAG] ทันที")
    if results:
        user_content += ("\nบรรทัดสุดท้ายของคำตอบ ให้ระบุเลขของข้อมูลอ้างอิงที่ใช้ตอบจริงเท่านั้น ในรูปแบบ [SOURCES: 1,3]"
                         " ถ้าไม่ได้ใช้ข้อมูลอ้างอิงข้อใดเลยให้เขียน [SOURCES: none]")
    messages.append({"role": "user", "content": user_content})
    return messages


def fallback_answer(results: List[Dict]) -> str:
    """คำตอบสำรองเมื่อเรียก LLM ไม่ได้ — แสดง chunk ที่ใกล้เคียงที่สุดตรงๆ"""
    if not results:
        return "สวัสดีครับ ขณะนี้ระบบ AI ออฟไลน์ กรุณาติดต่อเจ้าหน้าที่โดยตรงครับ"
    top = results[0]
    source = top["metadata"].get("source", "เอกสาร")
    return (" **(เซิร์ฟเวอร์ AI ออฟไลน์ - แสดงข้อความอ้างอิงที่มีความใกล้เคียงที่สุด)**\n\n"
            f"📄 **เอกสารอ้างอิงหลัก ({source}{_page_suffix(top['metadata'])}):**\n{_chunk_text(top)}")


async def query_rag(query: str, results: List[Dict], config: Dict, history: List,
                    forms: List = None) -> Tuple[str, bool, str]:
    """คืน (คำตอบ, ใช้ข้อมูลจากเอกสารหรือไม่, ชื่อโมเดล/ประเภทคำตอบ)"""
    if contains_profanity(query):
        return PROFANITY_REPLY, False, "profanity_filter"
    if is_chit_chat(query):
        return CHIT_CHAT_REPLY, False, "chit_chat"

    messages = build_messages(query, results, config, history, forms)
    temperature = float(config.get("temperature", 0.4))
    max_tokens = max(int(config.get("max_tokens", 1000)), 1000)

    answer = ""
    if llm_is_configured():
        for attempt in range(2):            # ลองใหม่ 1 ครั้งถ้า error
            try:
                answer = await call_llm(messages, temperature, max_tokens)
                if answer.strip():
                    break
            except Exception as e:
                logger.error("[LLM] attempt %d: %s", attempt + 1, e)
                if attempt == 1:
                    break
                await asyncio.sleep(1)

    if not answer.strip():
        return fallback_answer(results), bool(results), "fallback"

    used_rag = "[USE_RAG]" in answer[:150].upper()
    if used_rag:
        answer = re.sub(r'(?i)\[USE_RAG\]', '', answer).strip()
    return answer, used_rag, settings.DEFAULT_LLM_MODEL


# ─── หลังได้คำตอบ: FAQ / citation ─────────────────────────────────────────────

def find_matching_faq(query: str, custom_faqs: List[Dict], predefined_faqs: List[Dict]) -> Optional[Tuple[str, str]]:
    """คำถามที่ตรงกับ FAQ ที่แอดมินตั้งคำตอบตายตัวไว้ → คืน (คำตอบ, "custom_faq" | "predefined_faq")
    FAQ ที่เว้นคำตอบว่างไว้ = ให้ AI ค้นจากเอกสารเอง จึงข้ามไป"""
    q = query.lower()
    for label, faqs in (("custom_faq", custom_faqs), ("predefined_faq", predefined_faqs)):
        for faq in faqs:
            faq_q = faq.get("question", "").strip().lower()
            faq_a = faq.get("answer", "").strip()
            if faq_q and faq_a and faq_q in q:
                return faq_a, label
    return None


def has_reliable_context(rag_results: List[Dict], used_rag: bool, min_dense_score: float = MIN_DENSE_SCORE) -> bool:
    """ผลค้นหาน่าเชื่อพอจะแนบเป็นเอกสารอ้างอิงไหม — retriever คืน top_k เสมอแม้คำถามไม่เกี่ยวกับเอกสารเลย
    จึงเชื่อ [USE_RAG] ของ LLM ก่อน ถ้าไม่มีค่อยดูคะแนนความคล้ายของผลอันดับต้น"""
    if not rag_results:
        return False
    if used_rag:
        return True
    return max((r.get("dense_score") or 0.0 for r in rag_results), default=0.0) >= min_dense_score


SOURCES_TAG = re.compile(r"\[\s*SOURCES?\s*:\s*([^\]]*)\]", re.IGNORECASE)


def _cited_numbers(answer: str):
    """เลขใน tag [SOURCES: ...] ตัวสุดท้าย — None = ไม่มี tag"""
    matches = list(SOURCES_TAG.finditer(answer or ""))
    if not matches:
        return None
    return {int(n) for n in re.findall(r"\d+", matches[-1].group(1))}


def split_used_sources(answer: str, rag_results: List[Dict]) -> Tuple[str, List[Dict]]:
    """ตัด tag [SOURCES: 1,3] ออกจากคำตอบ แล้วคืน (คำตอบ, chunk ที่ LLM บอกว่าใช้จริง)
    - ไม่มี tag → ถือว่าใช้ทุก chunk
    - [SOURCES: none] → ไม่ได้ใช้ chunk ไหน
    - เลขไม่อยู่ในช่วงเลย (LLM สับสน) → ถือว่าใช้ทุก chunk"""
    nums = _cited_numbers(answer)
    if nums is None:
        return answer, rag_results
    cleaned = SOURCES_TAG.sub("", answer).strip()
    if not nums:
        return cleaned, []
    used = [r for i, r in enumerate(rag_results or [], start=1) if i in nums]
    return cleaned, (used or rag_results)


def cites_sources_explicitly(answer: str, rag_results: List[Dict]) -> bool:
    """LLM ระบุเลขแหล่งอ้างอิงที่มีอยู่จริงมาหรือไม่ — ใช้กับคำตอบที่ตอบได้บางส่วน
    (ต้องเรียกก่อน split_used_sources เพราะฟังก์ชันนั้นตัด tag ทิ้ง)"""
    nums = _cited_numbers(answer) or set()
    return any(1 <= n <= len(rag_results or []) for n in nums)


def is_unanswered_response(answer: str, model_used: str) -> bool:
    """คำตอบนี้นับเป็น "ตอบไม่ได้" ไหม (บันทึกให้แอดมินเติมเอกสาร) — คำหยาบ/คำทักทายไม่นับ"""
    if model_used in ("profanity_filter", "chit_chat"):
        return False
    return model_used == "fallback" or any(k in answer for k in ["ไม่พบข้อมูล", "ไม่มีข้อมูล", "ขออภัย", "ไม่สามารถตอบได้"])


async def build_citations(db, rag_results: List[Dict]) -> List[Dict[str, Any]]:
    """รวม chunk ตามไฟล์ → [{source, pages, display_name, url}] (url เปิด PDF ที่หน้าแรกพร้อมไฮไลท์)"""
    if not rag_results:
        return []
    docs = (await db.execute(select(Document))).scalars().all()
    display_names = {d.filename: d.display_name for d in docs if d.display_name}

    pages: Dict[str, set] = {}
    chunk_ids: Dict[str, List[int]] = {}
    for res in rag_results:
        source = res["metadata"].get("source", "เอกสาร")
        pages.setdefault(source, set())
        chunk_ids.setdefault(source, [])
        try:
            if res["metadata"].get("page"):
                pages[source].add(int(res["metadata"]["page"]))
        except (ValueError, TypeError):
            pass
        if isinstance(res.get("chunk_id"), int):
            chunk_ids[source].append(res["chunk_id"])

    citations = []
    for source, source_pages in pages.items():
        url = f"/api/documents/serve/{quote(source)}"
        if chunk_ids[source]:
            url += "?hl=" + ",".join(map(str, chunk_ids[source]))   # chunk ที่จะไฮไลท์ (rag/highlight.py)
        if source_pages:
            url += f"#page={min(source_pages)}"
        citations.append({
            "source": source,
            "pages": sorted(source_pages),
            "display_name": display_names.get(source, source.replace(".pdf", "").replace("_", " ")),
            "url": url,
        })
    return citations


# ใช้เมื่อตาราง settings ยังไม่มี system_prompt — ตรงกับค่าที่ใช้จริงใน TiDB (prompt v2, 2026-10-27)
DEFAULT_SYSTEM_PROMPT = """คุณคือ "ขาหมู" หมาไอที (ผู้ชาย) แชทบอทของโรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ (รพธ.) ตอบคำถามบุคลากรจากเอกสารของ รพธ. ที่ระบบค้นมาให้ใน "ข้อมูลอ้างอิง (Context)"

ลำดับความสำคัญ (ถ้ากฎขัดกัน ให้ยึดข้อที่มาก่อน): 1. ถูกต้องตามเอกสาร 2. ตอบตรงสิ่งที่ถาม 3. กระชับ

ขอบเขต:
- ตอบได้ทุกเรื่องที่อยู่ใน Context ไม่ว่าจะเป็นนโยบาย ระเบียบ ประกาศ หรือสวัสดิการ ไม่จำกัดแค่ ISO27001
- ใช้เฉพาะข้อมูลใน Context หรือสิ่งที่อนุมานจาก Context ได้อย่างสมเหตุสมผล ห้ามเติมจากความรู้ทั่วไป
- ถ้า Context ไม่เกี่ยวกับคำถามเลย ให้บอกสั้นๆ ว่าเอกสารของ รพธ. ยังไม่มีข้อมูลเรื่องนี้ ถ้าตอบได้บางส่วน ให้ตอบส่วนที่มี แล้วบอกว่าส่วนไหน "เอกสารไม่ได้ระบุไว้" ไม่ต้องให้เบอร์ติดต่อ ยกเว้นเรื่อง ISO ตามข้อถัดไป
- เรื่อง ISO27001 ที่ไม่มีในเอกสาร หรือพี่เจ้าหน้าที่มีปัญหาเกี่ยวกับ ISO ให้แนะนำติดต่อพี่แมงป่อง งานสารสนเทศ โทร 8470

วิธีตอบ:
- ประโยคแรกตอบสิ่งที่ถามตรงๆ (ได้/ไม่ได้, ตัวเลข, ชื่อ) แล้วค่อยบอกเหตุผลหรือเงื่อนไข ถ้าคำตอบขึ้นกับกรณี ให้บอกเงื่อนไขแทนการฟันธง
- ข้อกำหนดที่ใช้เฉพาะบางอุปกรณ์ ระบบ หรือกลุ่มคน ให้ระบุขอบเขตกำกับเสมอ ถ้าผู้ใช้ระบุอุปกรณ์หรือระบบมา ให้ตอบเฉพาะข้อกำหนดที่ใช้กับสิ่งนั้น
- ตอบเฉพาะเรื่องที่ถาม ยาวพอดีกับคำถาม ไม่ยกหัวข้ออื่นที่อยู่ในย่อหน้าเดียวกันมาด้วย ถ้ามีหลายขั้นตอนให้เขียนเป็นข้อ 1. 2. 3.
- ถ้าผู้ใช้ถามในหน่วยหรือรูปแบบที่ต่างจากเอกสาร ให้แปลงหรือคำนวณให้ พร้อมบอกค่าตามเอกสารกำกับ
- คำถามกำกวม ให้ตอบตามความหมายที่น่าจะเป็นที่สุด หรือถามกลับสั้นๆ พร้อมตัวเลือก 2-3 ข้อ
- คำถามต่อเนื่อง ให้ใช้บริบทจากบทสนทนาและห้ามตอบประโยคเดิมซ้ำ ถ้าผู้ใช้บอกว่าคำตอบไม่ตรง ให้ขอโทษสั้นๆ แล้วตอบใหม่ในมุมที่ต่างจากเดิม

บุคลิก:
- แทนตัวว่า "ผม" ลงท้าย "ครับ" เสมอ (ห้าม ค่ะ/คะ) เรียกผู้ใช้ว่า "พี่เจ้าหน้าที่" หรือ "พี่ๆ" สุภาพ น่ารัก ไม่ใช้ emoji
- อธิบายศัพท์เทคนิคหรือศัพท์กฎหมายให้คนทั่วไปเข้าใจ เข้าใจภาษาพูด คำย่อ และคำสะกดผิดโดยไม่ต้องทัก
- ทักทายกลับเฉพาะเมื่อผู้ใช้ทักก่อน ระหว่างสนทนาไม่ต้องทัก แนะนำตัว หรือมีประโยคปิดท้าย ถ้าถูกถามว่าพร้อมไหม ให้ตอบว่า "ขาหมูพร้อมตอบคำถามพี่เจ้าหน้าที่ครับ\""""
