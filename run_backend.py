# """
# TUH Chatbot AI — Backend Runner Script
# ทำหน้าที่: บังคับใช้ SelectorEventLoop บน Windows และรัน Backend Server พอร์ต 8000
# รัน: python run_backend.py
# """
import sys
import os
import asyncio
from pathlib import Path

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        print("🔧 Windows SelectorEventLoop policy configured successfully.")
    except Exception as e:
        print(f"⚠️ Failed to set SelectorEventLoop policy: {e}")

try:
    import uvicorn
except ImportError:
    print("❌ Error: uvicorn is not installed. Please run 'pip install uvicorn'")
    sys.exit(1)

if __name__ == "__main__":
    # เพิ่ม path ของ backend เข้าไปใน sys.path
    backend_dir = Path(__file__).parent / "Backend"
    sys.path.insert(0, str(backend_dir.resolve()))
    
    print("🚀 Starting TUH Chatbot Backend on http://localhost:8000 ...")
    
    async def start_server():
        config = uvicorn.Config(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            loop="asyncio"
        )
        server = uvicorn.Server(config)
        await server.serve()

    asyncio.run(start_server())
