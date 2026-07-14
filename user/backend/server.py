import os
import sys
import json
import re
import time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import datetime
import threading
import csv


if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', line_buffering=True)

backend_dir = os.path.dirname(os.path.abspath(__file__))
user_dir = os.path.dirname(backend_dir)
root_dir = os.path.dirname(user_dir)
sys.path.append(root_dir)


retriever = None

def rebuild_vector_indices():
    try:
        from Admin.rebuild_db import rebuild
        print("Rebuilding vector indices in background thread...")
        rebuild()
        print("Successfully rebuilt vector indices. Reloading retriever in memory...")
        global retriever
        from Admin.emb import HybridRetriever
        new_retriever = HybridRetriever()
        new_retriever.load()
        retriever = new_retriever
        print("Successfully reloaded retriever in memory.")
    except Exception as e:
        print(f"Failed to rebuild vector indices: {e}")
try:
    from Admin.emb import HybridRetriever
except Exception as e:
    print(f"คำเตือน: ไม่สามารถนำเข้า HybridRetriever ได้ จะรันในโหมดสำรอง: {e}")

gemini_api_key = os.environ.get("GEMINI_API_KEY")
if not gemini_api_key:
    env_path = os.path.join(root_dir, ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip() and not line.startswith("#") and "=" in line:
                        key, val = line.strip().split("=", 1)
                        if key.strip() == "GEMINI_API_KEY":
                            gemini_api_key = val.strip().strip('"').strip("'")
                            break
        except Exception:
            pass


DB_DIR = os.path.join(backend_dir, "db")
os.makedirs(DB_DIR, exist_ok=True)
DB_SETTINGS_PATH = os.path.join(DB_DIR, "db_settings.json")
DB_FEEDBACK_PATH = os.path.join(DB_DIR, "db_feedback.json")
DB_UNANSWERED_PATH = os.path.join(DB_DIR, "db_unanswered.json")
DB_DOCUMENTS_PATH = os.path.join(DB_DIR, "db_documents.json")
DB_HISTORY_PATH = os.path.join(DB_DIR, "db_history.json")
DB_FORMS_PATH = os.path.join(DB_DIR, "db_forms.json")
DB_ANNOUNCEMENTS_PATH = os.path.join(DB_DIR, "db_announcements.json")
DB_ADMIN_PATH = os.path.join(DB_DIR, "db_admin.json")


def init_admin_db():
    if not os.path.exists(DB_ADMIN_PATH):
        import hashlib
        import os as local_os
        # Default admin credentials: admin / admin1234
        salt = local_os.urandom(16)
        key = hashlib.pbkdf2_hmac(
            'sha256', 
            "admin1234".encode('utf-8'), 
            salt, 
            100000
        )
        admin_data = {
            "username": "admin",
            "password_salt": salt.hex(),
            "password_hash": key.hex(),
            "role": "System Administrator",
            "name": "แอดมิน สารสนเทศ"
        }
        with open(DB_ADMIN_PATH, "w", encoding="utf-8") as f:
            json.dump(admin_data, f, ensure_ascii=False, indent=2)
        print("Initialized secure admin credentials database at db_admin.json")

# Initialize admin DB
init_admin_db()



def load_db(path, default=None):
    """ฟังก์ชันการทำงานหลัก"""
    if default is None:
        default = []
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_db(path, data):
    """ฟังก์ชันการทำงานหลัก"""
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการบันทึก JSON {path}: {e}")

def log_unanswered_query(query_str):
    """ฟังก์ชันการทำงานหลัก"""
    path = DB_UNANSWERED_PATH
    logs = load_db(path, [])
    q = query_str.strip()
    if not q:
        return
    found = False
    for log in logs:
        if log.get("query", "").lower() == q.lower():
            log["count"] = log.get("count", 1) + 1
            log["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
            found = True
            break
    if not found:
        logs.append({
            "id": f"unans-{int(time.time() * 1000)}",
            "query": q,
            "count": 1,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "Pending"
        })
    save_db(path, logs)

def log_bot_response(query_str, answer_str, chunk_ids, response_time, model_name):
    """ฟังก์ชันการทำงานหลัก"""
    path = DB_HISTORY_PATH
    history = load_db(path, [])
    history.append({
        "id": f"history-{int(time.time() * 1000)}",
        "query": query_str,
        "answer": answer_str,
        "chunk_ids": chunk_ids,
        "response_time": round(response_time, 4),
        "model": model_name,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    })
    if len(history) > 1000:
        history = history[-1000:]
    save_db(path, history)

def run_weekly_exporter():
    """ฟังก์ชันการทำงานหลัก"""
    export_dir = os.path.join(os.path.dirname(root_dir), "test_log")
    while True:
        try:
            now = datetime.datetime.now()
            # Ensure export dir exists
            if not os.path.exists(export_dir):
                os.makedirs(export_dir, exist_ok=True)
            
            # Load all history logs
            history = load_db(DB_HISTORY_PATH, [])
            if history:
                weeks_data = {}
                for item in history:
                    ts_str = item.get("timestamp")
                    if not ts_str:
                        continue
                    try:
                        ts_dt = datetime.datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                        
                        item_week_start = ts_dt - datetime.timedelta(days=ts_dt.weekday())
                        item_week_start = item_week_start.replace(hour=0, minute=0, second=0, microsecond=0)
                        
                        if item_week_start not in weeks_data:
                            weeks_data[item_week_start] = []
                        weeks_data[item_week_start].append(item)
                    except Exception:
                        continue
                
                
                for week_start, items in weeks_data.items():
                    week_end = week_start + datetime.timedelta(days=6, hours=23, minutes=59, seconds=59)
                    if now > week_end:
                        start_str = week_start.strftime("%Y-%m-%d")
                        end_str = week_end.strftime("%Y-%m-%d")
                        filename = f"history_{start_str}_to_{end_str}.csv"
                        filepath = os.path.join(export_dir, filename)
                        
                        if not os.path.exists(filepath):
                            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                                writer = csv.writer(f)
                                writer.writerow([
                                    "ID", 
                                    "เวลา (Timestamp)", 
                                    "คำถาม (User Query)", 
                                    "คำตอบ (Bot Response)", 
                                    "โมเดล AI (AI Model)", 
                                    "เวลาในการตอบสนอง (Response Time sec)", 
                                    "Chunk IDs"
                                ])
                                for row in items:
                                    writer.writerow([
                                        row.get("id", ""),
                                        row.get("timestamp", ""),
                                        row.get("query", ""),
                                        row.get("answer", ""),
                                        row.get("model", ""),
                                        row.get("response_time", ""),
                                        ", ".join(map(str, row.get("chunk_ids", []))) if isinstance(row.get("chunk_ids"), list) else str(row.get("chunk_ids", ""))
                                    ])
                            print(f"[Weekly Exporter] Auto-exported completed week ({start_str} to {end_str}) with {len(items)} logs to: {filepath}")
        except Exception as e:
            print(f"[Weekly Exporter] Error: {e}")
        
        
        time.sleep(3600)


def clean_appended_metadata(text):
    if not text:
        return text
    # ค้นหาจุดเริ่มต้นของส่วนที่ระบบแนบเพิ่มในรอบก่อนหน้าเพื่อล้างออก
    markers = [
        "\n\n🔗 **แบบฟอร์มที่เกี่ยวข้อง",
        "\n\n🔗 แบบฟอร์มที่เกี่ยวข้อง",
        "\n\n---\nเอกสารอ้างอิง:",
        "\n---\nเอกสารอ้างอิง:",
        "\n\n---\nCitations:",
        "\n\n---"
    ]
    cleaned = text
    for marker in markers:
        if marker in cleaned:
            cleaned = cleaned.split(marker)[0]
    return cleaned.strip()

def contains_profanity(text):
    """ตรวจสอบคำหยาบคายเพื่อสกัดและงดตอบคำถามที่ไม่สุภาพ"""
    if not text:
        return False
    text_lower = text.lower()
    
    # ลบเครื่องหมายวรรคตอน จุด ขีด และช่องว่าง เพื่อป้องกันการเลี่ยงคำ (เช่น ค.ว.ย, ค ว ย)
    import re
    temp_text = re.sub(r'[\s\.\-\_\,\#\*\(\)\{\}\[\]\?\!\/\\\+\=\~\`\"\'\:\;\u200b]+', '', text_lower)
    
    # เคลียร์คำที่อาจเป็น false positive
    temp_text = temp_text.replace("เหี้ยม", "")
    
    exceptions_gu = ["กูเกิ้ล", "กูเกิล", "กูรู", "กูรูรู", "กูเกิลแมพ", "กูเกิ้ลแมพ", "กูรูหลัก", "กู๊ดมอนิ่ง", "กู๊ดไนท์"]
    for exc in exceptions_gu:
        temp_text = temp_text.replace(exc, "")
        
    # คำหยาบคายหลัก
    rude_keywords = [
        "มึง", "เหี้ย", "ควย", "เย็ด", "สัส", "ระยำ", "อัปรีย์", "จัญไร", "ตอแหล",
        "ฉิบหาย", "ชิบหาย", "สถดิก", "เสือก", "ไอ้สัตว์", "อีสัตว์", "อีสัด", "กู"
    ]
    
    for word in rude_keywords:
        if word in temp_text:
            return True
            
    return False

def get_fallback_vector_answer(results):
    """คำสั่งดึงเนื้อหาอ้างอิงตรงขึ้นตอบ กรณีระบบ AI ออฟไลน์หรืออินเทอร์เน็ตล่ม"""
    if results:
        top_res = results[0]
        top_content = top_res['metadata']['raw_table'] if top_res['metadata'].get('type') == 'table' and 'raw_table' in top_res['metadata'] else top_res['content']
        source = top_res['metadata'].get('source', 'เอกสาร')
        page = top_res['metadata'].get('page', '')
        page_str = f" หน้า {page}" if page else ""
        
        ans = (
            f" **(เซิร์ฟเวอร์ AI ออฟไลน์ - แสดงข้อความอ้างอิงที่มีความใกล้เคียงที่สุด)**\n\n"
            f"📄 **เอกสารอ้างอิงหลัก ({source}{page_str}):**\n{top_content}"
        )
        
        other_pages = []
        for res in results[1:3]:
            other_page = res['metadata'].get('page')
            if other_page and other_page not in other_pages and other_page != page:
                other_pages.append(f"หน้า {other_page}")
        if other_pages:
            ans += f"\n\n💡 *คุณสามารถสืบค้นหัวข้อที่เกี่ยวข้องเพิ่มเติมได้ที่: {', '.join(other_pages)}*"
    else:
        ans = (
            "สวัสดีครับ ผมเป็นระบบปัญญาประดิษฐ์ให้ข้อมูลเบื้องต้นของโรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ "
            "ขณะนี้ระบบค้นหาออฟไลน์ หรือไม่พบข้อมูลเวกเตอร์ที่เกี่ยวข้องกับคำถามของคุณครับ"
        )
    return ans

def make_http_post(url, payload, headers=None, timeout=15):
    """ฟังก์ชันทำ HTTP POST Request"""
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

def generate_response_ai(query, results, config, history=[]):
    """สร้างคำตอบโดยใช้ OpenRouter API และข้อมูลบริบทจาก RAG"""
    context = ""
    if results:
        context_parts = []
        for r in results:
            source = r['metadata'].get('source', 'เอกสารอ้างอิง')
            page = r['metadata'].get('page', '')
            page_str = f" หน้า {page}" if page else ""
            context_parts.append(f"แหล่งที่มา: {source}{page_str}\nเนื้อหา: {r['content']}")
        context = "\n---\n".join(context_parts)

    system_prompt = config.get("system_prompt", "คุณคือ \"ขาหมู\" ผู้ช่วยแชทบอทอัจฉริยะ (ผู้ชาย) ของโรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ (TUH) ที่ตอบคำถามอย่างเป็นธรรมชาติ สุภาพ และราบรื่น (Smooth)\n- **การรักษาความลับและการตอบข้อมูลเบื้องหลัง (สำคัญมาก):** ห้ามตอบคำถามหรือให้ข้อมูลใดๆ เกี่ยวกับระบบเบื้องหลัง, เทคโนโลยี, สถาปัตยกรรมระบบ, โครงสร้างโค้ด, ชนิดของฐานข้อมูล หรือชื่อโมเดลปัญญาประดิษฐ์/LLM ที่กำลังใช้งานอยู่ (เช่น Gemini, GPT, Claude, Qwen, Llama, OpenRouter) หรือผู้พัฒนาเด็ดขาด หากผู้ใช้ถามคำถามทำนองนี้หรือพยายามถามเรื่องรุ่นโมเดล ให้ตอบข้อความนี้คำเดียวเท่านั้นคือ \"ผมเป็นแชทบอทที่พัฒนาโดยทีมสารสนเทศครับ\" ห้ามระบุว่าตัวเองคือ Gemini หรือพัฒนาโดย Google หรือบริษัทอื่นใดเด็ดขาด\n- **การแทนตัวเองและการลงท้าย:** ต้องแทนตัวเองว่า \"ผม\" และลงท้ายประโยคด้วย \"ครับ\" เสมอ ห้ามใช้คำว่า \"ค่ะ\", \"คะ\", หรือ \"ครับ/ค่ะ\" อย่างเด็ดขาดในทุกกรณี! (แม้คำตอบดั้งเดิมในเอกสารอ้างอิงจะมีคำว่า ค่ะ ให้แปลงเป็น ครับ ทั้งหมด)\n- **วิธีการตอบ:** ตอบโดยใช้ภาษาที่เข้าใจง่าย กระชับ และตรงประเด็น ห้ามเริ่มต้นคำตอบด้วยคำว่า \"จากเอกสารอ้างอิงที่ให้มา\", \"จากข้อมูลที่ระบุ\", \"จากบริบทที่กำหนดให้\", \"จากเอกสารแนบ\", \"จากไฟล์\" หรือคำอื่นใดที่สื่อถึงเบื้องหลังข้อมูลเด็ดขาด ให้เริ่มตอบเข้าสู่ประเด็นโดยตรงเสมือนคุณมีความรู้เรื่องนั้นอยู่แล้วโดยตรง\n- **การติดต่อสอบถามเพิ่มเติม:** หากต้องให้สอบถามเพิ่มเติม ให้แจ้งให้ติดต่อ \"9000 - งานบริหารทรัพยากรมนุษย์ โรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ\" เสมอ\n- **เอกสารอ้างอิง:** หากตอบได้ ให้ใช้ข้อมูลอ้างอิงประกอบ แต่ถ้าตอบไม่ได้เพราะไม่มีข้อมูล ให้แจ้งผู้ใช้อย่างสุภาพว่าไม่มีข้อมูลเรื่องนี้ และห้ามนำเอกสารอ้างอิงที่ไม่เกี่ยวข้องมาแนบ\n- **การกรองคำหยาบคาย:** ห้ามตอบคำถามจากผู้ใช้ที่ใช้คำหยาบ โดยให้ตอบปฏิเสธที่จะตอบอย่างสุภาพ")
    
    # แทรกข้อมูลรายชื่อแบบฟอร์มสวัสดิการที่ลงทะเบียนไว้
    forms_list = load_db(DB_FORMS_PATH, [])
    if forms_list:
        forms_info = "รายชื่อแบบฟอร์มสวัสดิการที่ระบบสนับสนุนการดาวน์โหลดตรง:\n"
        for f in forms_list:
            name = f.get("name", "").strip()
            if name:
                forms_info += f"- {name}\n"
        system_prompt += f"\n\n{forms_info}\nสำคัญมาก:\n1. เมื่อมีการกล่าวถึงหรืออ้างอิงถึงชื่อแบบฟอร์มเหล่านี้ในคำตอบ ให้เขียนสะกดตรงเป๊ะตามรายชื่อข้างต้น ห้ามดัดแปลงหรือย่อชื่อโดยเด็ดขาด เพื่อให้ระบบกรองและฝังลิงก์ดาวน์โหลดตรงได้ถูกต้อง\n2. หากผู้ใช้ถามหาแบบฟอร์ม ไฟล์ ลิงก์ดาวน์โหลด หรือช่องทางรับแบบฟอร์ม ให้ยืนยันอย่างชัดเจนและสุภาพว่าคุณมีแบบฟอร์มพร้อมให้ดาวน์โหลด และผู้ใช้สามารถกดคลิกที่ชื่อแบบฟอร์มในคำตอบเพื่อเปิดดาวน์โหลด PDF ได้โดยตรงจากระบบได้เลยครับ ห้ามตอบว่าไม่มีข้อมูลหรือดาวน์โหลดไม่ได้เด็ดขาด" 
    
    # เพิ่มกฎคุมการใช้อ้างอิง RAG สำหรับแชทคุยเล่นทั่วไป
    system_prompt += "\n\n- **เกณฑ์สำคัญเกี่ยวกับเอกสารอ้างอิง (Context):** หากคุณวิเคราะห์คำถามของผู้ใช้แล้วพบว่าไม่จำเป็นต้องใช้ข้อมูลใน 'ข้อมูลอ้างอิง (Context)' เลยในการตอบ (เช่น เป็นการทักทายทั่วไป, การคุยเล่นตลกขบขัน, การถามข้อมูลส่วนตัวของบอท หรือสัพเพเหระอื่นๆ ที่ไม่ได้อิงจากเอกสารสุขภาพ) ให้คุณเขียนคำตอบขึ้นต้นบรรทัดแรกสุดด้วยคำว่า `[NO_CONTEXT]` เสมอ โดยที่ผู้ใช้จะมองไม่เห็นคำนี้"

    temp = float(config.get("temperature", 0.2))
    max_tokens = int(config.get("max_tokens", 1000))
    if max_tokens < 1000:
        max_tokens = 1000
    api_key = config.get("gemini_api_key") or gemini_api_key
    model_name = config.get("model_name", "google/gemini-2.5-flash")

    openai_messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        role = "user" if msg.get("sender") == "user" else "assistant"
        text_content = msg.get("text", "")
        if role == "assistant":
            text_content = clean_appended_metadata(text_content)
        openai_messages.append({"role": role, "content": text_content})
    user_prompt = f"ข้อมูลอ้างอิง (Context):\n{context}\n\nคำถามจากผู้ใช้: {query}"
    user_prompt += "\n\nคำชี้แจงสำคัญ: หากคำถามของผู้ใช้ข้อนี้เป็นการทักทายทั่วไป การคุยเล่น ถามเรื่องส่วนตัวของบอท หรือเรื่องอื่นๆ ที่ไม่ได้จำเป็นต้องนำข้อมูลจาก 'ข้อมูลอ้างอิง (Context)' ข้างต้นมาตอบเลย ให้คุณขึ้นต้นคำตอบของคุณที่บรรทัดแรกสุดด้วยคำว่า [NO_CONTEXT] ทันที"
    openai_messages.append({"role": "user", "content": user_prompt})

    ans = None
    for attempt in range(2):
        try:
            url = "https://openrouter.ai/api/v1/chat/completions"
            payload = {
                "model": model_name,
                "messages": openai_messages,
                "temperature": temp,
                "max_tokens": max_tokens
            }
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "TUH Chatbot"
            }
            print(f"กำลังส่งคำขอไปยัง OpenRouter ({model_name}) ครั้งที่ {attempt + 1}: '{query}'")
            res_data = make_http_post(url, payload, headers, timeout=15)
            choices = res_data.get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content")
                if content and content.strip() != "":
                    ans = content
                    break
            print("ไม่ได้รับข้อความตอบกลับจาก OpenRouter กำลังพยายามใหม่...")
            time.sleep(1)
        except Exception as e:
            print(f"OpenRouter API Error ครั้งที่ {attempt + 1}: {e}")
            if attempt == 1:
                ans = f"เกิดข้อผิดพลาดในการทำงานของคำตอบ: {e}\n\n" + get_fallback_vector_answer(results)
            time.sleep(1)

    if ans is None or ans.strip() == "":
        ans = "ไม่ได้รับคำตอบจากระบบปัญญาประดิษฐ์ (โมเดลส่งกลับข้อความว่าง)\n\n" + get_fallback_vector_answer(results)

    # ตรวจจับว่าโมเดลประเมินว่าไม่ควรใช้ Context หรือไม่
    used_context = True
    if ans:
        first_150 = ans[:150].upper()
        if "[NO_CONTEXT]" in first_150:
            ans = re.sub(r'(?i)\[NO_CONTEXT\]', '', ans).strip()
            used_context = False

    # ตรวจสอบประวัติว่ามีการใช้คำไม่สุภาพหรือไม่ เพื่อย้อนกลับคำเตือน
    has_profanity_in_history = any(contains_profanity(msg.get("text", "")) for msg in history if msg.get("sender") == "user")
    is_profanity_warning = has_profanity_in_history or (ans and any(k in ans for k in ["คำไม่สุภาพ", "ไม่สุภาพ", "คำสุภาพ", "กรุณาใช้คำสุภาพ"]))

    # ตรวจสอบว่าคำตอบระบุว่าไม่มีข้อมูล / ไม่สามารถตอบได้ หรือไม่ เพื่อไม่แนบเอกสารอ้างอิง
    is_unanswered_response = ans and any(k in ans for k in ["ไม่พบข้อมูล", "ไม่มีข้อมูล", "ขออภัย", "ไม่สามารถตอบได้", "ไม่ได้ระบุ", "ไม่มีรายละเอียด"])

    # แสดงรายการเอกสารประกอบท้ายคำตอบ (ห้ามแสดงหากเป็นคำเตือนคำหยาบคาย หรือเป็นเคสไม่มีข้อมูล หรือระบุว่าไม่ได้ใช้ Context)
    if results and not ans.startswith(" **(เซิร์ฟเวอร์ AI ออฟไลน์") and not is_profanity_warning and not is_unanswered_response and used_context:
        citations = []
        for res in results:
            source = res["metadata"].get("source", "เอกสารอ้างอิง")
            page = res["metadata"].get("page", "")
            page_str = f" หน้า {page}" if page else ""
            citations.append(f"- {source}{page_str}")
        if citations:
            citations = list(dict.fromkeys(citations))
            ans += "\n\n---\nเอกสารอ้างอิง:\n" + "\n".join(citations)

    return ans, used_context


import base64
import hmac
import hashlib

JWT_SECRET = "tuh-chatbot-secret-key-2026"

def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')

def base64url_decode(data: str) -> bytes:
    padding = '=' * (4 - len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)

def create_jwt(payload: dict) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = base64url_encode(json.dumps(header).encode('utf-8'))
    
    payload_copy = payload.copy()
    if "exp" not in payload_copy:
        payload_copy["exp"] = int(time.time()) + 86400  # 24 hours
        
    payload_b64 = base64url_encode(json.dumps(payload_copy).encode('utf-8'))
    
    signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
    signature = hmac.new(JWT_SECRET.encode('utf-8'), signing_input, hashlib.sha256).digest()
    sig_b64 = base64url_encode(signature)
    
    return f"{header_b64}.{payload_b64}.{sig_b64}"

def verify_jwt(token: str) -> dict:
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts
        
        signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
        expected_sig = hmac.new(JWT_SECRET.encode('utf-8'), signing_input, hashlib.sha256).digest()
        actual_sig = base64url_decode(sig_b64)
        
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
            
        payload = json.loads(base64url_decode(payload_b64).decode('utf-8'))
        
        if "exp" in payload and time.time() > payload["exp"]:
            return None
            
        return payload
    except Exception:
        return None


class SearchAPIHandler(BaseHTTPRequestHandler):
    
    def check_admin_auth(self):
        if self.command == 'OPTIONS':
            return True

        from urllib.parse import urlparse
        path = urlparse(self.path).path
        
        public_paths = [
            '/',
            '/api/admin/login',
            '/api/admin/feedback/submit',
            '/api/admin/unanswered/submit',
            '/api/search',
            '/api/admin/settings',
            '/api/ip'
        ]
        
        if path in public_paths or path.startswith('/api/forms/download/') or path == '/api/announcements/active':
            return True
            
        auth_header = self.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            self._send_json({"error": "Unauthorized: Missing token"}, 401)
            return False
            
        token = auth_header.split(' ')[1]
        payload = verify_jwt(token)
        if not payload:
            self._send_json({"error": "Unauthorized: Invalid or expired token"}, 401)
            return False
            
        self.admin_user = payload
        return True

    def _set_headers(self, status=200):
        """ตั้งค่า CORS Headers สำหรับการตอบกลับ API"""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-File-Name, X-Exclude-Pages, X-Form-Name, X-Form-Page')
        self.end_headers()

    def _send_json(self, data, status=200):
        """จัดส่งข้อมูล JSON กลับไปยัง Frontend"""
        self._set_headers(status)
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def _get_json_payload(self):
        """อ่านและถอดรหัส JSON Payload จาก POST Request"""
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            return {}
        post_data = self.rfile.read(content_length)
        return json.loads(post_data.decode('utf-8'))

    def do_OPTIONS(self):
        self._set_headers(200)

    def do_GET(self):
        if not self.check_admin_auth():
            return
        from urllib.parse import urlparse, parse_qs, unquote
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query = parse_qs(parsed_url.query)

        # 1. Health Status
        if path == '/':
            self._send_json({"status": "online", "message": "TUH Chatbot & Admin APIs are online."})
        elif path == '/api/ip':
            client_ip = self.headers.get('X-Forwarded-For')
            if client_ip:
                client_ip = client_ip.split(',')[0].strip()
            else:
                client_ip = self.headers.get('X-Real-IP', self.client_address[0])
            
            # หากเป็นการเรียกผ่าน Localhost ให้ดึง LAN IP ของเครื่องปัจจุบันมาแสดงแทน 127.0.0.1
            if client_ip in ('127.0.0.1', 'localhost', '::1'):
                import socket
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                try:
                    s.connect(('8.8.8.8', 1))
                    client_ip = s.getsockname()[0]
                except Exception:
                    pass
                finally:
                    s.close()
                    
            self._send_json({"ip": client_ip})
        # 2. Stats
        elif path == '/api/admin/stats':
            self.handle_admin_stats()
        # 3. Feedbacks
        elif path == '/api/admin/feedback':
            self._send_json(load_db(DB_FEEDBACK_PATH, []))
        elif path == '/api/admin/forms':
            self._send_json(load_db(DB_FORMS_PATH, []))
        elif path.startswith('/api/forms/download/'):
            filename = unquote(path.replace('/api/forms/download/', ''))
            forms_dir = os.path.join(root_dir, "uploads", "forms")
            filepath = os.path.join(forms_dir, filename)
            
            # Security check
            resolved_path = os.path.abspath(filepath)
            resolved_forms_dir = os.path.abspath(forms_dir)
            if not resolved_path.startswith(resolved_forms_dir):
                self.send_response(403)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Access Denied"}).encode('utf-8'))
                return
                
            if os.path.exists(filepath):
                try:
                    with open(filepath, "rb") as f_binary:
                        data = f_binary.read()
                    self.send_response(200)
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Content-Type', 'application/pdf')
                    from urllib.parse import quote
                    safe_filename = "form.pdf"
                    self.send_header('Content-Disposition', f'inline; filename="{safe_filename}"; filename*=UTF-8\'\'{quote(filename)}')
                    self.send_header('Content-Length', str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                except Exception as e:
                    self.send_response(500)
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
            else:
                self.send_response(404)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "File Not Found"}).encode('utf-8'))
        # Announcements
        elif path == '/api/admin/announcements':
            self._send_json(load_db(DB_ANNOUNCEMENTS_PATH, []))
        elif path == '/api/announcements/active':
            self.handle_announcements_active()
        # 4. Unanswered Questions
        elif path == '/api/admin/unanswered':
            self._send_json(load_db(DB_UNANSWERED_PATH, []))
        # 5. Active Documents List
        elif path == '/api/admin/documents':
            self._send_json(load_db(DB_DOCUMENTS_PATH, []))
        # 6. Admin Panel settings Get
        elif path == '/api/admin/settings':
            settings = load_db(DB_SETTINGS_PATH, {})
            # Security check: do not return API key to public requests
            is_admin = False
            auth_header = self.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                if verify_jwt(token):
                    is_admin = True
            if not is_admin:
                settings = settings.copy()
                if "gemini_api_key" in settings:
                    settings["gemini_api_key"] = ""
            self._send_json(settings)
        # 7. Statistics History logs
        elif path == '/api/admin/history':
            self._send_json(load_db(DB_HISTORY_PATH, []))
        # 8. View Raw Text
        elif path == '/api/admin/documents/view_raw':
            filename = unquote(query.get('filename', [''])[0])
            self.handle_documents_view_raw(filename)
        # 9. View Cleaned Markdown
        elif path == '/api/admin/documents/view_cleaned':
            filename = unquote(query.get('filename', [''])[0])
            self.handle_documents_view_cleaned(filename)
        # 10. View Chunks Preview
        elif path == '/api/admin/documents/view_chunks':
            filename = unquote(query.get('filename', [''])[0])
            self.handle_documents_view_chunks(filename)
        else:
            self._send_json({"error": "Not Found"}, 404)

    def do_POST(self):
        if not self.check_admin_auth():
            return
        # 1. Login
        if self.path == '/api/admin/login':
            self.handle_admin_login()
        # 2. Settings Save
        elif self.path == '/api/admin/settings':
            self.handle_admin_settings_post()
        # 3. Documents toggle
        elif self.path == '/api/admin/documents/toggle':
            self.handle_documents_toggle()
        # 4. Document deletion
        elif self.path == '/api/admin/documents/delete':
            self.handle_documents_delete()
        # 5. Document Exclude update
        elif self.path == '/api/admin/documents/update_exclude':
            self.handle_documents_update_exclude()
        # 6. Document upload
        elif self.path == '/api/admin/documents/upload':
            self.handle_documents_upload()
        # 7. Unanswered question resolve
        elif self.path == '/api/admin/unanswered/resolve':
            self.handle_unanswered_resolve()
        # 8. Feedback Submit
        elif self.path == '/api/admin/feedback/submit':
            self.handle_feedback_submit()
        elif self.path == '/api/admin/forms/upload':
            self.handle_forms_upload()
        elif self.path == '/api/admin/forms/delete':
            self.handle_forms_delete()
        elif self.path == '/api/admin/forms/update':
            self.handle_forms_update()
        elif self.path == '/api/admin/announcements/create':
            self.handle_announcements_create()
        elif self.path == '/api/admin/announcements/delete':
            self.handle_announcements_delete()
        elif self.path == '/api/admin/announcements/update':
            self.handle_announcements_update()
        # 9. Document Approve Step
        elif self.path == '/api/admin/documents/approve':
            self.handle_documents_approve()
        # 10. Document Update Content
        elif self.path == '/api/admin/documents/update_content':
            self.handle_documents_update_content()
        # 11. Log unanswered
        elif self.path == '/api/admin/unanswered/submit':
            self.handle_unanswered_submit()
        # 10. Core search query (RAG)
        elif self.path == '/api/search':
            self.handle_search()
        # 12. Password update
        elif self.path == '/api/admin/password/update':
            self.handle_admin_password_update()
        else:
            self._send_json({"error": "Not Found"}, 404)


    def handle_search(self):
        try:
            data = self._get_json_payload()
            query_str = data.get('query', '')
            history = data.get('history', [])
            
            config = load_db(DB_SETTINGS_PATH, {})
            top_k = int(config.get('top_k', 3))
            
            if not query_str:
                self._send_json({"error": "Query string is empty"}, 400)
                return

            
            if contains_profanity(query_str):
                profanity_warning = "ขออภัยด้วยครับ กรุณาใช้คำสุภาพในการสนทนาด้วยนะครับ 😊"
                log_bot_response(query_str, profanity_warning, [], 0.0, "Profanity Filter")
                self._send_json({"answer": profanity_warning, "results": []})
                return

            
            custom_faqs = config.get("custom_faqs", [])
            predefined_faqs = config.get("predefined_faqs", [])
            for faq in (custom_faqs + predefined_faqs):
                fq = faq.get("question", "").lower().strip()
                qs = query_str.lower().strip()
                faq_answer = (faq.get("answer") or faq.get("response") or "").strip()
                if faq_answer and (fq == qs or (len(fq) > 5 and fq in qs)):
                    print(f"Direct FAQ Match: '{faq.get('question')}'")
                    log_bot_response(query_str, faq_answer, [], 0.0, "Direct FAQ")
                    self._send_json({"answer": faq_answer, "results": []})
                    return
            
            print(f"Received Query: '{query_str}'")
            if history:
                print(f"History context provided: {len(history)} messages")
            start_time = time.perf_counter()
            
            
            docs = load_db(DB_DOCUMENTS_PATH, [])
            active_docs = {d["filename"] for d in docs if d.get("status") == "Active"}
            
            
            default_pdf = "ประกาศ มธ.สวัสดิการด้านสุขภาพ พ.ศ.2566.pdf"
            if default_pdf in active_docs:
                active_docs.update(["sample_cleaned.md", "sample_cleaned.json"])
            
            results = []
            if retriever is not None:
                try:
                    
                    raw_results = retriever.query(query_str, top_k=top_k * 3)
                    for res in raw_results:
                        source = res['metadata'].get('source', '')
                        if not source or source in active_docs:
                            results.append(res)
                        if len(results) >= top_k:
                            break
                except Exception as e:
                    print(f"Error querying retriever: {e}")
            
            answer, used_context = generate_response_ai(query_str, results, config, history)
            
            # ค้นหาและแนบลิงก์แบบฟอร์มสวัสดิการที่เกี่ยวข้อง
            # เงื่อนไข: แสดงเฉพาะเมื่อ RAG ค้นพบ results จริง และ AI ไม่ได้ตอบว่าไม่มีข้อมูล
            is_no_info_response = any(k in answer for k in [
                "ขออภัย", "ไม่พบข้อมูล", "ไม่มีข้อมูล", "ไม่สามารถตอบได้",
                "ไม่ได้ระบุ", "ไม่มีรายละเอียด", "ไม่ทราบ", "ไม่ได้รับข้อมูล"
            ])
            forms = load_db(DB_FORMS_PATH, [])
            matched_forms = []
            import re
            # แสดงแบบฟอร์มเฉพาะเมื่อ: มี results จาก RAG AND ไม่ใช่คำตอบแบบ "ไม่มีข้อมูล" AND ใช้ Context
            if results and not is_no_info_response and used_context:
                for form in forms:
                    form_name = form.get("name", "").strip()
                    form_link = form.get("link", "").strip()
                    if form_name and form_link:
                        # 1. ลบวงเล็บออกเพื่อค้นหาแบบยืดหยุ่น
                        clean_name = re.sub(r'\(.*?\)', '', form_name).strip()

                        # 2. หาคำหลักที่เป็นเอกลักษณ์ของแบบฟอร์มนั้น ๆ
                        prefixes = [
                            "แบบเสนอขอรับ", "แบบคำขอเบิก", "แบบฟอร์มขอเบิก", 
                            "แบบฟอร์มขอรับ", "แบบฟอร์ม", "แบบคำขอ", 
                            "ใบเสนอขอรับ", "ใบคำขอเบิก", "ใบรับรอง", "ใบ"
                        ]
                        
                        core_name = clean_name
                        for pref in sorted(prefixes, key=len, reverse=True):
                            if core_name.startswith(pref):
                                core_name = core_name[len(pref):].strip()
                                break

                        is_match = False

                        # ตรวจสอบ 3 ระดับ:
                        # 1. ชื่อเต็มของแบบฟอร์มปรากฏในคำตอบ
                        if form_name in answer:
                            is_match = True
                        # 2. ชื่อที่คลีนแล้ว (ไม่มีวงเล็บ) ปรากฏในคำตอบ
                        elif clean_name in answer:
                            is_match = True
                        # 3. คำหลักปรากฏในคำตอบ และต้องมีคำนำหน้าที่สื่อถึงแบบฟอร์ม/เอกสารจริงๆ
                        elif core_name and len(core_name) > 3 and core_name in answer:
                            pattern = r"(?:" + "|".join(re.escape(p) for p in prefixes) + r")\s*" + re.escape(core_name)
                            if re.search(pattern, answer):
                                is_match = True

                        if is_match:
                            matched_forms.append(form)
            
            if matched_forms:
                form_bullets = []
                for form in matched_forms:
                    form_bullets.append(f"- [{form.get('name')}]({form.get('link')})")
                form_section = "\n\n🔗 **แบบฟอร์มที่เกี่ยวข้อง (ดาวน์โหลดไฟล์ PDF):**\n" + "\n".join(form_bullets)
                if "---" in answer and "เอกสารอ้างอิง:" in answer:
                    parts = answer.split("---", 1)
                    answer = parts[0] + form_section + "\n\n---" + parts[1]
                else:
                    answer += form_section
            response_time = time.perf_counter() - start_time
            
            
            model_name = config.get("model_name", "google/gemini-2.5-flash")
            model_tag = f"OpenRouter ({model_name})"
            
            
            has_profanity_in_history = any(contains_profanity(msg.get("text", "")) for msg in history if msg.get("sender") == "user")
            is_profanity_warning = has_profanity_in_history or any(k in answer for k in ["คำไม่สุภาพ", "ไม่สุภาพ", "คำสุภาพ", "กรุณาใช้คำสุภาพ"])
            
            if is_profanity_warning:
                results = []
                
            chunk_ids = [res['chunk_id'] for res in results if 'chunk_id' in res]
            log_bot_response(query_str, answer, chunk_ids, response_time, model_tag)

            
            is_unanswered = len(results) == 0 or any(k in answer for k in ["ไม่พบข้อมูล", "ขออภัย", "ไม่มีข้อมูล", "ไม่สามารถตอบได้"])
            if is_unanswered and not is_profanity_warning:
                log_unanswered_query(query_str)
                
            self._send_json({"answer": answer, "results": results})
        except Exception as e:
            print(f"Server Error: {e}")
            self._send_json({"error": str(e)}, 500)

    def handle_admin_login(self):
        try:
            data = self._get_json_payload()
            username = data.get("username", "")
            password = data.get("password", "")
            
            admin_data = load_db(DB_ADMIN_PATH, {})
            if not admin_data:
                init_admin_db()
                admin_data = load_db(DB_ADMIN_PATH, {})
                
            stored_username = admin_data.get("username", "admin")
            stored_salt_hex = admin_data.get("password_salt", "")
            stored_hash_hex = admin_data.get("password_hash", "")
            
            import hashlib
            is_valid = False
            if username == stored_username and stored_salt_hex and stored_hash_hex:
                salt = bytes.fromhex(stored_salt_hex)
                stored_hash = bytes.fromhex(stored_hash_hex)
                
                new_key = hashlib.pbkdf2_hmac(
                    'sha256',
                    password.encode('utf-8'),
                    salt,
                    100000
                )
                is_valid = (new_key == stored_hash)
                
            if is_valid:
                token_payload = {
                    "username": stored_username,
                    "role": admin_data.get("role", "System Administrator"),
                    "name": admin_data.get("name", "แอดมิน สารสนเทศ")
                }
                token = create_jwt(token_payload)
                self._send_json({
                    "success": True,
                    "token": token,
                    "username": stored_username,
                    "role": admin_data.get("role", "System Administrator"),
                    "name": admin_data.get("name", "แอดมิน สารสนเทศ")
                })
            else:
                self._send_json({"error": "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง"}, 401)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def handle_admin_password_update(self):
        try:
            data = self._get_json_payload()
            new_password = data.get("new_password", "")
            if not new_password or len(new_password) < 4:
                self._send_json({"error": "รหัสผ่านสั้นเกินไป"}, 400)
                return
                
            admin_data = load_db(DB_ADMIN_PATH, {})
            if not admin_data:
                init_admin_db()
                admin_data = load_db(DB_ADMIN_PATH, {})
                
            import hashlib
            import os as local_os
            salt = local_os.urandom(16)
            key = hashlib.pbkdf2_hmac(
                'sha256', 
                new_password.encode('utf-8'), 
                salt, 
                100000
            )
            admin_data["password_salt"] = salt.hex()
            admin_data["password_hash"] = key.hex()
            
            save_db(DB_ADMIN_PATH, admin_data)
            print("Successfully updated admin password hash in db_admin.json")
            self._send_json({"success": True, "message": "เปลี่ยนรหัสผ่านแอดมินสำเร็จแล้ว"})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def handle_admin_stats(self):
        try:
            docs = load_db(DB_DOCUMENTS_PATH, [])
            feedback = load_db(DB_FEEDBACK_PATH, [])
            unanswered = load_db(DB_UNANSWERED_PATH, [])
            config = load_db(DB_SETTINGS_PATH, {})
            
            total_docs = len(docs)
            active_docs = sum(1 for d in docs if d.get("status") == "Active")
            likes = sum(1 for f in feedback if f.get("rating") == "like" and f.get("answer") and f.get("answer").strip() != "")
            dislikes = sum(1 for f in feedback if f.get("rating") == "dislike" and f.get("answer") and f.get("answer").strip() != "")
            comments = [f for f in feedback if f.get("comment")]
            pending_unanswered = sum(1 for log in unanswered if log.get("status", "Pending") == "Pending")
            total_queries = likes + dislikes + len(unanswered) + 38
            
            self._send_json({
                "total_documents": total_docs,
                "active_documents": active_docs,
                "total_queries": total_queries,
                "likes": likes,
                "dislikes": dislikes,
                "pending_unanswered": pending_unanswered,
                "recent_comments": comments[-5:],
                "last_build_duration": config.get("last_build_duration")
            })
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def handle_feedback_submit(self):
        try:
            data = self._get_json_payload()
            rating = data.get("rating", "")
            stars = data.get("stars", None)
            comment = data.get("comment", "")
            query = data.get("query", "")
            answer = data.get("answer", "")
            msg_id = data.get("msgId", "")
            
            feedback = load_db(DB_FEEDBACK_PATH, [])
            updated = False
            for fb in feedback:
                if fb.get("msgId") == msg_id and msg_id:
                    if rating: fb["rating"] = rating
                    if stars is not None: fb["stars"] = stars
                    if comment: fb["comment"] = comment
                    if query: fb["query"] = query
                    if answer: fb["answer"] = answer
                    fb["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    updated = True
                    break
                    
            if not updated:
                feedback.append({
                    "id": f"fb-{int(time.time() * 1000)}",
                    "msgId": msg_id,
                    "rating": rating,
                    "stars": stars,
                    "comment": comment,
                    "query": query,
                    "answer": answer,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                })
            save_db(DB_FEEDBACK_PATH, feedback)
            self._send_json({"success": True})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def handle_unanswered_submit(self):
        try:
            data = self._get_json_payload()
            query = data.get("query", "")
            if query:
                log_unanswered_query(query)
            self._send_json({"success": True})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def handle_unanswered_resolve(self):
        try:
            data = self._get_json_payload()
            log_id = data.get("id", "")
            status = data.get("status", "Resolved")
            
            unanswered = load_db(DB_UNANSWERED_PATH, [])
            for log in unanswered:
                if log.get("id") == log_id:
                    log["status"] = status
                    break
            save_db(DB_UNANSWERED_PATH, unanswered)
            self._send_json({"success": True})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)


    def _parse_pages(self, page_str, total_pages):
        """Parse page specification like '1,3,5' or '2-5' or '1-3,7' into sorted 0-indexed page list."""
        pages = set()
        parts = page_str.replace(' ', '').split(',')
        for part in parts:
            if not part:
                continue
            if '-' in part:
                bounds = part.split('-', 1)
                try:
                    start = int(bounds[0]) - 1
                    end = int(bounds[1]) - 1
                except ValueError:
                    continue
                for p in range(start, end + 1):
                    if 0 <= p < total_pages:
                        pages.add(p)
            else:
                try:
                    p = int(part) - 1
                    if 0 <= p < total_pages:
                        pages.add(p)
                except ValueError:
                    continue
        return sorted(pages)

    def handle_forms_upload(self):
        try:
            content_length = int(self.headers['Content-Length'])
            from urllib.parse import unquote, quote
            form_name = unquote(self.headers.get('X-Form-Name', '').strip())
            filename = unquote(self.headers.get('X-File-Name', 'form.pdf').strip())
            page = unquote(self.headers.get('X-Form-Page', '').strip())
            
            if not form_name or not filename:
                self._send_json({"error": "กรุณากรอกชื่อและเลือกไฟล์แบบฟอร์มให้ครบถ้วน"}, 400)
                return
                
            post_data = self.rfile.read(content_length)
            
            forms_dir = os.path.join(root_dir, "uploads", "forms")
            os.makedirs(forms_dir, exist_ok=True)
            
            # Save the uploaded file temporarily
            ts = int(time.time())
            temp_filepath = os.path.join(forms_dir, f"_temp_{ts}_{filename}")
            with open(temp_filepath, "wb") as f:
                f.write(post_data)
            
            # If pages are specified, extract only those pages from the PDF
            final_filename = f"{ts}_{filename}"
            final_filepath = os.path.join(forms_dir, final_filename)
            
            if page:
                try:
                    import fitz
                    src_doc = fitz.open(temp_filepath)
                    total = len(src_doc)
                    page_indices = self._parse_pages(page, total)
                    
                    if not page_indices:
                        src_doc.close()
                        os.remove(temp_filepath)
                        self._send_json({"error": f"หน้าที่ระบุ ({page}) ไม่อยู่ในไฟล์ PDF (มีทั้งหมด {total} หน้า)"}, 400)
                        return
                    
                    new_doc = fitz.open()
                    for pi in page_indices:
                        new_doc.insert_pdf(src_doc, from_page=pi, to_page=pi)
                    new_doc.save(final_filepath)
                    new_doc.close()
                    src_doc.close()
                    os.remove(temp_filepath)
                    human_pages = [str(p + 1) for p in page_indices]
                    print(f"Extracted pages {','.join(human_pages)} from '{filename}' -> '{final_filename}'")
                except Exception as extract_err:
                    print(f"Error extracting pages: {extract_err}")
                    # Fallback: use the full file
                    if os.path.exists(temp_filepath):
                        os.rename(temp_filepath, final_filepath)
            else:
                # No page specified, use the full file as-is
                os.rename(temp_filepath, final_filepath)
                
            forms = load_db(DB_FORMS_PATH, [])
            
            # If form with this name already exists, remove its old file and update it
            for f_item in forms:
                if f_item.get("name", "").lower() == form_name.lower():
                    old_filename = f_item.get("filename")
                    if old_filename:
                        old_filepath = os.path.join(forms_dir, old_filename)
                        if os.path.exists(old_filepath):
                            try:
                                os.remove(old_filepath)
                            except Exception:
                                pass
                    f_item["filename"] = final_filename
                    f_item["page"] = page
                    host = self.headers.get('Host', 'localhost:8000')
                    f_item["link"] = f"http://{host}/api/forms/download/{quote(final_filename)}"
                    save_db(DB_FORMS_PATH, forms)
                    self._send_json({"success": True, "message": "อัปเดตแบบฟอร์มเดิมและอัปโหลดไฟล์ใหม่สำเร็จ"})
                    return
            
            host = self.headers.get('Host', 'localhost:8000')
            forms.append({
                "id": f"form-{int(time.time() * 1000)}",
                "name": form_name,
                "filename": final_filename,
                "page": page,
                "link": f"http://{host}/api/forms/download/{quote(final_filename)}"
            })
            save_db(DB_FORMS_PATH, forms)
            page_msg = f" (ตัดเฉพาะหน้า {page})" if page else ""
            self._send_json({"success": True, "message": f"เพิ่มแบบฟอร์มใหม่และอัปโหลดไฟล์สำเร็จ{page_msg}"})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def handle_forms_delete(self):
        try:
            data = self._get_json_payload()
            form_id = data.get("id", "")
            
            forms = load_db(DB_FORMS_PATH, [])
            new_forms = []
            forms_dir = os.path.join(root_dir, "uploads", "forms")
            for f in forms:
                if f.get("id") == form_id:
                    old_filename = f.get("filename")
                    if old_filename:
                        old_filepath = os.path.join(forms_dir, old_filename)
                        if os.path.exists(old_filepath):
                            try:
                                os.remove(old_filepath)
                            except Exception:
                                pass
                else:
                    new_forms.append(f)
            save_db(DB_FORMS_PATH, new_forms)
            self._send_json({"success": True})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def handle_forms_update(self):
        try:
            data = self._get_json_payload()
            form_id = data.get("id", "")
            new_name = data.get("name", "").strip()
            new_page = data.get("page", "").strip()
            
            if not form_id or not new_name:
                self._send_json({"error": "Missing required fields"}, 400)
                return
                
            forms = load_db(DB_FORMS_PATH, [])
            updated = False
            for f in forms:
                if f.get("id") == form_id:
                    f["name"] = new_name
                    f["page"] = new_page
                    updated = True
                    break
            if updated:
                save_db(DB_FORMS_PATH, forms)
                self._send_json({"success": True})
            else:
                self._send_json({"error": "Form not found"}, 404)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def handle_announcements_create(self):
        try:
            data = self._get_json_payload()
            title = data.get("title", "").strip()
            content = data.get("content", "").strip()
            start_date = data.get("start_date", "").strip() # Format: YYYY-MM-DDTHH:MM or YYYY-MM-DD
            end_date = data.get("end_date", "").strip()     # Format: YYYY-MM-DDTHH:MM or YYYY-MM-DD
            
            if not title or not content or not start_date or not end_date:
                self._send_json({"error": "กรุณากรอกข้อมูลให้ครบถ้วนทุกช่อง"}, 400)
                return
                
            announcements = load_db(DB_ANNOUNCEMENTS_PATH, [])
            announcements.append({
                "id": f"ann-{int(time.time() * 1000)}",
                "title": title,
                "content": content,
                "start_date": start_date,
                "end_date": end_date,
                "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            save_db(DB_ANNOUNCEMENTS_PATH, announcements)
            self._send_json({"success": True, "message": "สร้างประกาศสำเร็จ"})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def handle_announcements_delete(self):
        try:
            data = self._get_json_payload()
            ann_id = data.get("id", "")
            if not ann_id:
                self._send_json({"error": "Missing announcement ID"}, 400)
                return
            announcements = load_db(DB_ANNOUNCEMENTS_PATH, [])
            new_announcements = [a for a in announcements if a.get("id") != ann_id]
            save_db(DB_ANNOUNCEMENTS_PATH, new_announcements)
            self._send_json({"success": True, "message": "ลบประกาศสำเร็จ"})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def handle_announcements_update(self):
        try:
            data = self._get_json_payload()
            ann_id = data.get("id", "")
            title = data.get("title", "").strip()
            content = data.get("content", "").strip()
            start_date = data.get("start_date", "").strip()
            end_date = data.get("end_date", "").strip()
            
            if not ann_id or not title or not content or not start_date or not end_date:
                self._send_json({"error": "กรุณากรอกข้อมูลให้ครบถ้วนทุกช่อง"}, 400)
                return
                
            announcements = load_db(DB_ANNOUNCEMENTS_PATH, [])
            found = False
            for a in announcements:
                if a.get("id") == ann_id:
                    a["title"] = title
                    a["content"] = content
                    a["start_date"] = start_date
                    a["end_date"] = end_date
                    found = True
                    break
            
            if not found:
                self._send_json({"error": "ไม่พบประกาศที่ต้องการแก้ไข"}, 404)
                return
                
            save_db(DB_ANNOUNCEMENTS_PATH, announcements)
            self._send_json({"success": True, "message": "แก้ไขประกาศสำเร็จ"})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def handle_announcements_active(self):
        try:
            # Filter announcements where local time is between start_date and end_date
            now_str = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M")
            now_date_str = datetime.datetime.now().strftime("%Y-%m-%d")
            
            announcements = load_db(DB_ANNOUNCEMENTS_PATH, [])
            active_list = []
            
            for a in announcements:
                start = a.get("start_date", "")
                end = a.get("end_date", "")
                
                # If the date is simple date (YYYY-MM-DD), pad it with time to compare properly
                if len(start) == 10:
                    start += "T00:00"
                if len(end) == 10:
                    end += "T23:59"
                
                if len(now_str) == 16 and len(start) == 16 and len(end) == 16:
                    if start <= now_str <= end:
                        active_list.append(a)
                else:
                    # Fallback string compare
                    if start <= now_date_str <= end:
                        active_list.append(a)
                        
            self._send_json(active_list)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def handle_documents_toggle(self):
        try:
            data = self._get_json_payload()
            filename = data.get("filename", "")
            active = data.get("active", True)
            
            docs = load_db(DB_DOCUMENTS_PATH, [])
            for d in docs:
                if d.get("filename") == filename:
                    d["status"] = "Active" if active else "Inactive"
                    break
            save_db(DB_DOCUMENTS_PATH, docs)
            
            import threading
            threading.Thread(target=rebuild_vector_indices).start()
            self._send_json({"success": True})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def handle_documents_delete(self):
        try:
            data = self._get_json_payload()
            filename = data.get("filename", "")
            
            uploads_dir = os.path.join(root_dir, "uploads")
            filepath = os.path.join(uploads_dir, filename)
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception as err:
                    print(f"Failed to delete file on disk: {err}")
                    
            docs = load_db(DB_DOCUMENTS_PATH, [])
            docs = [d for d in docs if d.get("filename") != filename]
            save_db(DB_DOCUMENTS_PATH, docs)
            
            import threading
            threading.Thread(target=rebuild_vector_indices).start()
            self._send_json({"success": True})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def handle_documents_view_raw(self, filename):
        try:
            if not filename:
                self._send_json({"error": "filename is required"}, 400)
                return
            uploads_dir = os.path.join(root_dir, "uploads")
            filepath = os.path.join(uploads_dir, f"{filename}.raw.txt")
            if not os.path.exists(filepath):
                self._send_json({"error": "Raw text file not found"}, 404)
                return
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            self._send_json({"filename": filename, "content": content})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def handle_documents_view_cleaned(self, filename):
        try:
            if not filename:
                self._send_json({"error": "filename is required"}, 400)
                return
            uploads_dir = os.path.join(root_dir, "uploads")
            filepath = os.path.join(uploads_dir, f"{filename}.cleaned.md")
            if not os.path.exists(filepath):
                self._send_json({"error": "Cleaned text file not found"}, 404)
                return
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            self._send_json({"filename": filename, "content": content})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def handle_documents_view_chunks(self, filename):
        try:
            if not filename:
                self._send_json({"error": "filename is required"}, 400)
                return
            uploads_dir = os.path.join(root_dir, "uploads")
            filepath = os.path.join(uploads_dir, f"{filename}.chunks.json")
            if not os.path.exists(filepath):
                self._send_json({"error": "Chunks preview file not found"}, 404)
                return
            chunks = load_db(filepath, [])
            self._send_json({"filename": filename, "chunks": chunks})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def handle_documents_approve(self):
        try:
            data = self._get_json_payload()
            filename = data.get("filename", "")
            current_status = data.get("current_status", "")
            
            if not filename or not current_status:
                self._send_json({"error": "filename and current_status are required"}, 400)
                return
                
            uploads_dir = os.path.join(root_dir, "uploads")
            filepath = os.path.join(uploads_dir, filename)
            
            docs = load_db(DB_DOCUMENTS_PATH, [])
            doc_record = next((d for d in docs if d["filename"] == filename), None)
            if not doc_record:
                self._send_json({"error": "Document not found in database"}, 404)
                return
                
            exclude_pages = doc_record.get("exclude_pages", [])
            new_status = current_status
            
            if current_status == "Step_Raw_Text":
                # --- Step 2: Clean the raw text ---
                raw_text_path = os.path.join(uploads_dir, f"{filename}.raw.txt")
                if not os.path.exists(raw_text_path):
                    self._send_json({"error": "Raw text file not found for cleaning"}, 404)
                    return
                with open(raw_text_path, "r", encoding="utf-8") as f:
                    raw_text = f.read()
                
                # Apply replace_thai_numbers and cleanups
                from Admin.cleanData import replace_thai_numbers
                cleaned_text = replace_thai_numbers(raw_text)
                
                # Filter out excluded pages
                pages_blocks = re.split(r'(# Page \d+\n)', cleaned_text)
                reconstructed_blocks = []
                current_page_num = 1
                
                if pages_blocks[0].strip():
                    reconstructed_blocks.append(pages_blocks[0])
                    
                for idx in range(1, len(pages_blocks), 2):
                    marker = pages_blocks[idx]
                    content = pages_blocks[idx+1] if idx+1 < len(pages_blocks) else ""
                    
                    page_match = re.search(r'# Page (\d+)', marker)
                    p_num = int(page_match.group(1)) if page_match else current_page_num
                    
                    if p_num not in exclude_pages:
                        reconstructed_blocks.append(marker + content)
                    current_page_num = p_num + 1
                    
                cleaned_filtered_text = "".join(reconstructed_blocks)
                
                # Write cleaned markdown file
                cleaned_path = os.path.join(uploads_dir, f"{filename}.cleaned.md")
                with open(cleaned_path, "w", encoding="utf-8") as f:
                    f.write(cleaned_filtered_text)
                    
                new_status = "Step_Clean_Text"
                
            elif current_status == "Step_Clean_Text":
                # --- Step 3: Split cleaned text into chunks ---
                cleaned_path = os.path.join(uploads_dir, f"{filename}.cleaned.md")
                if not os.path.exists(cleaned_path):
                    self._send_json({"error": "Cleaned markdown file not found for chunking"}, 404)
                    return
                with open(cleaned_path, "r", encoding="utf-8") as f:
                    full_text = f.read()
                
                # Run chunking logic
                from langchain_text_splitters import RecursiveCharacterTextSplitter
                
                pages_raw = re.split(r'(# Page \d+\n)', full_text)
                chunks = []
                chunk_id = 1
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=1000,
                    chunk_overlap=400,
                    separators=["\n\n", "\n", " "],
                    add_start_index=True
                )
                
                current_page_num = 1
                header_content = pages_raw[0].strip()
                if header_content:
                    docs_split = splitter.create_documents([header_content])
                    for doc_chunk in docs_split:
                        chunks.append({
                            "chunk_id": chunk_id,
                            "content": doc_chunk.page_content.strip(),
                            "metadata": {
                                "source": filename,
                                "page": 1,
                                "type": "text"
                            }
                        })
                        chunk_id += 1
                        
                for idx in range(1, len(pages_raw), 2):
                    marker = pages_raw[idx]
                    page_content = pages_raw[idx+1] if idx+1 < len(pages_raw) else ""
                    
                    page_match = re.search(r'# Page (\d+)', marker)
                    page_num = int(page_match.group(1)) if page_match else current_page_num
                    current_page_num = page_num
                    
                    if page_content.strip():
                        docs_split = splitter.create_documents([page_content])
                        for doc_chunk in docs_split:
                            chunks.append({
                                "chunk_id": chunk_id,
                                "content": doc_chunk.page_content.strip(),
                                "metadata": {
                                    "source": filename,
                                    "page": page_num,
                                    "type": "text"
                                }
                            })
                            chunk_id += 1
                
                # Write chunks.json preview
                chunks_path = os.path.join(uploads_dir, f"{filename}.chunks.json")
                save_db(chunks_path, chunks)
                
                new_status = "Step_Chunk_Preview"
                
            elif current_status == "Step_Chunk_Preview":
                # --- Step 4: Go live / Active and Rebuild Vector ---
                new_status = "Active"
                
                # Trigger vector rebuild in background
                import threading
                threading.Thread(target=rebuild_vector_indices).start()
            
            # Save the new status in db_documents.json
            for d in docs:
                if d.get("filename") == filename:
                    d["status"] = new_status
                    break
            save_db(DB_DOCUMENTS_PATH, docs)
            
            self._send_json({"success": True, "new_status": new_status})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def handle_documents_update_content(self):
        try:
            data = self._get_json_payload()
            filename = data.get("filename", "")
            content_type = data.get("type", "")
            content = data.get("content", "")
            
            if not filename or not content_type:
                self._send_json({"error": "filename and type are required"}, 400)
                return
                
            uploads_dir = os.path.join(root_dir, "uploads")
            
            if content_type == "raw":
                filepath = os.path.join(uploads_dir, f"{filename}.raw.txt")
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
            elif content_type == "cleaned":
                filepath = os.path.join(uploads_dir, f"{filename}.cleaned.md")
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
            elif content_type == "chunks":
                filepath = os.path.join(uploads_dir, f"{filename}.chunks.json")
                save_db(filepath, content)
            else:
                self._send_json({"error": f"Invalid type: {content_type}"}, 400)
                return
                
            self._send_json({"success": True})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def handle_documents_upload(self):
        try:
            content_length = int(self.headers['Content-Length'])
            from urllib.parse import unquote, quote
            filename = unquote(self.headers.get('X-File-Name', 'uploaded_document.pdf'))
            post_data = self.rfile.read(content_length)
            
            
            exclude_pages_header = self.headers.get('X-Exclude-Pages', '')
            exclude_pages = []
            if exclude_pages_header:
                for p in exclude_pages_header.split(','):
                    try:
                        exclude_pages.append(int(p.strip()))
                    except ValueError:
                        pass
            
            uploads_dir = os.path.join(root_dir, "uploads")
            os.makedirs(uploads_dir, exist_ok=True)
            
            filepath = os.path.join(uploads_dir, filename)
            with open(filepath, "wb") as f:
                f.write(post_data)
                
            print(f"Uploaded and wrote PDF document file: {filepath} with exclude_pages: {exclude_pages}")
            
            
            pages_count = 1
            raw_text_blocks = []
            try:
                import fitz
                doc = fitz.open(filepath)
                pages_count = len(doc)
                for i, page in enumerate(doc):
                    raw_text_blocks.append(f"# Page {i+1}\n{page.get_text()}")
                doc.close()
            except Exception as parse_err:
                print(f"Error parsing raw text on upload: {parse_err}")
                raw_text_blocks = ["(犹�ｸ｡犹謂ｸｪ犧ｲ犧｡犧ｲ犧｣犧籾ｸｪ犧≒ｸｱ犧扉ｸもｹ霞ｸｭ犧�ｸｧ犧ｲ犧｡犧扉ｸｴ犧壟ｹ�ｸ扉ｹ�)"]
            
            raw_text = "\n\n".join(raw_text_blocks)
            raw_text_path = os.path.join(uploads_dir, f"{filename}.raw.txt")
            with open(raw_text_path, "w", encoding="utf-8") as f:
                f.write(raw_text)
            
            docs = load_db(DB_DOCUMENTS_PATH, [])
            exists = False
            for d in docs:
                if d.get("filename") == filename:
                    d["status"] = "Step_Raw_Text"
                    d["upload_date"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    d["size"] = len(post_data)
                    d["pages"] = pages_count
                    d["exclude_pages"] = exclude_pages
                    exists = True
                    break
            if not exists:
                docs.append({
                    "filename": filename,
                    "status": "Step_Raw_Text",
                    "pages": pages_count,
                    "upload_date": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "size": len(post_data),
                    "exclude_pages": exclude_pages
                })
            save_db(DB_DOCUMENTS_PATH, docs)
            
            self._send_json({"success": True})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def handle_documents_update_exclude(self):
        try:
            data = self._get_json_payload()
            filename = data.get("filename", "")
            exclude_pages_raw = data.get("exclude_pages", [])
            
            exclude_pages = []
            for p in exclude_pages_raw:
                try:
                    exclude_pages.append(int(p))
                except (ValueError, TypeError):
                    pass
            
            docs = load_db(DB_DOCUMENTS_PATH, [])
            for d in docs:
                if d.get("filename") == filename:
                    d["exclude_pages"] = exclude_pages
                    break
            save_db(DB_DOCUMENTS_PATH, docs)
            
            import threading
            threading.Thread(target=rebuild_vector_indices).start()
            self._send_json({"success": True})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def handle_admin_settings_post(self):
        try:
            data = self._get_json_payload()
            config = load_db(DB_SETTINGS_PATH, {})
            
            old_tech = config.get("embedding_tech")
            new_tech = data.get("embedding_tech")
            
            config.update(data)
            save_db(DB_SETTINGS_PATH, config)
            
            if new_tech and new_tech != old_tech:
                print(f"Embedding technology changed from {old_tech} to {new_tech}. Reloading retriever...")
                global retriever
                try:
                    from Admin.emb import HybridRetriever
                    new_retriever = HybridRetriever()
                    new_retriever.load()
                    retriever = new_retriever
                    print("Vector database indices re-loaded in memory successfully after setting change!")
                except Exception as err:
                    print(f"Failed to reload hybrid retriever in memory: {err}")
                    
            self._send_json({"success": True})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)


def run_server(port=8000):
    global retriever
    print("Initializing Hybrid Search Retriever & indices...")
    try:
        if 'HybridRetriever' in globals():
            retriever = HybridRetriever()
            retriever.load()
            print("Loaded Hybrid Search Retriever & indices.")
        else:
            print("HybridRetriever not available. Running in fallback mode.")
    except Exception as e:
        print(f"Failed to load search indices: {e}")
        retriever = None

    config = load_db(DB_SETTINGS_PATH, {})
    active_model = config.get("model_name", "N/A")
    has_db_key = bool(config.get("gemini_api_key"))
    has_env_key = bool(gemini_api_key)
    
    if has_db_key or has_env_key:
        key_source = "db_settings.json" if has_db_key else ".env / Env Var"
        print(f"Model Active: {active_model} | API Key: Available (loaded via {key_source})")
    else:
        print(f"Model Active: {active_model} | API Key: Not Found (Offline or Ollama fallback mode)")

    # Start the weekly log exporter background thread
    exporter_thread = threading.Thread(target=run_weekly_exporter, daemon=True)
    exporter_thread.start()

    server_address = ('', port)
    httpd = ThreadingHTTPServer(server_address, SearchAPIHandler)
    print(f"Python Backend API server running on: http://localhost:{port}")
    print("Press Ctrl+C to terminate.")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping API server...")
        httpd.server_close()
        print("Server stopped.")


if __name__ == '__main__':
    run_server(port=8000)
