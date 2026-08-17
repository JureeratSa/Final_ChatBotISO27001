import os
import sys
import json
import time
import re

# Add backend directory to path
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user", "backend")
sys.path.append(backend_dir)

try:
    import pymysql
except ImportError:
    print("❌ Error: pymysql is not installed. Running 'pip install pymysql'...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "pymysql"])
    import pymysql

# Import config from server.py directly
try:
    from server import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, DB_DIR
    from server import DB_SETTINGS_PATH, DB_FEEDBACK_PATH, DB_UNANSWERED_PATH, DB_DOCUMENTS_PATH, DB_HISTORY_PATH, DB_FORMS_PATH, DB_ANNOUNCEMENTS_PATH, DB_ADMIN_PATH
except ImportError as e:
    print(f"❌ Error importing server config: {e}")
    sys.exit(1)

print("==================================================================")
print("🚀 TUH Chatbot Data Migration to TiDB Cloud (Relational Constraints)")
print("==================================================================")
print(f"Target DB Host: {DB_HOST}")
print(f"Target DB Name: {DB_NAME}")
print(f"Target DB User: {DB_USER}")
print("==================================================================")

try:
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        charset="utf8mb4"
    )
    cursor = conn.cursor()
    
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}`")
    cursor.execute(f"USE `{DB_NAME}`")
    
    print(f"✅ Successfully connected and verified database '{DB_NAME}' on TiDB Cloud!")
except Exception as e:
    print(f"❌ Database Connection Failed: {e}")
    sys.exit(1)

# List of JSON paths we want to load
paths_to_load = [
    DB_SETTINGS_PATH,
    DB_ADMIN_PATH,
    DB_DOCUMENTS_PATH,
    DB_HISTORY_PATH,
    DB_FEEDBACK_PATH,
    DB_UNANSWERED_PATH,
    DB_FORMS_PATH,
    DB_ANNOUNCEMENTS_PATH
]

data_store = {}
for p in paths_to_load:
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                data_store[p] = json.load(f)
        except Exception as e:
            print(f"⚠️ Warning: Could not read {os.path.basename(p)}: {e}")
            data_store[p] = []
    else:
        data_store[p] = []

# --- Drop Old Tables (in correct dependency order to prevent FK errors) ---
print("\n🧹 Dropping old tables in dependency order...")
tables_to_drop = [
    "history_documents",
    "feedback",
    "unanswered",
    "forms",
    "announcements",
    "documents",
    "history",
    "settings",
    "admin"
]
for tbl in tables_to_drop:
    try:
        cursor.execute(f"DROP TABLE IF EXISTS {tbl}")
        print(f"   Dropped table '{tbl}' (if existed)")
    except Exception as e:
        print(f"   ⚠️ Could not drop '{tbl}': {e}")

# --- 1. Re-create Tables (Independent Tables first) ---
print("\n🛠️ Creating database tables with Foreign Key constraints...")

try:
    # A. Settings
    cursor.execute("""
    CREATE TABLE settings (
        id VARCHAR(50) PRIMARY KEY,
        model_name VARCHAR(100),
        temperature FLOAT,
        max_tokens INT,
        top_k INT,
        embedding_tech VARCHAR(50),
        system_prompt TEXT,
        welcome_message TEXT,
        chat_greeting TEXT,
        custom_faqs LONGTEXT,
        predefined_faqs LONGTEXT,
        last_build_duration FLOAT
    )
    """)
    print("   ✅ Table 'settings' created.")

    # B. Admin
    cursor.execute("""
    CREATE TABLE admin (
        id VARCHAR(50) PRIMARY KEY,
        username VARCHAR(100),
        password_salt VARCHAR(100),
        password_hash VARCHAR(150),
        role VARCHAR(100),
        name VARCHAR(100)
    )
    """)
    print("   ✅ Table 'admin' created.")

    # C. Documents (Referenced by history_documents)
    cursor.execute("""
    CREATE TABLE documents (
        filename VARCHAR(255) PRIMARY KEY,
        upload_date DATETIME,
        status VARCHAR(50),
        pages INT,
        size INT,
        exclude_pages TEXT,
        display_name VARCHAR(255),
        chunking_duration FLOAT,
        embedding_duration FLOAT
    )
    """)
    print("   ✅ Table 'documents' created.")

    # D. History (Referenced by feedback & history_documents)
    cursor.execute("""
    CREATE TABLE history (
        id VARCHAR(255) PRIMARY KEY,
        date DATETIME,
        query TEXT,
        answer TEXT,
        response_time FLOAT,
        chunk TEXT,
        api_model VARCHAR(255)
    )
    """)
    print("   ✅ Table 'history' created.")

    # E. Feedback (References history)
    cursor.execute("""
    CREATE TABLE feedback (
        id VARCHAR(255) PRIMARY KEY,
        rating VARCHAR(50),
        comment TEXT,
        query TEXT,
        answer TEXT,
        date DATETIME,
        history_id VARCHAR(255),
        CONSTRAINT fk_feedback_history FOREIGN KEY (history_id) 
            REFERENCES history(id) ON DELETE SET NULL
    )
    """)
    print("   ✅ Table 'feedback' created with FOREIGN KEY to 'history'.")

    # F. Unanswered
    cursor.execute("""
    CREATE TABLE unanswered (
        id VARCHAR(255) PRIMARY KEY,
        query TEXT,
        count INT,
        date DATETIME,
        status VARCHAR(50)
    )
    """)
    print("   ✅ Table 'unanswered' created.")

    # G. Forms
    cursor.execute("""
    CREATE TABLE forms (
        id VARCHAR(255) PRIMARY KEY,
        name VARCHAR(255),
        filename VARCHAR(255),
        page VARCHAR(50),
        download_link VARCHAR(255)
    )
    """)
    print("   ✅ Table 'forms' created.")

    # H. Announcements
    cursor.execute("""
    CREATE TABLE announcements (
        id VARCHAR(255) PRIMARY KEY,
        title VARCHAR(255),
        content TEXT,
        start_date VARCHAR(100),
        end_date VARCHAR(100),
        pinned TINYINT(1)
    )
    """)
    print("   ✅ Table 'announcements' created.")

    # I. History Documents (Junction Table for Many-to-Many relationship)
    cursor.execute("""
    CREATE TABLE history_documents (
        history_id VARCHAR(255),
        document_filename VARCHAR(255),
        PRIMARY KEY (history_id, document_filename),
        CONSTRAINT fk_hd_history FOREIGN KEY (history_id) 
            REFERENCES history(id) ON DELETE CASCADE,
        CONSTRAINT fk_hd_document FOREIGN KEY (document_filename) 
            REFERENCES documents(filename) ON DELETE CASCADE
    )
    """)
    print("   ✅ Junction Table 'history_documents' created with Many-to-Many FOREIGN KEYS.")

except Exception as e:
    print(f"❌ Table creation failed: {e}")
    sys.exit(1)

# --- 2. Populate Data in order of dependency ---
print("\n📥 Populating relational datasets...")

try:
    # A. Settings
    settings_data = data_store[DB_SETTINGS_PATH]
    if settings_data:
        sql = """
        INSERT INTO settings (id, model_name, temperature, max_tokens, top_k, embedding_tech, system_prompt, welcome_message, chat_greeting, custom_faqs, predefined_faqs, last_build_duration)
        VALUES ('config', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (
            settings_data.get("model_name"),
            settings_data.get("temperature"),
            settings_data.get("max_tokens"),
            settings_data.get("top_k"),
            settings_data.get("embedding_tech"),
            settings_data.get("system_prompt"),
            settings_data.get("welcome_message"),
            settings_data.get("chat_greeting"),
            json.dumps(settings_data.get("custom_faqs", []), ensure_ascii=False),
            json.dumps(settings_data.get("predefined_faqs", []), ensure_ascii=False),
            settings_data.get("last_build_duration")
        ))
        print("   🎉 Populated 'settings'")

    # B. Admin
    admin_data = data_store[DB_ADMIN_PATH]
    if admin_data:
        sql = """
        INSERT INTO admin (id, username, password_salt, password_hash, role, name)
        VALUES ('config', %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (
            admin_data.get("username"),
            admin_data.get("password_salt"),
            admin_data.get("password_hash"),
            admin_data.get("role"),
            admin_data.get("name")
        ))
        print("   🎉 Populated 'admin'")

    # C. Documents
    docs_data = data_store[DB_DOCUMENTS_PATH]
    doc_filenames = set()
    if docs_data:
        insert_docs = []
        for item in docs_data:
            exclude_str = ", ".join(map(str, item.get("exclude_pages", [])))
            filename = item.get("filename")
            doc_filenames.add(filename)
            insert_docs.append((
                filename,
                item.get("upload_date"),
                item.get("status"),
                item.get("pages"),
                item.get("size"),
                exclude_str,
                item.get("display_name"),
                item.get("chunking_duration"),
                item.get("embedding_duration")
            ))
        sql = "INSERT INTO documents (filename, upload_date, status, pages, size, exclude_pages, display_name, chunking_duration, embedding_duration) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
        cursor.executemany(sql, insert_docs)
        print(f"   🎉 Populated {len(insert_docs)} rows in 'documents'")

    # D. History
    history_data = data_store[DB_HISTORY_PATH]
    history_map = {} # Map query -> history_id for feedback linking
    if history_data:
        insert_history = []
        for idx, item in enumerate(history_data):
            item_id = item.get("id") or f"history-{idx}-{int(time.time() * 1000)}"
            chunk_val = ", ".join(map(str, item.get("chunk_ids", [])))
            query = item.get("query", "").strip()
            if query:
                # Keep track of the latest history ID for this query to map feedback
                history_map[query.lower()] = item_id
            
            insert_history.append((
                str(item_id),
                item.get("timestamp"),
                item.get("query"),
                item.get("answer"),
                item.get("response_time"),
                chunk_val,
                item.get("model")
            ))
        sql = "INSERT INTO history (id, date, query, answer, response_time, chunk, api_model) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        cursor.executemany(sql, insert_history)
        print(f"   🎉 Populated {len(insert_history)} rows in 'history'")

        # D2. Parse and populate Junction table history_documents based on answer contents
        insert_junctions = []
        for item in history_data:
            item_id = item.get("id")
            answer = item.get("answer") or ""
            # Find references to .pdf files inside the answer
            referenced_pdfs = re.findall(r'([\w\s\.-]+\.pdf)', answer)
            for pdf in referenced_pdfs:
                pdf_name = pdf.strip()
                # Check if this document exists in our doc filenames list
                if pdf_name in doc_filenames:
                    insert_junctions.append((item_id, pdf_name))
        
        # De-duplicate junctions
        insert_junctions = list(set(insert_junctions))
        if insert_junctions:
            sql = "INSERT INTO history_documents (history_id, document_filename) VALUES (%s, %s)"
            cursor.executemany(sql, insert_junctions)
            print(f"   🎉 Linked {len(insert_junctions)} rows in junction 'history_documents'")

    # E. Feedback
    feedback_data = data_store[DB_FEEDBACK_PATH]
    if feedback_data:
        insert_fb = []
        for idx, item in enumerate(feedback_data):
            item_id = item.get("msgId") or f"fb-{idx}-{int(time.time() * 1000)}"
            query = (item.get("query") or "").strip().lower()
            
            # Smart Lookup: Find the matching history_id by checking if the query matches
            history_id = history_map.get(query)
            
            insert_fb.append((
                str(item.get("id") or f"fb-id-{idx}"),
                item.get("rating"),
                item.get("comment"),
                item.get("query"),
                item.get("answer"),
                item.get("timestamp"),
                history_id # foreign key linked here!
            ))
        sql = "INSERT INTO feedback (id, rating, comment, query, answer, date, history_id) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        cursor.executemany(sql, insert_fb)
        print(f"   🎉 Populated {len(insert_fb)} rows in 'feedback' (linked matches to history)")

    # F. Unanswered
    unanswered_data = data_store[DB_UNANSWERED_PATH]
    if unanswered_data:
        insert_unans = []
        for idx, item in enumerate(unanswered_data):
            insert_unans.append((
                str(item.get("id")),
                item.get("query"),
                item.get("count"),
                item.get("timestamp"),
                item.get("status")
            ))
        sql = "INSERT INTO unanswered (id, query, count, date, status) VALUES (%s, %s, %s, %s, %s)"
        cursor.executemany(sql, insert_unans)
        print(f"   🎉 Populated {len(insert_unans)} rows in 'unanswered'")

    # G. Forms
    forms_data = data_store[DB_FORMS_PATH]
    if forms_data:
        insert_forms = []
        for idx, item in enumerate(forms_data):
            insert_forms.append((
                str(item.get("id")),
                item.get("name"),
                item.get("filename"),
                str(item.get("page") or ""),
                item.get("download_link")
            ))
        sql = "INSERT INTO forms (id, name, filename, page, download_link) VALUES (%s, %s, %s, %s, %s)"
        cursor.executemany(sql, insert_forms)
        print(f"   🎉 Populated {len(insert_forms)} rows in 'forms'")

    # H. Announcements
    ann_data = data_store[DB_ANNOUNCEMENTS_PATH]
    if ann_data:
        insert_ann = []
        for idx, item in enumerate(ann_data):
            insert_ann.append((
                str(item.get("id")),
                item.get("title"),
                item.get("content"),
                item.get("start_date"),
                item.get("end_date"),
                1 if item.get("pinned") else 0
            ))
        sql = "INSERT INTO announcements (id, title, content, start_date, end_date, pinned) VALUES (%s, %s, %s, %s, %s, %s)"
        cursor.executemany(sql, insert_ann)
        print(f"   🎉 Populated {len(insert_ann)} rows in 'announcements'")

    conn.commit()

except Exception as e:
    print(f"❌ Failed to populate data: {e}")
    conn.rollback()
    sys.exit(1)

cursor.close()
conn.close()
print("\n==================================================================")
print("🏆 All database tables converted and linked with Foreign Keys successfully!")
print("==================================================================")
