"""Optimized Vapi Assistant Configuration for Cedar Lane Auto Detailing.

Tuned for low voice response latency.
"""

from typing import Dict, Any
from app.prompts import get_system_prompt, TOOLS_SPEC


def get_vapi_assistant_payload(server_url: str = "") -> Dict[str, Any]:
    """Generate assistant specification dictionary for Vapi API creation."""
    base_domain = server_url.rstrip("/") if server_url else "https://YOUR_DOMAIN.ngrok-free.app"
    webhook_url = f"{base_domain}/api/vapi/webhook"

    vapi_tools = [
        {
            "type": "function",
            "async": False,
            "server": {"url": webhook_url},
            "function": tool_entry["function"],
        }
        for tool_entry in TOOLS_SPEC
    ]

    return {
        "name": "Cedar Lane Auto Detailing Receptionist",
        "transcriber": {
            "provider": "deepgram",
            "model": "nova-2",
            "language": "en-US",
            "endpointing": 255,
            "smartFormat": True,
        },
        "model": {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "temperature": 0.3,
            "maxTokens": 150,
            "messages": [
                {
                    "role": "system",
                    "content": get_system_prompt(is_voice=True),
                }
            ],
            "tools": vapi_tools,
        },
        "voice": {
            "provider": "cartesia",
            "voiceId": "79a125e8-cd45-4c13-8a67-188112f4dd22",
            "model": "sonic-english",
        },
        "firstMessage": "Thanks for calling Cedar Lane Auto Detailing. How can I help you today?",
        "firstMessageMode": "assistant-speaks-first",
        "silenceTimeoutSeconds": 25,
        "maxDurationSeconds": 600,
        "serverUrl": webhook_url,
    }
