import os
import subprocess
import sys
import time

# Reconfigure stdout/stderr to use UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def cleanup_leftovers():
    print("🧹 Cleaning up duplicate background processes to prevent port/resource conflicts...")
    try:
        # PowerShell script to kill processes running our scripts/frontends
        cmd = (
            'powershell -Command "'
            'Get-CimInstance Win32_Process -Filter \\"Name = \'python.exe\'\\" | '
            'Where-Object { $_.CommandLine -like \'*server.py*\' -or $_.CommandLine -like \'*run_dev_server.py*\' -or $_.CommandLine -like \'*run_admin_server.py*\' } | '
            'ForEach-Object { Stop-Process -Id $_.ProcessId -Force }; '
            'Get-CimInstance Win32_Process -Filter \\"Name = \'node.exe\'\\" | '
            'Where-Object { $_.CommandLine -like \'*tuh-admin-frontend*\' -or $_.CommandLine -like \'*tuh-chatbot-frontend*\' -or $_.CommandLine -like \'*npm-cli.js*run*dev*\' } | '
            'ForEach-Object { Stop-Process -Id $_.ProcessId -Force }'
            '"'
        )
        subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"⚠️ Cleanup warning: {e}")

# Run cleanup before starting
cleanup_leftovers()

print("==================================================================")
print("Starting all servers (Backend, User Frontend, Admin Frontend)...")
print("==================================================================")

processes = []

try:
    # 1. Start Python Backend API
    print("Starting Python Backend API on http://localhost:8000...")
    backend = subprocess.Popen(["py", "user/backend/server.py"], shell=True)
    processes.append(backend)
    time.sleep(3) # Wait for backend to initialize and load FAISS indices
    
    # 2. Start User Frontend Mirror & Dev Server
    print("Starting User Frontend on http://localhost:5175...")
    user_frontend = subprocess.Popen(["py", "run_dev_server.py"], shell=True)
    processes.append(user_frontend)
    
    # 3. Start Admin Frontend Mirror & Dev Server
    print("Starting Admin Frontend on http://localhost:5174...")
    admin_frontend = subprocess.Popen(["py", "run_admin_server.py"], shell=True)
    processes.append(admin_frontend)
    
    print("\n[SUCCESS] All servers are starting up in the background.")
    print("👉 User UI:  http://localhost:5175")
    print("👉 Admin UI: http://localhost:5174")
    print("👉 Backend:  http://localhost:8000")
    print("\nPress Ctrl+C in this terminal to stop all servers at once.\n")
    
    # Keep the main script alive and monitor child processes
    while True:
        time.sleep(1)
        
except KeyboardInterrupt:
    print("\n🛑 Stopping all servers...")
    for p in processes:
        try:
            # Forcefully kill the process tree (since subprocesses run under cmd/shell launcher)
            subprocess.run(f"taskkill /F /T /PID {p.pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
    print("✨ All servers stopped successfully.")
