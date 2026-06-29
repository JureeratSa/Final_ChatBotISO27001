import os
import sys
import json
import re
import time
import shutil
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

# 犧吭ｸｳ犹犧もｹ霞ｸｲ犹もｸ｡犧扉ｸｹ犧･犧ｪ犧ｷ犧壟ｸ�ｹ霞ｸ吭ｸもｹ霞ｸｭ犧｡犧ｹ犧･犧｣犧ｰ犹犧壟ｸｵ犧｢犧� RAG
retriever = None
try:
    from Admin.emb import HybridRetriever
except Exception as e:
    print(f"犧�ｸｳ犹犧歩ｸｷ犧ｭ犧�: 犹�ｸ｡犹謂ｸｪ犧ｲ犧｡犧ｲ犧｣犧籾ｸ吭ｸｳ犹犧もｹ霞ｸｲ HybridRetriever 犧もｸ内ｸｰ犹犧｣犧ｴ犹謂ｸ｡犧歩ｹ霞ｸ吭ｸ｣犧ｰ犧壟ｸ�: {e}")

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
    """犹もｸｫ犧･犧扉ｸもｹ霞ｸｭ犧｡犧ｹ犧･犧謂ｸｲ犧≒ｹ�ｸ游ｸ･犹� JSON"""
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
    """犧壟ｸｱ犧吭ｸ伶ｸｶ犧≒ｸもｹ霞ｸｭ犧｡犧ｹ犧･犧･犧�ｹ�ｸ游ｸ･犹� JSON"""
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"犹犧≒ｸｴ犧扉ｸもｹ霞ｸｭ犧憫ｸｴ犧扉ｸ樅ｸ･犧ｲ犧扉ｹ�ｸ吭ｸ≒ｸｲ犧｣犧壟ｸｱ犧吭ｸ伶ｸｶ犧� JSON {path}: {e}")

def log_unanswered_query(query_str):
    """犧壟ｸｱ犧吭ｸ伶ｸｶ犧≒ｸ�ｸｳ犧籾ｸｲ犧｡犧伶ｸｵ犹謂ｹ�ｸ｡犹謂ｸ樅ｸ壟ｸもｹ霞ｸｭ犧｡犧ｹ犧･犹�ｸ� RAG 犹犧樅ｸｷ犹謂ｸｭ犧｣犧ｭ犧≒ｸｲ犧｣犹≒ｸ≒ｹ霞ｹ�ｸもｸ謂ｸｲ犧≒ｹ≒ｸｭ犧扉ｸ｡犧ｴ犧�"""
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
    """犧壟ｸｱ犧吭ｸ伶ｸｶ犧≒ｸ巵ｸ｣犧ｰ犧ｧ犧ｱ犧歩ｸｴ犧≒ｸｲ犧｣犧｣犧ｱ犧吭ｸ歩ｸｭ犧壟ｸ�ｸｳ犧籾ｸｲ犧｡犧もｸｭ犧�ｸ壟ｸｭ犧�"""
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
    """犹犧杳ｹ霞ｸｲ犧歩ｸ｣犧ｧ犧謂ｹ犧癌ｹ�ｸ�ｹ犧樅ｸｷ犹謂ｸｭ犧ｪ犹謂ｸ�ｸｭ犧ｭ犧≒ｹ�ｸ游ｸ･犹呉ｸ巵ｸ｣犧ｰ犧ｧ犧ｱ犧歩ｸｴ犧≒ｸｲ犧｣犧歩ｸｭ犧壟ｸ｣犧ｲ犧｢犧ｪ犧ｱ犧巵ｸ扉ｸｲ犧ｫ犹呉ｸ歩ｸｱ犧扉ｸ｣犧ｭ犧壟ｸｧ犧ｱ犧吭ｸｭ犧ｲ犧伶ｸｴ犧歩ｸ｢犹呉ｸｭ犧ｱ犧歩ｹもｸ吭ｸ｡犧ｱ犧歩ｸｴ"""
    export_dir = r"Z:\Intern\2026\犧｡犧ｧ犧･\test_log"
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
                        # 犧�ｸｳ犧吭ｸｧ犧内ｸｧ犧ｱ犧吭ｸ謂ｸｱ犧吭ｸ伶ｸ｣犹呉ｸ伶ｸｵ犹謂ｹ犧巵ｹ�ｸ吭ｸｧ犧ｱ犧吭ｹ犧｣犧ｴ犹謂ｸ｡犧歩ｹ霞ｸ吭ｸもｸｭ犧�ｸｪ犧ｱ犧巵ｸ扉ｸｲ犧ｫ犹呉ｸ吭ｸｵ犹�
                        item_week_start = ts_dt - datetime.timedelta(days=ts_dt.weekday())
                        item_week_start = item_week_start.replace(hour=0, minute=0, second=0, microsecond=0)
                        
                        if item_week_start not in weeks_data:
                            weeks_data[item_week_start] = []
                        weeks_data[item_week_start].append(item)
                    except Exception:
                        continue
                
                # 犧歩ｸ｣犧ｧ犧謂ｹ犧癌ｹ�ｸ�ｹ≒ｸ歩ｹ謂ｸ･犧ｰ犧ｪ犧ｱ犧巵ｸ扉ｸｲ犧ｫ犹呉ｸ伶ｸｵ犹謂ｸ歩ｸｱ犧扉ｸ｣犧ｭ犧壟ｹ≒ｸ･犹霞ｸｧ (犧ｧ犧ｱ犧吭ｸｭ犧ｲ犧伶ｸｴ犧歩ｸ｢犹呉ｸもｸｭ犧�ｸｪ犧ｱ犧巵ｸ扉ｸｲ犧ｫ犹呉ｸ吭ｸｱ犹霞ｸ吭ｸ憫ｹ謂ｸｲ犧吭ｹ�ｸ巵ｹ≒ｸ･犹霞ｸｧ)
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
                                    "犹犧ｧ犧･犧ｲ犧伶ｸｵ犹謂ｸ歩ｸｭ犧� (Timestamp)", 
                                    "犧�ｸｳ犧籾ｸｲ犧｡犧謂ｸｲ犧≒ｸ憫ｸｹ犹霞ｹ�ｸ癌ｹ� (User Query)", 
                                    "犧�ｸｳ犧歩ｸｭ犧壟ｸ伶ｸｵ犹謂ｸ壟ｸｭ犧伶ｸ歩ｸｭ犧� (Bot Response)", 
                                    "犹もｸ｡犹犧扉ｸ･ AI (AI Model)", 
                                    "犹犧ｧ犧･犧ｲ犧歩ｸｭ犧壟ｸｪ犧吭ｸｭ犧� (Response Time sec)", 
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
        
        # 犧ｫ犧･犧ｱ犧� 1 犧癌ｸｱ犹謂ｸｧ犹もｸ｡犧�ｸ≒ｹ謂ｸｭ犧吭ｸ歩ｸ｣犧ｧ犧謂ｹ犧癌ｹ�ｸ�ｸ｣犧ｭ犧壟ｸ籾ｸｱ犧扉ｹ�ｸ�
        time.sleep(3600)


def init_databases():
    """犹犧歩ｸ｣犧ｵ犧｢犧｡犧説ｸｲ犧吭ｸもｹ霞ｸｭ犧｡犧ｹ犧･犧ｪ犧ｳ犧ｫ犧｣犧ｱ犧壟ｸ≒ｸｲ犧｣犧｣犧ｱ犧吭ｸ�ｸ｣犧ｱ犹霞ｸ�ｹ≒ｸ｣犧�"""
    default_faqs = [
        {
            "id": 1,
            "question": "犹≒ｸ吭ｸｰ犧吭ｸｳ犧ｧ犧ｴ犧倨ｸｵ犧扉ｸｹ犹≒ｸ･犧扉ｸｧ犧�ｸ歩ｸｲ犹犧｡犧ｷ犹謂ｸｭ犧歩ｹ霞ｸｭ犧�ｸ謂ｹ霞ｸｭ犧�ｸｫ犧吭ｹ霞ｸｲ犧謂ｸｭ犧�ｸｭ犧｡犧樅ｸｴ犧ｧ犹犧歩ｸｭ犧｣犹呉ｹ犧巵ｹ�ｸ吭ｹ犧ｧ犧･犧ｲ犧吭ｸｲ犧�",
            "icon": "fa-eye-slash",
            "answer": "犹≒ｸ吭ｸｰ犧吭ｸｳ犧≒ｸ� 20-20-20:\n1. �操 犧樅ｸｱ犧≒ｸｪ犧ｲ犧｢犧歩ｸｲ犧伶ｸｸ犧� 20 犧吭ｸｲ犧伶ｸｵ\n2. �元 犧｡犧ｭ犧�ｹ�ｸ≒ｸ･犧ｭ犧ｭ犧≒ｹ�ｸ� 20 犧游ｸｸ犧表n3. 竢ｱ�� 犧樅ｸｱ犧≒ｸｪ犧ｲ犧｢犧歩ｸｲ犧吭ｸｲ犧吭ｸｭ犧｢犹謂ｸｲ犧�ｸ吭ｹ霞ｸｭ犧｢ 20 犧ｧ犧ｴ犧吭ｸｲ犧伶ｸｵ\n犧巵ｸ｣犧ｱ犧壟ｸ｣犧ｰ犧扉ｸｱ犧壟ｸ謂ｸｭ犧ｫ犹謂ｸｲ犧� 50-70 犧金ｸ｡. 犹≒ｸ･犧ｰ犧≒ｸ｣犧ｰ犧樅ｸ｣犧ｴ犧壟ｸ歩ｸｲ犧壟ｹ謂ｸｭ犧｢犹� 犧�ｸ｣犧ｱ犧�"
        },
        {
            "id": 2,
            "question": "犧もｸｱ犹霞ｸ吭ｸ歩ｸｭ犧吭ｸ≒ｸｲ犧｣犧伶ｸｳ犧壟ｸｱ犧歩ｸ｣犧巵ｸ｣犧ｰ犧謂ｸｳ犧歩ｸｱ犧ｧ犧憫ｸｹ犹霞ｸ巵ｹ謂ｸｧ犧｢犹�ｸｫ犧｡犹謂ｸ歩ｹ霞ｸｭ犧�ｹ�ｸ癌ｹ霞ｹ犧ｭ犧≒ｸｪ犧ｲ犧｣犧ｭ犧ｰ犹�ｸ｣犧壟ｹ霞ｸｲ犧�?",
            "question": "犧もｸｱ犹霞ｸ吭ｸ歩ｸｭ犧吭ｸ≒ｸｲ犧｣犧伶ｸｳ犧壟ｸｱ犧歩ｸ｣犧巵ｸ｣犧ｰ犧謂ｸｳ犧歩ｸｱ犧ｧ犧憫ｸｹ犹霞ｸ巵ｹ謂ｸｧ犧｢犹ｸｫ犧｡犹謂ｸ歩ｹ霞ｸｭ犧ｹｸ癌ｹ霞ｹ€犧ｭ犧≒ｸｪ犧ｲ犧｣犧ｭ犧ｰ犹ｸ｣犧壟ｹ霞ｸｲ犧?",
            "icon": "fa-id-card",
            "answer": "犧ｪ犧ｲ犧｡犧ｲ犧｣犧籾ｸ･犧ｸ伶ｸｰ犹€犧壟ｸｵ犧｢犧吭ｸ･犹謂ｸｧ犧ｸｫ犧吭ｹ霞ｸｲ犧憫ｹ謂ｸｲ犧吭ｹ≒ｸｭ犧 TUH Easy App 犧ｫ犧｣犧ｷ犧ｭ犧｢犧ｷ犹謂ｸ吭ｸ壟ｸｱ犧歩ｸ｣犧巵ｸ｣犧ｰ犧癌ｸｲ犧癌ｸ吭ｸ歩ｸｱ犧ｧ犧謂ｸ｣犧ｴ犧ｸ伶ｸｵ犹謂ｹ≒ｸ憫ｸ吭ｸ≒ｹ€犧ｧ犧癌ｸ｣犧ｰ犹€犧壟ｸｵ犧｢犧 犧歩ｸｶ犧≒ｸ憫ｸｹ犹霞ｸ巵ｹ謂ｸｧ犧｢犧吭ｸｭ犧 犧癌ｸｱ犹霞ｸ 1 犧巵ｸ｣犧ｰ犧歩ｸｹ 1 犧ｸ｣犧ｱ犧"
        },
        {
            "id": 3,
            "question": "犧歩ｸｴ犧扉ｸ歩ｹ謂ｸｭ犧ｨ犧ｹ犧吭ｸ｢犹呉ｹｸｭ犧伶ｸｵ (犧ｸｲ犧吭ｸｪ犧ｲ犧｣犧ｪ犧吭ｹ€犧伶ｸｨ) 犧｣犧.犧倨ｸ｣犧｣犧｡犧ｨ犧ｲ犧ｪ犧歩ｸ｣犹呉ｸｯ 犹ｸ扉ｹ霞ｸ癌ｹ謂ｸｭ犧ｸ伶ｸｲ犧ｹｸｫ犧吭ｸ壟ｹ霞ｸｲ犧?",
            "icon": "fa-network-wired",
            "answer": "到 犹€犧壟ｸｭ犧｣犹呉ｸ犧ｲ犧｢犹ｸ: 犧歩ｹ謂ｸｭ 7120 - 7124\n笨会ｸ 犧ｭ犧ｵ犹€犧｡犧･: it@tuh.ac.th\n召 犧ｪ犧籾ｸｲ犧吭ｸ伶ｸｵ犹: 犧ｭ犧ｲ犧ｸｲ犧｣犧≒ｸｴ犧歩ｸ歩ｸｴ犧ｧ犧ｱ犧亭ｸ吭ｸｲ 犧癌ｸｱ犹霞ｸ 4 犹ｸ吭ｸｧ犧ｱ犧吭ｹ€犧ｧ犧･犧ｲ犧｣犧ｲ犧癌ｸ≒ｸｲ犧｣犧ｸ｣犧ｱ犧"
        },
        {
            "id": 4,
            "question": "犹€犧ｧ犧･犧ｲ犧伶ｸｳ犧≒ｸｲ犧｣犧もｸｭ犧ｸｸ･犧ｴ犧吭ｸｴ犧≒ｸ吭ｸｭ犧≒ｹ€犧ｧ犧･犧ｲ犧｣犧ｲ犧癌ｸ≒ｸｲ犧｣犧ｸｷ犧ｭ犧癌ｹ謂ｸｧ犧ｹ€犧ｧ犧･犧ｲ犹ｸ?",
            "icon": "fa-clock",
            "answer": "�套 犧謂ｸｱ犧吭ｸ伶ｸ｣犹� - 犧ｨ犧ｸ犧≒ｸ｣犹�: 16:00 - 20:00 犧�.\n�套 犹犧ｪ犧ｲ犧｣犹� - 犧ｭ犧ｲ犧伶ｸｴ犧歩ｸ｢犹� 犹≒ｸ･犧ｰ犧ｧ犧ｱ犧吭ｸｫ犧｢犧ｸ犧扉ｸ吭ｸｱ犧≒ｸもｸｱ犧歩ｸ､犧≒ｸｩ犹�: 08:00 - 12:00 犧�. 犧�ｸ｣犧ｱ犧�"
        },
        {
            "id": 5,
            "question": "犧ｪ犧ｲ犧｡犧ｲ犧｣犧籾ｸ歩ｸ｣犧ｧ犧謂ｸｪ犧ｭ犧壟ｸｪ犧ｴ犧伶ｸ倨ｸｴ犹呉ｸ≒ｸｲ犧｣犧｣犧ｱ犧≒ｸｩ犧ｲ犧樅ｸ｢犧ｲ犧壟ｸｲ犧･ (犹犧癌ｹ謂ｸ� 犧壟ｸｱ犧歩ｸ｣犧伶ｸｭ犧�, 犧巵ｸ｣犧ｰ犧≒ｸｱ犧吭ｸｪ犧ｱ犧�ｸ�ｸ｡) 犹�ｸ扉ｹ霞ｸｭ犧｢犹謂ｸｲ犧�ｹ�ｸ｣?",
            "icon": "fa-hand-holding-medical",
            "answer": "1. 犧歩ｸ｣犧ｧ犧謂ｸｪ犧ｭ犧壟ｹ�ｸ吭ｹ≒ｸｭ犧巵ｹ犧巵ｹ金ｸｲ犧歩ｸｱ犧Ⅸn2. 犹≒ｸｭ犧扉ｹ�ｸ･犧吭ｹ� 犧ｪ犧巵ｸｪ犧�. @nhso\n3. 犧歩ｸ｣犧ｧ犧謂ｸ伶ｸｵ犹謂ｹ犧�ｸ｣犧ｷ犹謂ｸｭ犧� Kiosk 犧歩ｸｶ犧� OPD 犧癌ｸｱ犹霞ｸ� 1 犧ｫ犧｣犧ｷ犧ｭ犹もｸ伶ｸ｣犧ｪ犧ｲ犧｢犧扉ｹ謂ｸｧ犧� 犧ｪ犧巵ｸｪ犧�. 1330 犧�ｸ｣犧ｱ犧�"
        },
        {
            "id": 6,
            "question": "犧もｸｭ犧･犧ｴ犧�ｸ≒ｹ呉ｸ扉ｸｲ犧ｧ犧吭ｹ呉ｹもｸｫ犧･犧扉ｹ≒ｸｭ犧巵ｸ樅ｸ･犧ｴ犹犧�ｸ癌ｸｱ犧� TUH Easy App 犧ｪ犧ｳ犧ｫ犧｣犧ｱ犧壟ｸ謂ｸｭ犧�ｸ�ｸｴ犧ｧ犧≒ｸｲ犧｣犧｣犧ｱ犧≒ｸｩ犧ｲ",
            "icon": "fa-mobile-screen-button",
            "answer": "�憧 犧扉ｸｲ犧ｧ犧吭ｹ呉ｹもｸｫ犧･犧扉ｹ�ｸ扉ｹ霞ｸ伶ｸｵ犹�:\n- iOS: https://apps.apple.com/th/app/tuh-easy/id1527718210\n- Android: https://play.google.com/store/apps/details?id=th.ac.tuh.easyapp"
        }
    ]

    # 犧壟ｸｱ犧吭ｸ伶ｸｶ犧≒ｸもｹ霞ｸｭ犧｡犧ｹ犧･犧歩ｸｱ犹霞ｸ�ｸ�ｹ謂ｸｲ犹犧壟ｸｷ犹霞ｸｭ犧�ｸ歩ｹ霞ｸ�
    if not os.path.exists(DB_SETTINGS_PATH):
        default_settings = {
            "gemini_api_key": gemini_api_key or "",
            "model_name": "gemini-2.5-flash" if gemini_api_key else "qwen2.5:3b",
            "temperature": 0.2,
            "max_tokens": 1000,
            "top_k": 3,
            "system_prompt": "คุณคือ TUH Chatbot AI ผู้ช่วยที่รอบรู้และพร้อมช่วยเหลือตอบคำถามของโรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ ยินดีให้บริการตอบคำถามทางการพยาบาล สวัสดิการและข้อมูลต่างๆ อย่างสุภาพที่สุด (ความยาวไม่เกิน 3-4 บรรทัด หรือสรุปกระชับที่สุด) ห้ามกล่าวอ้างว่าข้อมูลมาจากที่ใด หรืออ้างอิงถึงคำว่า 'ข้อมูลที่กำหนดให้', 'เอกสาร', 'แหล่งข้อมูล' ใดๆ เด็ดขาด ตอบเป็นภาษาไทยอย่างเป็นธรรมชาติและสุภาพที่สุดเสมอ หากไม่มีข้อมูลให้ตอบผู้ใช้อย่างสุภาพว่าไม่มีข้อมูลในระบบ",
            "welcome_message": "สวัสดีครับ ยินดีต้อนรับสู่ **TUH Chatbot AI** ยินดีให้บริการครับ\n\nหากต้องการสอบถามข้อมูลสวัสดิการ สามารถพิมพ์คำถามได้เลยครับ"
        }
        save_db(DB_SETTINGS_PATH, default_settings)

    if not os.path.exists(DB_DOCUMENTS_PATH):
        docs = []
        default_filename = "ประกาศ มธ.สวัสดิการด้านสุขภาพ พ.ศ.2566.pdf"
        size = 0
        try:
            if os.path.exists(os.path.join(base_dir, default_filename)):
                size = os.path.getsize(os.path.join(base_dir, default_filename))
        except Exception:
            pass
        docs.append({
            "filename": default_filename,
            "status": "Active",
            "pages": 18,
            "upload_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "size": size,
            "exclude_pages": []
        })
        save_db(DB_DOCUMENTS_PATH, docs)

def rebuild_vector_indices():
    """犹犧倨ｸ｣犧扉ｹ犧壟ｸｷ犹霞ｸｭ犧�ｸｫ犧･犧ｱ犧�ｸｪ犧ｱ犹謂ｸ�ｸｪ犧｣犹霞ｸｲ犧� Index 犹�ｸｫ犧｡犹謂ｸｭ犧ｱ犧歩ｹもｸ吭ｸ｡犧ｱ犧歩ｸｴ"""
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


# --- [ 犧游ｸｱ犧�ｸ≒ｹ呉ｸ癌ｸｱ犧吭ｸ歩ｸｱ犧ｧ犧癌ｹ謂ｸｧ犧｢犧≒ｸｲ犧｣犧伶ｸｳ RAG & AI ] ---

def clean_thai_text(text):
    text = re.sub(r'\?+', '', text)
    text = text.replace('|', ' ')
    text = re.sub(r' +', ' ', text)
    text = re.sub(r'\n+', '\n', text)
    return text.strip()

def contains_profanity(text):
    """犧歩ｸ｣犧ｧ犧謂ｸｪ犧ｭ犧壟ｸ�ｸｳ犧ｫ犧｢犧ｲ犧壟ｹ�ｸ吭ｸ�ｸｳ犧籾ｸｲ犧｡犧もｸｭ犧�ｸ憫ｸｹ犹霞ｹ�ｸ癌ｹ霞ｹ犧樅ｸｷ犹謂ｸｭ犹≒ｸ謂ｹ霞ｸ�ｹ犧歩ｸｷ犧ｭ犧吭ｸｭ犧｢犹謂ｸｲ犧�ｸｪ犧ｸ犧�犧ｲ犧�"""
    if not text:
        return False
    text_lower = text.lower()
    
    # 1. 犧･犧壟ｸもｹ霞ｸｭ犧｢犧≒ｹ犧ｧ犹霞ｸ吭ｸ伶ｸｵ犹謂ｸｭ犧ｲ犧謂ｸ｡犧ｵ犧�ｸｳ犧ｧ犹謂ｸｲ "犹犧ｫ犧ｵ犹霞ｸ｢" 犧ｫ犧｣犧ｷ犧ｭ "犧≒ｸｹ" 犹犧樅ｸｷ犹謂ｸｭ犧ｫ犧･犧ｵ犧≒ｹ犧･犧ｵ犹謂ｸ｢犧� false positive
    temp_text = text_lower
    temp_text = temp_text.replace("犹犧ｫ犧ｵ犹霞ｸ｢犧｡", "")  # 犹犧癌ｹ謂ｸ� 犹もｸｫ犧扉ｹ犧ｫ犧ｵ犹霞ｸ｢犧｡
    
    exceptions_gu = ["犧≒ｸｹ犹�", "犧≒ｸｹ犧･", "犧≒ｸｹ犧｣", "犧≒ｸｹ犧｣犧ｹ", "犧≒ｸｹ犹犧≒ｸｴ", "犧≒ｸｹ犹癌ｸ�", "犧≒ｸｹ犹犧壟ｸｭ犧｣犹�", "犧≒ｸｹ犧歩ｸｹ", "犧≒ｸｹ犹犧｡犹�"]
    for exc in exceptions_gu:
        temp_text = temp_text.replace(exc, "")
        
    # 2. 犧｣犧ｲ犧｢犧≒ｸｲ犧｣犧�ｸｳ犧ｫ犧｢犧ｲ犧壟ｸｫ犧･犧ｱ犧≒ｸ伶ｸｵ犹謂ｸ謂ｸｰ犧�ｸｱ犧扉ｸ≒ｸ｣犧ｭ犧�
    rude_keywords = [
        "犧｡犧ｶ犧�", "犹犧ｫ犧ｵ犹霞ｸ｢", "犧�ｸｧ犧｢", "犹犧｢犹�ｸ�", "犧ｪ犧ｱ犧ｪ", "犧｣犧ｰ犧｢犧ｳ", "犧ｭ犧ｱ犧巵ｸ｣犧ｵ犧｢犹�", "犧謂ｸｱ犧財ｹ�ｸ｣", "犧歩ｸｭ犹≒ｸｫ犧･",
        "犧癌ｸｴ犧壟ｸｫ犧ｲ犧｢", "犧霞ｸｴ犧壟ｸｫ犧ｲ犧｢", "犧ｪ犹霞ｸ吭ｸ歩ｸｵ犧�", "犹犧ｪ犧ｷ犧ｭ犧�", "犹�ｸｭ犹霞ｸｪ犧ｱ犧歩ｸｧ犹�", "犹�ｸｭ犧ｪ犧ｱ犧歩ｸｧ犹�", "犧ｭ犧ｵ犧ｪ犧ｱ犧歩ｸｧ犹�", "犧≒ｸｹ"
    ]
    
    for word in rude_keywords:
        if word in temp_text:
            return True
            
    return False

def get_fallback_vector_answer(results):
    """犧�ｸｳ犧ｪ犧ｱ犹謂ｸ�ｸ扉ｸｶ犧�ｹ犧吭ｸｷ犹霞ｸｭ犧ｫ犧ｲ犧ｭ犹霞ｸｲ犧�ｸｭ犧ｴ犧�ｸ歩ｸ｣犧�ｸもｸｶ犹霞ｸ吭ｸ歩ｸｭ犧� 犧≒ｸ｣犧内ｸｵ犧｣犧ｰ犧壟ｸ� AI 犧ｭ犧ｭ犧游ｹ�ｸ･犧吭ｹ呉ｸｫ犧｣犧ｷ犧ｭ犧ｭ犧ｴ犧吭ｹ犧伶ｸｭ犧｣犹呉ｹ犧吭ｹ�ｸ歩ｸ･犹謂ｸ｡"""
    if results:
        top_res = results[0]
        top_content = top_res['metadata']['raw_table'] if top_res['metadata'].get('type') == 'table' and 'raw_table' in top_res['metadata'] else top_res['content']
        source = top_res['metadata'].get('source', '犹犧ｭ犧≒ｸｪ犧ｲ犧｣')
        page = top_res['metadata'].get('page', '')
        page_str = f" 犧ｫ犧吭ｹ霞ｸｲ {page}" if page else ""
        
        ans = (
            f" **(犹犧金ｸｴ犧｣犹呉ｸ游ｹ犧ｧ犧ｭ犧｣犹� AI 犧ｭ犧ｭ犧游ｹ�ｸ･犧吭ｹ� - 犹≒ｸｪ犧扉ｸ�ｸもｹ霞ｸｭ犧�ｸｧ犧ｲ犧｡犧ｭ犹霞ｸｲ犧�ｸｭ犧ｴ犧�ｸ伶ｸｵ犹謂ｸ｡犧ｵ犧�ｸｧ犧ｲ犧｡犹�ｸ≒ｸ･犹霞ｹ犧�ｸｵ犧｢犧�ｸ伶ｸｵ犹謂ｸｪ犧ｸ犧�)**\n\n"
            f"�塘 **犹犧ｭ犧≒ｸｪ犧ｲ犧｣犧ｭ犹霞ｸｲ犧�ｸｭ犧ｴ犧�ｸｫ犧･犧ｱ犧� ({source}{page_str}):**\n{top_content}"
        )
        
        other_pages = []
        for res in results[1:3]:
            other_page = res['metadata'].get('page')
            if other_page and other_page not in other_pages and other_page != page:
                other_pages.append(f"犧ｫ犧吭ｹ霞ｸｲ {other_page}")
        if other_pages:
            ans += f"\n\n�庁 *犧�ｸｸ犧内ｸｪ犧ｲ犧｡犧ｲ犧｣犧籾ｸｪ犧ｷ犧壟ｸ�ｹ霞ｸ吭ｸｫ犧ｱ犧ｧ犧もｹ霞ｸｭ犧伶ｸｵ犹謂ｹ犧≒ｸｵ犹謂ｸ｢犧ｧ犧もｹ霞ｸｭ犧�ｹ犧樅ｸｴ犹謂ｸ｡犹犧歩ｸｴ犧｡犹�ｸ扉ｹ霞ｸ伶ｸｵ犹�: {', '.join(other_pages)}*"
    else:
        ans = (
            "犧ｪ犧ｧ犧ｱ犧ｪ犧扉ｸｵ犧�ｸ｣犧ｱ犧� 犧憫ｸ｡犹犧巵ｹ�ｸ吭ｸ｣犧ｰ犧壟ｸ壟ｸ巵ｸｱ犧財ｸ財ｸｲ犧巵ｸ｣犧ｰ犧扉ｸｴ犧ｩ犧説ｹ呉ｹ�ｸｫ犹霞ｸもｹ霞ｸｭ犧｡犧ｹ犧･犹犧壟ｸｷ犹霞ｸｭ犧�ｸ歩ｹ霞ｸ吭ｸもｸｭ犧�ｹもｸ｣犧�ｸ樅ｸ｢犧ｲ犧壟ｸｲ犧･犧倨ｸ｣犧｣犧｡犧ｨ犧ｲ犧ｪ犧歩ｸ｣犹呉ｹ犧霞ｸ･犧ｴ犧｡犧樅ｸ｣犧ｰ犹犧≒ｸｵ犧｢犧｣犧歩ｸｴ "
            "犧もｸ内ｸｰ犧吭ｸｵ犹霞ｸ｣犧ｰ犧壟ｸ壟ｸ�ｹ霞ｸ吭ｸｫ犧ｲ犧ｭ犧ｭ犧游ｹ�ｸ･犧吭ｹ� 犧ｫ犧｣犧ｷ犧ｭ犹�ｸ｡犹謂ｸ樅ｸ壟ｸもｹ霞ｸｭ犧｡犧ｹ犧･犹犧ｧ犧≒ｹ犧歩ｸｭ犧｣犹呉ｸ伶ｸｵ犹謂ｹ犧≒ｸｵ犹謂ｸ｢犧ｧ犧もｹ霞ｸｭ犧�ｸ≒ｸｱ犧壟ｸ�ｸｳ犧籾ｸｲ犧｡犧もｸｭ犧�ｸ�ｸｸ犧内ｸ�ｸ｣犧ｱ犧�"
        )
    return ans

def make_http_post(url, payload, headers=None, timeout=15):
    """犧伶ｸｳ犧ｫ犧吭ｹ霞ｸｲ犧伶ｸｵ犹謂ｸｪ犹謂ｸ�ｸ�ｸｳ犧もｸｭ犧扉ｸｶ犧� API 犹犧�ｸ｣犧ｷ犧ｭ犧もｹ謂ｸｲ犧｢犹≒ｸ壟ｸ壟ｹ犧｣犧ｵ犧｢犧�ｸ歩ｸｱ犧ｧ犹犧扉ｸｵ犧｢犧ｧ犧癌ｹ謂ｸｧ犧｢犧･犧扉ｸ�ｸｧ犧ｲ犧｡犧｢犧ｸ犹謂ｸ�ｹ犧ｫ犧｢犧ｴ犧�ｸもｸｭ犧� urllib"""
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
    """犧ｪ犹謂ｸ�ｸ�ｸｳ犧籾ｸｲ犧｡犹≒ｸ･犧ｰ犧もｹ霞ｸｭ犧｡犧ｹ犧･ RAG 犹�ｸ巵ｸ巵ｸ｣犧ｰ犧｡犧ｧ犧･犧憫ｸ･犧�ｸｳ犧歩ｸｭ犧壟ｸ憫ｹ謂ｸｲ犧� OpenRouter API"""
    context = ""
    if results:
        context_parts = []
        for r in results:
            source = r['metadata'].get('source', '犹犧ｭ犧≒ｸｪ犧ｲ犧｣')
            page = r['metadata'].get('page', '')
            content = r['metadata']['raw_table'] if r['metadata'].get('type') == 'table' and 'raw_table' in r['metadata'] else r['content']
            context_parts.append(f"犹犧吭ｸｷ犹霞ｸｭ犧ｫ犧ｲ犧ｫ犧･犧ｱ犧� (犧謂ｸｲ犧� {source} 犧ｫ犧吭ｹ霞ｸｲ {page}):\n{content}")
        context = "\n---\n".join(context_parts)

    system_prompt = config.get("system_prompt", "犧�ｸｸ犧内ｸ�ｸｷ犧ｭ TUH Chatbot AI 犧巵ｸｱ犧財ｸ財ｸｲ犧巵ｸ｣犧ｰ犧扉ｸｴ犧ｩ犧説ｹ呉ｸ癌ｹ謂ｸｧ犧｢犹犧ｫ犧･犧ｷ犧ｭ犧歩ｸｭ犧壟ｸ�ｸｳ犧籾ｸｲ犧｡犧もｸｭ犧�ｹもｸ｣犧�ｸ樅ｸ｢犧ｲ犧壟ｸｲ犧･犧倨ｸ｣犧｣犧｡犧ｨ犧ｲ犧ｪ犧歩ｸ｣犹呉ｹ犧霞ｸ･犧ｴ犧｡犧樅ｸ｣犧ｰ犹犧≒ｸｵ犧｢犧｣犧歩ｸｴ 犧謂ｸ�ｸ歩ｸｭ犧壟ｸ�ｸｳ犧籾ｸｲ犧｡犧憫ｸｹ犹霞ｹ�ｸ癌ｹ霞ｹもｸ扉ｸ｢犧ｭ犹霞ｸｲ犧�ｸｭ犧ｴ犧�ｸ謂ｸｲ犧≒ｸもｹ霞ｸｭ犧｡犧ｹ犧･犧伶ｸｵ犹謂ｸ≒ｸｳ犧ｫ犧吭ｸ扉ｹ�ｸｫ犹霞ｸｭ犧｢犹謂ｸｲ犧�ｹ犧巵ｹ�ｸ吭ｸ倨ｸ｣犧｣犧｡犧癌ｸｲ犧歩ｸｴ犹≒ｸ･犧ｰ犧歩ｸ｣犧�ｸ巵ｸ｣犧ｰ犹犧扉ｹ�ｸ吭ｸ伶ｸｵ犹謂ｸｪ犧ｸ犧� (犧�ｸｧ犧ｲ犧｡犧｢犧ｲ犧ｧ犹�ｸ｡犹謂ｹ犧≒ｸｴ犧� 3-4 犧壟ｸ｣犧｣犧伶ｸｱ犧� 犧ｫ犧｣犧ｷ犧ｭ犧ｪ犧｣犧ｸ犧巵ｹ犧巵ｹ�ｸ吭ｸもｹ霞ｸｭ犧ｪ犧ｱ犹霞ｸ吭ｹ�) 犧ｫ犹霞ｸｲ犧｡犧樅ｸｹ犧扉ｸｫ犧｣犧ｷ犧ｭ犧ｭ犹霞ｸｲ犧�ｸｭ犧ｴ犧�ｸ籾ｸｶ犧�ｸ�ｸｳ犧ｧ犹謂ｸｲ '犧謂ｸｲ犧≒ｸ壟ｸ｣犧ｴ犧壟ｸ伶ｸ伶ｸｵ犹謂ｸ≒ｸｳ犧ｫ犧吭ｸ扉ｹ�ｸｫ犹�', '犧謂ｸｲ犧≒ｹ犧ｭ犧≒ｸｪ犧ｲ犧｣犧伶ｸｵ犹謂ｹ≒ｸ吭ｸ壟ｹ�ｸｧ犹�', '犧謂ｸｲ犧≒ｹ�ｸ游ｸ･犹�' 犧ｫ犧｣犧ｷ犧ｭ犧�ｸｳ犧ｭ犧ｷ犹謂ｸ吭ｹ�ｸ扉ｸ伶ｸｵ犹謂ｸｪ犧ｷ犹謂ｸｭ犧籾ｸｶ犧�ｹ≒ｸｫ犧･犹謂ｸ�ｸもｹ霞ｸｭ犧｡犧ｹ犧･犧ｫ犧｣犧ｷ犧ｭ犹犧壟ｸｷ犹霞ｸｭ犧�ｸｫ犧･犧ｱ犧�ｸ≒ｸｲ犧｣犧巵ｹ霞ｸｭ犧吭ｸもｹ霞ｸｭ犧｡犧ｹ犧･犹もｸ扉ｸ｢犹犧扉ｹ�ｸ扉ｸもｸｲ犧� 犹�ｸｫ犹霞ｸ歩ｸｭ犧壟ｹ犧ｪ犧｡犧ｷ犧ｭ犧吭ｸｧ犹謂ｸｲ犧�ｸｸ犧内ｸ｡犧ｵ犧�ｸｧ犧ｲ犧｡犧｣犧ｹ犹霞ｹ犧｣犧ｷ犹謂ｸｭ犧�ｸ吭ｸｱ犹霞ｸ吭ｸｭ犧｢犧ｹ犹謂ｹ≒ｸ･犹霞ｸｧ犹もｸ扉ｸ｢犧歩ｸ｣犧� 犧ｫ犧ｲ犧≒ｹ�ｸ｡犹謂ｸ樅ｸ壟ｸもｹ霞ｸｭ犧｡犧ｹ犧･ 犹�ｸｫ犹霞ｹ≒ｸ謂ｹ霞ｸ�ｸ憫ｸｹ犹霞ｹ�ｸ癌ｹ霞ｸｭ犧｢犹謂ｸｲ犧�ｸｪ犧ｸ犧�犧ｲ犧樅ｸｧ犹謂ｸｲ犹�ｸ｡犹謂ｸ樅ｸ壟ｸもｹ霞ｸｭ犧｡犧ｹ犧･ 犹≒ｸ･犧ｰ犧歩ｹ霞ｸｭ犧�ｸ歩ｸｭ犧壟ｸ≒ｸ･犧ｱ犧壟ｹ犧巵ｹ�ｸ吭ｸ�犧ｲ犧ｩ犧ｲ犹�ｸ伶ｸ｢ 犧ｫ犹霞ｸｲ犧｡犧歩ｸｭ犧壟ｸ�ｸｳ犧籾ｸｲ犧｡犧謂ｸｲ犧≒ｸ�ｸ吭ｸ伶ｸｵ犹謂ｸ樅ｸｴ犧｡犧樅ｹ呉ｸ�ｸｳ犧ｫ犧｢犧ｲ犧壟ｹ犧もｹ霞ｸｲ犧｡犧ｲ 犹犧癌ｹ謂ｸ� 犧≒ｸｹ 犹�ｸｭ犹霞ｹ犧ｫ犧ｵ犹霞ｸ｢ 犹�ｸｭ犹霞ｸｪ犧ｱ犧歩ｸｧ犹� 犧｡犧ｶ犧�")
    temp = float(config.get("temperature", 0.2))
    max_tokens = int(config.get("max_tokens", 1000))
    api_key = config.get("gemini_api_key") or gemini_api_key
    model_name = config.get("model_name", "deepseek/deepseek-v4-flash")

    openai_messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        role = "user" if msg.get("sender") == "user" else "assistant"
        openai_messages.append({"role": role, "content": msg.get("text", "")})
    openai_messages.append({"role": "user", "content": f"犧壟ｸ｣犧ｴ犧壟ｸ伶ｸもｹ霞ｸｭ犧｡犧ｹ犧･犧ｭ犹霞ｸｲ犧�ｸｭ犧ｴ犧� (Context):\n{context}\n\n犧�ｸｳ犧籾ｸｲ犧｡犧謂ｸｲ犧≒ｸ憫ｸｹ犹霞ｹ�ｸ癌ｹ�: {query}"})

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
            print(f"犧≒ｸｳ犧･犧ｱ犧�ｹ犧｣犧ｵ犧｢犧≒ｹ�ｸ癌ｹ� OpenRouter ({model_name}) 犧｣犧ｭ犧壟ｸ伶ｸｵ犹� {attempt + 1}: '{query}'")
            res_data = make_http_post(url, payload, headers, timeout=15)
            choices = res_data.get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content")
                if content and content.strip() != "":
                    ans = content
                    break
            print("笞��� 犹�ｸ扉ｹ霞ｸ｣犧ｱ犧壟ｸ�ｸｳ犧歩ｸｭ犧壟ｸｧ犹謂ｸｲ犧�ｹ犧巵ｸ･犹謂ｸｲ犧謂ｸｲ犧� OpenRouter 犧謂ｸｰ犧伶ｸｳ犧≒ｸｲ犧｣犹犧癌ｸｷ犹謂ｸｭ犧｡犧歩ｹ謂ｸｭ犧･犧ｭ犧�ｹ�ｸｫ犧｡犹謂ｸｭ犧ｵ犧≒ｸ�ｸ｣犧ｱ犹霞ｸ�...")
            time.sleep(1)
        except Exception as e:
            print(f"OpenRouter API Error 犹�ｸ吭ｸ｣犧ｭ犧壟ｸ伶ｸｵ犹� {attempt + 1}: {e}")
            if attempt == 1:
                ans = f"犹犧≒ｸｴ犧扉ｸもｹ霞ｸｭ犧憫ｸｴ犧扉ｸ樅ｸ･犧ｲ犧扉ｹ�ｸ吭ｸ≒ｸｲ犧｣犧扉ｸｶ犧�ｸ�ｸｳ犧歩ｸｭ犧�: {e}\n\n" + get_fallback_vector_answer(results)
            time.sleep(1)

    if ans is None or ans.strip() == "":
        ans = "ไม่ได้รับคำตอบจากระบบปัญญาประดิษฐ์ (โมเดลส่งกลับข้อความว่าง)\n\n" + get_fallback_vector_answer(results)

    # ตรวจสอบประวัติว่ามีการใช้คำไม่สุภาพหรือไม่ เพื่อย้อนกลับคำเตือน
    has_profanity_in_history = any(contains_profanity(msg.get("text", "")) for msg in history if msg.get("sender") == "user")
    is_profanity_warning = has_profanity_in_history or (ans and any(k in ans for k in ["คำไม่สุภาพ", "ไม่สุภาพ", "คำสุภาพ", "กรุณาใช้คำสุภาพ"]))

    # แสดงรายการเอกสารประกอบท้ายคำตอบ
    if results and not ans.startswith(" **(เซิร์ฟเวอร์ AI ออฟไลน์") and not is_profanity_warning:
        citations = []
        for res in results:
            source = res["metadata"].get("source", "เอกสารอ้างอิง")
            page = res["metadata"].get("page", "")
            page_str = f" หน้า {page}" if page else ""
            citations.append(f"- {source}{page_str}")
        if citations:
            citations = list(dict.fromkeys(citations))
            ans += "\n\n---\nเอกสารอ้างอิง:\n" + "\n".join(citations)

    return ans



class SearchAPIHandler(BaseHTTPRequestHandler):
    
    def _set_headers(self, status=200):
        """犧歩ｸｱ犹霞ｸ�ｸ�ｹ謂ｸｲ Header 犧｣犧ｭ犧�ｸ｣犧ｱ犧� CORS 犧ｪ犧ｳ犧ｫ犧｣犧ｱ犧壟ｸ杳ｸｱ犹謂ｸ� Frontend"""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-File-Name, X-Exclude-Pages')
        self.end_headers()

    def _send_json(self, data, status=200):
        """犧ｪ犹謂ｸ�ｸ�ｸｳ犧歩ｸｭ犧壟ｸ≒ｸ･犧ｱ犧壟ｸ≒ｸ･犧ｱ犧壟ｹ�ｸ吭ｸ｣犧ｹ犧巵ｹもｸ�ｸ｣犧�ｸｪ犧｣犹霞ｸｲ犧� JSON"""
        self._set_headers(status)
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def _get_json_payload(self):
        """犧ｭ犹謂ｸｲ犧吭ｸもｹ霞ｸｭ犧｡犧ｹ犧･ JSON Payload 犧伶ｸｵ犹謂ｸｫ犧吭ｹ霞ｸｲ犧壟ｹ霞ｸｲ犧吭ｸ｢犧ｷ犹謂ｸ吭ｸ�ｸｳ犧もｸｭ犧｡犧ｲ"""
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            return {}
        post_data = self.rfile.read(content_length)
        return json.loads(post_data.decode('utf-8'))

    def do_OPTIONS(self):
        self._set_headers(200)

    def do_GET(self):
        from urllib.parse import urlparse, parse_qs, unquote
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query = parse_qs(parsed_url.query)

        # 1. Health Status
        if path == '/':
            self._send_json({"status": "online", "message": "TUH Chatbot & Admin APIs are online."})
        # 2. Stats
        elif path == '/api/admin/stats':
            self.handle_admin_stats()
        # 3. Feedbacks
        elif path == '/api/admin/feedback':
            self._send_json(load_db(DB_FEEDBACK_PATH, []))
        # 4. Unanswered Questions
        elif path == '/api/admin/unanswered':
            self._send_json(load_db(DB_UNANSWERED_PATH, []))
        # 5. Active Documents List
        elif path == '/api/admin/documents':
            self._send_json(load_db(DB_DOCUMENTS_PATH, []))
        # 6. Admin Panel settings Get
        elif path == '/api/admin/settings':
            self._send_json(load_db(DB_SETTINGS_PATH, {}))
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

            # 犧歩ｸ｣犧ｧ犧謂ｸｪ犧ｭ犧壟ｸ�ｸｳ犧ｫ犧｢犧ｲ犧壟ｸ≒ｹ謂ｸｭ犧吭ｸ巵ｸ｣犧ｰ犧｡犧ｧ犧･犧憫ｸ･
            if contains_profanity(query_str):
                profanity_warning = "犧もｸｭ犧ｭ犧�犧ｱ犧｢犧�ｸ｣犧ｱ犧� 犧≒ｸ｣犧ｸ犧内ｸｲ犹�ｸ癌ｹ霞ｸ�ｸｳ犧ｪ犧ｸ犧�犧ｲ犧樅ｹ�ｸ吭ｸ≒ｸｲ犧｣犧ｪ犧吭ｸ伶ｸ吭ｸｲ犧扉ｹ霞ｸｧ犧｢犧�ｸ｣犧ｱ犧� ��"
                log_bot_response(query_str, profanity_warning, [], 0.0, "Profanity Filter")
                self._send_json({"answer": profanity_warning, "results": []})
                return

            # 犧�ｹ霞ｸ吭ｸｫ犧ｲ犹�ｸ吭ｸ巵ｸ｣犧ｰ犧ｧ犧ｱ犧歩ｸｴ FAQ 犧歩ｸ｣犧�ｸ≒ｹ謂ｸｭ犧吭ｹ犧樅ｸｷ犹謂ｸｭ犧歩ｸｭ犧壟ｸ伶ｸｱ犧吭ｸ伶ｸｵ
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
            
            # 犧歩ｸ｣犧ｧ犧謂ｸｪ犧ｭ犧壟ｸ｣犧ｲ犧｢犧≒ｸｲ犧｣犹犧ｭ犧≒ｸｪ犧ｲ犧｣犧伶ｸｵ犹謂ｹ犧巵ｸｴ犧扉ｹ犧巵ｹ�ｸ� Active
            docs = load_db(DB_DOCUMENTS_PATH, [])
            active_docs = {d["filename"] for d in docs if d.get("status") == "Active"}
            
            # 犹≒ｸ｡犧巵ｸ癌ｸｷ犹謂ｸｭ犧�ｸｹ犹謂ｸｪ犧ｱ犧財ｸ財ｸｲ犧｣犧ｭ犧�ｸ｣犧ｱ犧壟ｹ�ｸ游ｸ･犹呉ｸ｣犧ｰ犧壟ｸ壟ｹ犧≒ｹ謂ｸｲ
            default_pdf = "犧巵ｸ｣犧ｰ犧≒ｸｲ犧ｨ 犧｡犧�.犧ｪ犧ｧ犧ｱ犧ｪ犧扉ｸｴ犧≒ｸｲ犧｣犧扉ｹ霞ｸｲ犧吭ｸｪ犧ｸ犧もｸ�犧ｲ犧� 犧�.犧ｨ.2566.pdf"
            if default_pdf in active_docs:
                active_docs.update(["sample_cleaned.md", "sample_cleaned.json"])
            
            results = []
            if retriever is not None:
                try:
                    # 犧�ｹ霞ｸ吭ｸｫ犧ｲ犹犧憫ｸｷ犹謂ｸｭ犹犧･犧ｷ犧ｭ犧� 3 犹犧伶ｹ謂ｸｲ犧ｪ犧ｳ犧ｫ犧｣犧ｱ犧壟ｸ伶ｸｳ犧≒ｸｲ犧｣犧�ｸｱ犧扉ｸ≒ｸ｣犧ｭ犧�ｸ�ｸｧ犧ｲ犧｡犹犧巵ｸｴ犧扉ｸ巵ｸｴ犧�
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
            
            # 犧壟ｸｱ犧吭ｸ伶ｸｶ犧≒ｸ巵ｸ｣犧ｰ犧ｧ犧ｱ犧歩ｸｴ犹≒ｸ･犧ｰ犧歩ｸｱ犧ｧ犧謂ｸｳ犧･犧ｭ犧�
            model_name = config.get("model_name", "deepseek/deepseek-v4-flash")
            model_tag = f"OpenRouter ({model_name})"
            
            # 犹犧癌ｹ�ｸ�ｸｧ犹謂ｸｲ犧�ｸｳ犧歩ｸｭ犧壟ｹ犧巵ｹ�ｸ吭ｸ�ｸｳ犹犧歩ｸｷ犧ｭ犧吭ｸ�ｸｳ犧ｫ犧｢犧ｲ犧壟ｸｫ犧｣犧ｷ犧ｭ犹�ｸ｡犹� 犹犧樅ｸｷ犹謂ｸｭ犹犧�ｸ･犧ｵ犧｢犧｣犹呉ｸ憫ｸ･犧･犧ｱ犧樅ｸ倨ｹ呉ｹ≒ｸ･犧ｰ犧巵ｹ霞ｸｭ犧�ｸ≒ｸｱ犧吭ｸ≒ｸｲ犧｣犧扉ｸｶ犧�ｹ犧ｭ犧≒ｸｪ犧ｲ犧｣犧ｭ犹霞ｸｲ犧�ｸｭ犧ｴ犧�
            has_profanity_in_history = any(contains_profanity(msg.get("text", "")) for msg in history if msg.get("sender") == "user")
            is_profanity_warning = has_profanity_in_history or any(k in answer for k in ["犧�ｸｳ犧ｫ犧｢犧ｲ犧�", "犹�ｸ｡犹謂ｸｪ犧ｸ犧�犧ｲ犧�", "犧�ｸｳ犧ｪ犧ｸ犧�犧ｲ犧�", "犹�ｸ癌ｹ霞ｸ�ｸｳ犧ｪ犧ｸ犧�犧ｲ犧�"])
            
            if is_profanity_warning:
                results = []
                
            chunk_ids = [res['chunk_id'] for res in results if 'chunk_id' in res]
            log_bot_response(query_str, answer, chunk_ids, response_time, model_tag)

            # 犧�ｸｱ犧扉ｸ≒ｸ｣犧ｭ犧�ｸ籾ｹ霞ｸｲ犧ｫ犧ｲ犧�ｸｧ犧ｲ犧｡犧｣犧ｹ犹霞ｹ�ｸ｡犹謂ｸ樅ｹ霞ｸ�
            is_unanswered = len(results) == 0 or any(k in answer for k in ["犹�ｸ｡犹謂ｸ樅ｸ壟ｸもｹ霞ｸｭ犧｡犧ｹ犧･", "犧もｸｭ犧ｭ犧�犧ｱ犧｢", "犹�ｸ｡犹謂ｸ｡犧ｵ犧もｹ霞ｸｭ犧｡犧ｹ犧･", "犹�ｸ｡犹謂ｸｪ犧ｲ犧｡犧ｲ犧｣犧籾ｸ歩ｸｭ犧壟ｹ�ｸ扉ｹ�"])
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
            
            if username == "admin" and password == "admin1234":
                self._send_json({
                    "success": True,
                    "token": "tuh-admin-session-token-998877",
                    "username": "admin",
                    "role": "System Administrator",
                    "name": "犹≒ｸｭ犧扉ｸ｡犧ｴ犧� 犧ｪ犧ｲ犧｣犧ｪ犧吭ｹ犧伶ｸｨ"
                })
            else:
                self._send_json({"error": "犧癌ｸｷ犹謂ｸｭ犧憫ｸｹ犹霞ｹ�ｸ癌ｹ霞ｸｫ犧｣犧ｷ犧ｭ犧｣犧ｫ犧ｱ犧ｪ犧憫ｹ謂ｸｲ犧吭ｹ�ｸ｡犹謂ｸ籾ｸｹ犧≒ｸ歩ｹ霞ｸｭ犧�"}, 401)
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
                "recent_comments": comments[-5:],
                "last_build_duration": config.get("last_build_duration")
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
            from urllib.parse import unquote
            filename = unquote(self.headers.get('X-File-Name', 'uploaded_document.pdf'))
            post_data = self.rfile.read(content_length)
            
            # 犧扉ｸｶ犧�ｸもｹ霞ｸｭ犧｡犧ｹ犧･犧ｫ犧吭ｹ霞ｸｲ犧伶ｸｵ犹謂ｸ歩ｹ霞ｸｭ犧�ｸ≒ｸｲ犧｣犧･犧ｰ犹犧ｧ犹霞ｸ吭ｸ謂ｸｲ犧� header
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
            
            # 犧ｪ犧≒ｸｱ犧扉ｸ�ｸｳ犧扉ｸｴ犧壟ｹ≒ｸ壟ｸ壟ｸ伶ｸｵ犧･犧ｰ犧ｫ犧吭ｹ霞ｸｲ (Step 1)
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
