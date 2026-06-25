import os
import sys
import json
import re
import time
import shutil
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', line_buffering=True)

backend_dir = os.path.dirname(os.path.abspath(__file__))
user_dir = os.path.dirname(backend_dir)
root_dir = os.path.dirname(user_dir)
sys.path.append(root_dir)

# นำเข้าโมดูลสืบค้นข้อมูลระเบียบ RAG
retriever = None
try:
    from Admin.emb import HybridRetriever
except Exception as e:
    print(f"คำเตือน: ไม่สามารถนำเข้า HybridRetriever ขณะเริ่มต้นระบบ: {e}")

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



def load_db(path, default=None):
    """โหลดข้อมูลจากไฟล์ JSON"""
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
    """บันทึกข้อมูลลงไฟล์ JSON"""
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการบันทึก JSON {path}: {e}")

def log_unanswered_query(query_str):
    """บันทึกคำถามที่ไม่พบข้อมูลใน RAG เพื่อรอการแก้ไขจากแอดมิน"""
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
    """บันทึกประวัติการรันตอบคำถามของบอท"""
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

def init_databases():
    """เตรียมฐานข้อมูลสำหรับการรันครั้งแรก"""
    default_faqs = [
        {
            "id": 1,
            "question": "แนะนำวิธีดูแลดวงตาเมื่อต้องจ้องหน้าจอคอมพิวเตอร์เป็นเวลานาน",
            "icon": "fa-eye-slash",
            "answer": "แนะนำกฎ 20-20-20:\n1. 👀 พักสายตาทุก 20 นาที\n2. 🌳 มองไกลออกไป 20 ฟุต\n3. ⏱️ พักสายตานานอย่างน้อย 20 วินาที\nปรับระดับจอห่าง 50-70 ซม. และกระพริบตาบ่อยๆ ครับ"
        },
        {
            "id": 2,
            "question": "ขั้นตอนการทำบัตรประจำตัวผู้ป่วยใหม่ต้องใช้เอกสารอะไรบ้าง?",
            "icon": "fa-id-card",
            "answer": "สามารถลงทะเบียนล่วงหน้าผ่านแอป TUH Easy App หรือยื่นบัตรประชาชนตัวจริงที่แผนกเวชระเบียน ตึกผู้ป่วยนอก ชั้น 1 ประตู 1 ครับ"
        },
        {
            "id": 3,
            "question": "ติดต่อศูนย์ไอที (งานสารสนเทศ) รพ.ธรรมศาสตร์ฯ ได้ช่องทางไหนบ้าง?",
            "icon": "fa-network-wired",
            "answer": "📞 เบอร์ภายใน: ต่อ 7120 - 7124\n✉️ อีเมล: it@tuh.ac.th\n🏢 สถานที่: อาคารกิตติวัฒนา ชั้น 4 ในวันเวลาราชการครับ"
        },
        {
            "id": 4,
            "question": "เวลาทำการของคลินิกนอกเวลาราชการคือช่วงเวลาใด?",
            "icon": "fa-clock",
            "answer": "📅 จันทร์ - ศุกร์: 16:00 - 20:00 น.\n📅 เสาร์ - อาทิตย์ และวันหยุดนักขัตฤกษ์: 08:00 - 12:00 น. ครับ"
        },
        {
            "id": 5,
            "question": "สามารถตรวจสอบสิทธิ์การรักษาพยาบาล (เช่น บัตรทอง, ประกันสังคม) ได้อย่างไร?",
            "icon": "fa-hand-holding-medical",
            "answer": "1. ตรวจสอบในแอปเป๋าตัง\n2. แอดไลน์ สปสช. @nhso\n3. ตรวจที่เครื่อง Kiosk ตึก OPD ชั้น 1 หรือโทรสายด่วน สปสช. 1330 ครับ"
        },
        {
            "id": 6,
            "question": "ขอลิงก์ดาวน์โหลดแอปพลิเคชัน TUH Easy App สำหรับจองคิวการรักษา",
            "icon": "fa-mobile-screen-button",
            "answer": "📲 ดาวน์โหลดได้ที่:\n- iOS: https://apps.apple.com/th/app/tuh-easy/id1527718210\n- Android: https://play.google.com/store/apps/details?id=th.ac.tuh.easyapp"
        }
    ]

    # บันทึกข้อมูลตั้งค่าเบื้องต้น
    if not os.path.exists(DB_SETTINGS_PATH):
        default_settings = {
            "gemini_api_key": gemini_api_key or "",
            "model_name": "gemini-2.5-flash" if gemini_api_key else "qwen2.5:3b",
            "temperature": 0.2,
            "max_tokens": 400,
            "top_k": 3,
            "system_prompt": "คุณคือ TUH Chatbot AI ปัญญาประดิษฐ์ช่วยเหลือตอบคำถามของโรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ จงตอบคำถามผู้ใช้โดยอ้างอิงข้อมูลจากบริบท (Context) ที่กำหนดให้อย่างกระชับ สั้น ตรงประเด็นที่สุด (ความยาวไม่ควรเกิน 5 บรรทัด หรือสรุปย่อเป็นข้อย่อยกระชับ) ห้ามอธิบายยืดเยื้อหรือทวนเนื้อความในบริบทซ้ำโดยไม่จำเป็น หากเรื่องใดไม่มีข้อมูลในบริบท ให้ระบุสั้นๆ อย่างสุภาพว่าไม่พบข้อมูล และต้องตอบกลับเป็นภาษาไทย ห้ามตอบคำถามจากคนที่พิมพ์คำหยาบเข้ามา เช่น กู ไอเหี้ย ไอสัตว์ มึง",
            "welcome_message": "สวัสดีครับ ยินดีต้อนรับสู่ **TUH Chatbot AI** ยินดีให้บริการครับ 😊\n\nท่านต้องการสอบถามข้อมูลด้านใด สามารถพิมพ์สอบถามหรือกดเลือกคำถามยอดนิยมด้านล่างนี้ได้เลยครับ",
            "predefined_faqs": default_faqs
        }
        save_db(DB_SETTINGS_PATH, default_settings)
    else:
        config = load_db(DB_SETTINGS_PATH, {})
        if "predefined_faqs" not in config:
            config["predefined_faqs"] = default_faqs
            save_db(DB_SETTINGS_PATH, config)

    uploads_dir = os.path.join(root_dir, "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    
    docs = load_db(DB_DOCUMENTS_PATH, [])
    default_filename = "ประกาศ มธ.สวัสดิการด้านสุขภาพ พ.ศ.2566.pdf"
    default_pdf_src = os.path.join(root_dir, default_filename)
    default_pdf_dest = os.path.join(uploads_dir, default_filename)
    
    if os.path.exists(default_pdf_src) and not os.path.exists(default_pdf_dest):
        try:
            shutil.copy2(default_pdf_src, default_pdf_dest)
            print(f"Copied default PDF document to uploads: {default_filename}")
        except Exception as e:
            print(f"Failed to copy default PDF: {e}")
            
    if not docs and os.path.exists(default_pdf_dest):
        size = os.path.getsize(default_pdf_dest)
        docs.append({
            "filename": default_filename,
            "status": "Active",
            "pages": 19,
            "upload_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "size": size,
            "exclude_pages": [12, 13, 14, 18]
        })
        save_db(DB_DOCUMENTS_PATH, docs)

def rebuild_vector_indices():
    """เธรดเบื้องหลังสั่งสร้าง Index ใหม่อัตโนมัติ"""
    print(" Rebuilding vector database indices...")
    admin_dir = os.path.join(root_dir, "Admin")
    rebuild_script = os.path.join(admin_dir, "rebuild_db.py")
    if not os.path.exists(rebuild_script):
        print(f" Script not found: {rebuild_script}")
        return
        
    try:
        import subprocess
        result = subprocess.run(["py", rebuild_script], capture_output=True, text=True)
        print("Rebuild stdout:", result.stdout)
        if result.stderr:
            print("Rebuild stderr:", result.stderr)
            
        global retriever
        try:
            from Admin.emb import HybridRetriever
            new_retriever = HybridRetriever()
            new_retriever.load()
            retriever = new_retriever
            print(" Vector database indices re-loaded in memory successfully!")
        except Exception as err:
            print(f" Failed to reload hybrid retriever in memory: {err}")
    except Exception as e:
        print(f"Error executing rebuild_db.py: {e}")

init_databases()


# --- [ ฟังก์ชันตัวช่วยการทำ RAG & AI ] ---

def clean_thai_text(text):
    text = re.sub(r'\?+', '', text)
    text = text.replace('|', ' ')
    text = re.sub(r' +', ' ', text)
    text = re.sub(r'\n+', '\n', text)
    return text.strip()

def contains_profanity(text):
    """ตรวจสอบคำหยาบในคำถามของผู้ใช้เพื่อแจ้งเตือนอย่างสุภาพ"""
    if not text:
        return False
    text_lower = text.lower()
    
    # 1. ลบข้อยกเว้นที่อาจมีคำว่า "เหี้ย" หรือ "กู" เพื่อหลีกเลี่ยง false positive
    temp_text = text_lower
    temp_text = temp_text.replace("เหี้ยม", "")  # เช่น โหดเหี้ยม
    
    exceptions_gu = ["กู้", "กูล", "กูร", "กูรู", "กูเกิ", "กู๊ด", "กูเบอร์", "กูตู", "กูเม่"]
    for exc in exceptions_gu:
        temp_text = temp_text.replace(exc, "")
        
    # 2. รายการคำหยาบหลักที่จะคัดกรอง
    rude_keywords = [
        "มึง", "เหี้ย", "ควย", "เย็ด", "สัส", "ระยำ", "อัปรีย์", "จัญไร", "ตอแหล",
        "ชิบหาย", "ฉิบหาย", "ส้นตีน", "เสือก", "ไอ้สัตว์", "ไอสัตว์", "อีสัตว์", "กู"
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
    """ทำหน้าที่ส่งคำขอดึง API เครือข่ายแบบเรียงตัวเดียวช่วยลดความยุ่งเหยิงของ urllib"""
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
    """ส่งคำถามและข้อมูล RAG ไปประมวลผลคำตอบผ่าน OpenRouter API"""
    context = ""
    if results:
        context_parts = []
        for r in results:
            source = r['metadata'].get('source', 'เอกสาร')
            page = r['metadata'].get('page', '')
            content = r['metadata']['raw_table'] if r['metadata'].get('type') == 'table' and 'raw_table' in r['metadata'] else r['content']
            context_parts.append(f"เนื้อหาหลัก (จาก {source} หน้า {page}):\n{content}")
        context = "\n---\n".join(context_parts)

    system_prompt = config.get("system_prompt", "คุณคือ TUH Chatbot AI...")
    temp = float(config.get("temperature", 0.2))
    max_tokens = int(config.get("max_tokens", 400))
    api_key = config.get("gemini_api_key") or gemini_api_key
    model_name = config.get("model_name", "deepseek/deepseek-v4-flash")

    openai_messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        role = "user" if msg.get("sender") == "user" else "assistant"
        openai_messages.append({"role": role, "content": msg.get("text", "")})
    openai_messages.append({"role": "user", "content": f"บริบทข้อมูลอ้างอิง (Context):\n{context}\n\nคำถามจากผู้ใช้: {query}"})

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
            print(f"กำลังเรียกใช้ OpenRouter ({model_name}) รอบที่ {attempt + 1}: '{query}'")
            res_data = make_http_post(url, payload, headers, timeout=15)
            choices = res_data.get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content")
                if content and content.strip() != "":
                    ans = content
                    break
            print("⚠️ ได้รับคำตอบว่างเปล่าจาก OpenRouter จะทำการเชื่อมต่อลองใหม่อีกครั้ง...")
            time.sleep(1)
        except Exception as e:
            print(f"OpenRouter API Error ในรอบที่ {attempt + 1}: {e}")
            if attempt == 1:
                ans = f"เกิดข้อผิดพลาดในการดึงคำตอบ: {e}\n\n" + get_fallback_vector_answer(results)
            time.sleep(1)

    if ans is None or ans.strip() == "":
        ans = "ไม่ได้รับคำตอบจากระบบปัญญาประดิษฐ์ (โมเดลส่งกลับข้อความว่าง)\n\n" + get_fallback_vector_answer(results)

    # ใส่เครดิตหน้าเอกสารประกอบด้านล่างคำตอบ
    if results and not ans.startswith(" **(เซิร์ฟเวอร์"):
        citations = []
        for res in results:
            source = res["metadata"].get("source", "เอกสารสวัสดิการโรงพยาบาล")
            page = res["metadata"].get("page", "")
            page_str = f" หน้า {page}" if page else ""
            citations.append(f"- {source}{page_str}")
        if citations:
            citations = list(dict.fromkeys(citations))
            ans += "\n\n---\nเอกสารอ้างอิง:\n" + "\n".join(citations)

    return ans



class SearchAPIHandler(BaseHTTPRequestHandler):
    
    def _set_headers(self, status=200):
        """ตั้งค่า Header รองรับ CORS สำหรับฝั่ง Frontend"""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-File-Name')
        self.end_headers()

    def _send_json(self, data, status=200):
        """ส่งคำตอบกลับกลับในรูปโครงสร้าง JSON"""
        self._set_headers(status)
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def _get_json_payload(self):
        """อ่านข้อมูล JSON Payload ที่หน้าบ้านยื่นคำขอมา"""
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            return {}
        post_data = self.rfile.read(content_length)
        return json.loads(post_data.decode('utf-8'))

    def do_OPTIONS(self):
        self._set_headers(200)

    def do_GET(self):
        # 1. Health Status
        if self.path == '/':
            self._send_json({"status": "online", "message": "TUH Chatbot & Admin APIs are online."})
        # 2. Stats
        elif self.path == '/api/admin/stats':
            self.handle_admin_stats()
        # 3. Feedbacks
        elif self.path == '/api/admin/feedback':
            self._send_json(load_db(DB_FEEDBACK_PATH, []))
        # 4. Unanswered Questions
        elif self.path == '/api/admin/unanswered':
            self._send_json(load_db(DB_UNANSWERED_PATH, []))
        # 5. Active Documents List
        elif self.path == '/api/admin/documents':
            self._send_json(load_db(DB_DOCUMENTS_PATH, []))
        # 6. Admin Panel settings Get
        elif self.path == '/api/admin/settings':
            self._send_json(load_db(DB_SETTINGS_PATH, {}))
        # 7. Statistics History logs
        elif self.path == '/api/admin/history':
            self._send_json(load_db(DB_HISTORY_PATH, []))
        else:
            self._send_json({"error": "Not Found"}, 404)

    def do_POST(self):
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
        # 9. Log unanswered
        elif self.path == '/api/admin/unanswered/submit':
            self.handle_unanswered_submit()
        # 10. Core search query (RAG)
        elif self.path == '/api/search':
            self.handle_search()
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

            # ตรวจสอบคำหยาบก่อนประมวลผล
            if contains_profanity(query_str):
                profanity_warning = "ขออภัยครับ กรุณาใช้คำสุภาพในการสนทนาด้วยครับ 😊"
                log_bot_response(query_str, profanity_warning, [], 0.0, "Profanity Filter")
                self._send_json({"answer": profanity_warning, "results": []})
                return

            # ค้นหาในประวัติ FAQ ตรงก่อนเพื่อตอบทันที
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
            
            # ตรวจสอบรายการเอกสารที่เปิดเป็น Active
            docs = load_db(DB_DOCUMENTS_PATH, [])
            active_docs = {d["filename"] for d in docs if d.get("status") == "Active"}
            
            # แมปชื่อคู่สัญญารองรับไฟล์ระบบเก่า
            default_pdf = "ประกาศ มธ.สวัสดิการด้านสุขภาพ พ.ศ.2566.pdf"
            if default_pdf in active_docs:
                active_docs.update(["sample_cleaned.md", "sample_cleaned.json"])
            
            results = []
            if retriever is not None:
                try:
                    # ค้นหาเผื่อเลือก 3 เท่าสำหรับทำการคัดกรองความเปิดปิด
                    raw_results = retriever.query(query_str, top_k=top_k * 3)
                    for res in raw_results:
                        source = res['metadata'].get('source', '')
                        if not source or source in active_docs:
                            results.append(res)
                        if len(results) >= top_k:
                            break
                except Exception as e:
                    print(f"Error querying retriever: {e}")
            
            answer = generate_response_ai(query_str, results, config, history)
            response_time = time.perf_counter() - start_time
            
            # บันทึกประวัติและตัวจำลอง
            model_name = config.get("model_name", "deepseek/deepseek-v4-flash")
            model_tag = f"OpenRouter ({model_name})"
            
            chunk_ids = [res['chunk_id'] for res in results if 'chunk_id' in res]
            log_bot_response(query_str, answer, chunk_ids, response_time, model_tag)

            # คัดกรองถ้าหาความรู้ไม่พ้น
            is_unanswered = len(results) == 0 or any(k in answer for k in ["ไม่พบข้อมูล", "ขออภัย", "ไม่มีข้อมูล", "ไม่สามารถตอบได้"])
            if is_unanswered:
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
            
            if username == "admin" and password == "admin1234":
                self._send_json({
                    "success": True,
                    "token": "tuh-admin-session-token-998877",
                    "username": "admin",
                    "role": "System Administrator",
                    "name": "แอดมิน สารสนเทศ"
                })
            else:
                self._send_json({"error": "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง"}, 401)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def handle_admin_stats(self):
        try:
            docs = load_db(DB_DOCUMENTS_PATH, [])
            feedback = load_db(DB_FEEDBACK_PATH, [])
            unanswered = load_db(DB_UNANSWERED_PATH, [])
            
            total_docs = len(docs)
            active_docs = sum(1 for d in docs if d.get("status") == "Active")
            likes = sum(1 for f in feedback if f.get("rating") == "like")
            dislikes = sum(1 for f in feedback if f.get("rating") == "dislike")
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
                "recent_comments": comments[-5:]
            })
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def handle_feedback_submit(self):
        try:
            data = self._get_json_payload()
            rating = data.get("rating", "")
            comment = data.get("comment", "")
            query = data.get("query", "")
            msg_id = data.get("msgId", "")
            
            feedback = load_db(DB_FEEDBACK_PATH, [])
            updated = False
            for fb in feedback:
                if fb.get("msgId") == msg_id and msg_id:
                    if rating: fb["rating"] = rating
                    if comment: fb["comment"] = comment
                    fb["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    updated = True
                    break
                    
            if not updated:
                feedback.append({
                    "id": f"fb-{int(time.time() * 1000)}",
                    "msgId": msg_id,
                    "rating": rating,
                    "comment": comment,
                    "query": query,
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

    def handle_documents_upload(self):
        try:
            content_length = int(self.headers['Content-Length'])
            from urllib.parse import unquote
            filename = unquote(self.headers.get('X-File-Name', 'uploaded_document.pdf'))
            post_data = self.rfile.read(content_length)
            
            uploads_dir = os.path.join(root_dir, "uploads")
            os.makedirs(uploads_dir, exist_ok=True)
            
            filepath = os.path.join(uploads_dir, filename)
            with open(filepath, "wb") as f:
                f.write(post_data)
                
            print(f"Uploaded and wrote PDF document file: {filepath}")
            
            docs = load_db(DB_DOCUMENTS_PATH, [])
            exists = False
            for d in docs:
                if d.get("filename") == filename:
                    d["status"] = "Processing"
                    d["upload_date"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    d["size"] = len(post_data)
                    exists = True
                    break
            if not exists:
                docs.append({
                    "filename": filename,
                    "status": "Processing",
                    "pages": 0,
                    "upload_date": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "size": len(post_data),
                    "exclude_pages": []
                })
            save_db(DB_DOCUMENTS_PATH, docs)
            
            import threading
            def run_processing():
                try:
                    pages_count = 1
                    try:
                        import fitz
                        doc = fitz.open(filepath)
                        pages_count = len(doc)
                        doc.close()
                    except Exception:
                        pass
                        
                    current_docs = load_db(DB_DOCUMENTS_PATH, [])
                    for cd in current_docs:
                        if cd.get("filename") == filename:
                            cd["pages"] = pages_count
                    save_db(DB_DOCUMENTS_PATH, current_docs)
                    
                    rebuild_vector_indices()
                    
                    current_docs = load_db(DB_DOCUMENTS_PATH, [])
                    for cd in current_docs:
                        if cd.get("filename") == filename:
                            cd["status"] = "Active"
                    save_db(DB_DOCUMENTS_PATH, current_docs)
                except Exception as err:
                    print(f"Error in bg processing for {filename}: {err}")
                    current_docs = load_db(DB_DOCUMENTS_PATH, [])
                    for cd in current_docs:
                        if cd.get("filename") == filename:
                            cd["status"] = "Error"
                    save_db(DB_DOCUMENTS_PATH, current_docs)
                    
            threading.Thread(target=run_processing).start()
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
            config.update(data)
            save_db(DB_SETTINGS_PATH, config)
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
