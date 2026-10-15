"""FastAPI routes for Vapi webhooks and the custom LLM endpoint."""

import json
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from app.config import settings
from app.agent import agent
from app.vapi.assistant_config import get_vapi_assistant_payload
from app.tools.calendar_service import calendar_service
from app.tools.sheets_service import sheets_service

router = APIRouter(prefix="/api/vapi", tags=["vapi"])


@router.get("/status")
async def get_vapi_status():
    """Diagnostic endpoint — shows calendar/sheets connection state."""
    events = calendar_service.list_upcoming_events(max_results=5)
    contacts = sheets_service.get_contacts()
    return {
        "status": "online",
        "service_name": settings.SHOP_NAME,
        "calendar_id": settings.GOOGLE_CALENDAR_ID,
        "calendar_connected": calendar_service.service is not None,
        "upcoming_events_count": len(events),
        "sheets_connected": sheets_service.service is not None,
        "contacts_logged_count": len(contacts),
        "llm_provider": settings.LLM_PROVIDER,
        "llm_model": settings.GROQ_MODEL if settings.LLM_PROVIDER == "groq" else settings.OPENAI_MODEL,
    }


@router.get("/assistant-config")
async def get_assistant_config(request: Request):
    """Return the Vapi assistant JSON payload (used to create/update the voice assistant)."""
    host = request.headers.get("host", "localhost:8000")
    scheme = "https" if ("ngrok" in host or "localtunnel" in host) else "http"
    base_url = settings.SERVER_PUBLIC_URL or f"{scheme}://{host}"
    return get_vapi_assistant_payload(base_url)


@router.post("/webhook")
async def handle_vapi_webhook(request: Request):
    """Handle tool-calls, assistant-request, and end-of-call-report events from Vapi."""
    try:
        data = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc

    msg_type = data.get("message", {}).get("type") or data.get("type")

    if msg_type == "tool-calls":
        tool_calls = data.get("message", {}).get("toolCalls", []) or data.get("toolCalls", [])
        results = []
        for tc in tool_calls:
            call_id = tc.get("id")
            fn = tc.get("function", {})
            fn_name = fn.get("name")
            raw_args = fn.get("arguments", {})
            fn_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            output = agent.execute_tool(fn_name, fn_args)
            results.append({"toolCallId": call_id, "result": json.dumps(output)})
        return JSONResponse(content={"results": results})

    if msg_type == "assistant-request":
        host = request.headers.get("host", "localhost:8000")
        base_url = settings.SERVER_PUBLIC_URL or f"https://{host}"
        return JSONResponse(content={"assistant": get_vapi_assistant_payload(base_url)})

    if msg_type == "end-of-call-report":
        call_obj = data.get("message", {}).get("call", {}) or data.get("call", {})
        phone = call_obj.get("customer", {}).get("number", "Unknown")
        summary = data.get("message", {}).get("summary", "Call completed.")
        sheets_service.log_call(
            caller_name="Voice Caller",
            phone_number=phone,
            intent="Voice Call Completed",
            summary=summary,
            status="Call Ended",
            action_required="None",
        )
        return JSONResponse(content={"status": "received"})

    return JSONResponse(content={"status": "ignored", "type": msg_type})


@router.post("/custom-llm")
async def vapi_custom_llm(request: Request):
    """OpenAI-compatible chat completion endpoint for Vapi Custom LLM mode."""
    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc

    messages = body.get("messages", [])
    reply_text, _ = agent.chat(messages, is_voice=True)

    return {
        "id": "chatcmpl-vapi-cedar-lane",
        "object": "chat.completion",
        "created": 1729000000,
        "model": "cedar-lane-voice-agent",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": reply_text},
                "finish_reason": "stop",
            }
        ],
    }
