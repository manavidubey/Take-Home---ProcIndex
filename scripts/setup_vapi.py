"""
Setup script to automatically deploy or update the Cedar Lane Assistant on Vapi
via the Vapi REST API (https://api.vapi.ai).
"""

import os
import sys
import json
import urllib.request
import urllib.error
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.vapi.assistant_config import get_vapi_assistant_payload

def deploy_vapi_assistant():
    vapi_key = settings.VAPI_API_KEY or os.getenv("VAPI_API_KEY")
    if not vapi_key:
        print("⚠️ VAPI_API_KEY is not set in your .env file.")
        print("To deploy automatically:")
        print("1. Get your Private API key from https://dashboard.vapi.ai")
        print("2. Add VAPI_API_KEY=your_key to your .env file")
        print("3. Add SERVER_PUBLIC_URL=https://your-domain.ngrok-free.app (or localtunnel URL)")
        print("\nAlternatively, you can manually copy the JSON configuration from:")
        print("http://localhost:8000 (Vapi Voice Setup tab) or app/vapi/assistant_config.py")
        print("and paste it directly into the Vapi Dashboard!")
        return

    public_url = settings.SERVER_PUBLIC_URL or os.getenv("SERVER_PUBLIC_URL", "")
    if not public_url:
        print("⚠️ Warning: SERVER_PUBLIC_URL is not set. Using localhost placeholder.")
        print("Run 'npx localtunnel --port 8000' and set SERVER_PUBLIC_URL in your .env first.")

    payload = get_vapi_assistant_payload(public_url)
    data = json.dumps(payload).encode("utf-8")

    # Check if assistant ID already exists to update or create
    assistant_id = settings.VAPI_ASSISTANT_ID or os.getenv("VAPI_ASSISTANT_ID")
    
    if assistant_id:
        url = f"https://api.vapi.ai/assistant/{assistant_id}"
        method = "PATCH"
        print(f"🔄 Updating existing Vapi Assistant ({assistant_id})...")
    else:
        url = "https://api.vapi.ai/assistant"
        method = "POST"
        print("🚀 Creating new Vapi Assistant...")

    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {vapi_key}",
            "Content-Type": "application/json"
        },
        method=method
    )

    try:
        with urllib.request.urlopen(req) as resp:
            res_data = json.loads(resp.read().decode())
            new_id = res_data.get("id")
            print("✅ Vapi Assistant Deployed Successfully!")
            print(f"Assistant ID: {new_id}")
            print(f"Name: {res_data.get('name')}")
            print(f"Voice: {res_data.get('voice', {}).get('provider')} ({res_data.get('voice', {}).get('voiceId')})")
            print(f"Transcriber: {res_data.get('transcriber', {}).get('provider')} (Nova-2, 255ms endpointing)")
            print("\nSave this to your .env:")
            print(f"VAPI_ASSISTANT_ID={new_id}")
    except urllib.error.HTTPError as e:
        print(f"❌ Error deploying to Vapi ({e.code}):", e.read().decode())
    except Exception as e:
        print("❌ Unexpected error:", e)

if __name__ == "__main__":
    deploy_vapi_assistant()
