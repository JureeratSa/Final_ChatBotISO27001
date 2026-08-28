import os
import shutil
import subprocess
import sys
import time
import threading

# Reconfigure stdout/stderr to use UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Paths
base_dir = os.path.dirname(os.path.abspath(__file__))
src_admin = os.path.join(base_dir, "AdminWeb")
dest_admin = r"C:\Users\ITS\tuh-admin-web"
log_file_path = os.path.join(base_dir, "admin_web_dev_server.log")

print("Initializing Local Admin Dev Mirror on C: drive...")
print(f"Source: {src_admin}")
print(f"Destination: {dest_admin}")

# Create destination directory if it doesn't exist
os.makedirs(dest_admin, exist_ok=True)

# Files to copy at root of admin
root_files = [
    "package.json",
    "vite.config.js",
    "tailwind.config.js",
    "postcss.config.js",
    "index.html"
]

def safe_copy(src_file, dest_file):
    dest_dir = os.path.dirname(dest_file)
    temp_file = os.path.join(dest_dir, f".{os.path.basename(dest_file)}.tmp")
    try:
        shutil.copy2(src_file, temp_file)
        os.replace(temp_file, dest_file)
    except Exception as e:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception:
                pass
        raise e

def sync_root_files():
    for filename in root_files:
        src_file = os.path.join(src_admin, filename)
        dest_file = os.path.join(dest_admin, filename)
        try:
            if os.path.exists(src_file):
                if not os.path.exists(dest_file) or os.path.getmtime(src_file) > os.path.getmtime(dest_file):
                    safe_copy(src_file, dest_file)
        except Exception as e:
            print(f"\n[Sync Warning] Failed to copy {filename}: {e}")

def sync_src_directory():
    src_src = os.path.join(src_admin, "src")
    dest_src = os.path.join(dest_admin, "src")
    if not os.path.exists(src_src):
        return

    for root, dirs, files in os.walk(src_src):
        rel_path = os.path.relpath(root, src_src)
        if rel_path == ".":
            target_dir = dest_src
        else:
            target_dir = os.path.join(dest_src, rel_path)

        os.makedirs(target_dir, exist_ok=True)

        for file in files:
            if file.startswith('.') or file.startswith('~') or '.tmp' in file:
                continue

            src_file = os.path.join(root, file)
            dest_file = os.path.join(target_dir, file)
            try:
                if not os.path.exists(dest_file) or os.path.getmtime(src_file) > os.path.getmtime(dest_file):
                    safe_copy(src_file, dest_file)
                    print(f"Synced Admin: {os.path.join('src', rel_path if rel_path != '.' else '', file)}")
            except Exception as e:
                print(f"\n[Sync Warning] Failed to copy {file}: {e}")

# Initial Sync
sync_root_files()
sync_src_directory()

# Run npm install on C: if node_modules doesn't exist
dest_node_modules = os.path.join(dest_admin, "node_modules")
if not os.path.exists(dest_node_modules):
    print("Installing packages on C: drive for Admin...")
    subprocess.run("npm install", cwd=dest_admin, shell=True)

print("Starting Vite dev server on C: drive for Admin (port 5174)...")
dev_process = subprocess.Popen(
    "npm run dev -- --force --port 5174",
    cwd=dest_admin,
    shell=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
    encoding="utf-8"
)

log_file = open(log_file_path, "w", encoding="utf-8")

def log_output(line):
    sys.stdout.write(line)
    sys.stdout.flush()
    log_file.write(line)
    log_file.flush()

print("Syncing active. Press Ctrl+C to stop.")
try:
    def log_reader():
        for line in iter(dev_process.stdout.readline, ""):
            log_output(line)

    reader_thread = threading.Thread(target=log_reader, daemon=True)
    reader_thread.start()

    while dev_process.poll() is None:
        time.sleep(0.5)
        try:
            sync_root_files()
            sync_src_directory()
        except Exception as e:
            print(f"\n[Sync Warning] Watch loop error: {e}. Retrying in next loop...")

    print(f"Dev server exited with code {dev_process.returncode}")
except KeyboardInterrupt:
    print("\nStopping admin dev server...")
    try:
        subprocess.run(f"taskkill /F /T /PID {dev_process.pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
    print("Admin dev server stopped.")
finally:
    log_file.close()
