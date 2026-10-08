import os
import requests
from dotenv import load_dotenv

load_dotenv("Backend/.env")
api_key = os.getenv("OPENROUTER_API_KEY")

models = [
    "meta-llama/llama-3.3-70b-instruct",
    "qwen/qwen-2.5-72b-instruct"
]

for m in models:
    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": m,
                "messages": [{"role": "user", "content": "Return JSON: {\"status\": \"ok\", \"model\": \"" + m + "\"}"}],
                "temperature": 0.0,
                "max_tokens": 80
            },
            timeout=25
        )
        print(f"{m} -> Status: {r.status_code}")
        if r.status_code == 200:
            print("Response:", r.json()["choices"][0]["message"]["content"][:100])
        else:
            print("Error:", r.text[:200])
    except Exception as e:
        print(f"Exception for {m}: {e}")
