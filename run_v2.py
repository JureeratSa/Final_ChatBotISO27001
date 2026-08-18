# """
# TUH Chatbot AI v2 — Local Runner Script
# ทำหน้าที่: แก้ไขบั๊ก Event Loop SSL บน Windows และรัน Backend Server พอร์ต 8000
# รัน: python run_v2.py
# """
import sys
import os
import asyncio
from pathlib import Path

# 1. บังคับใช้ SelectorEventLoop บน Windows เพื่อป้องกันบั๊ก WinError 87 SSL กับ TiDB Cloud
if sys.platform == 'win32':
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
    backend_dir = Path(__file__).parent / "v2" / "backend"
    sys.path.insert(0, str(backend_dir.resolve()))
    
    print("🚀 Starting TUH Chatbot AI v2 Backend on http://localhost:8000 ...")
    
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
