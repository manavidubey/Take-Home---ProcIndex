"""FastAPI application for Cedar Lane Auto Detailing AI Receptionist."""

import os
from typing import List, Optional
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import settings
from app.agent import agent
from app.tools.calendar_service import calendar_service
from app.tools.sheets_service import sheets_service
from app.vapi.router import router as vapi_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AI Receptionist for Cedar Lane Auto Detailing",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(vapi_router)

static_dir = os.path.join(os.path.dirname(__file__), "web", "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


class ChatMessage(BaseModel):
    """Schema for a single chat message turn."""
    role: str
    content: str


class ChatRequest(BaseModel):
    """Payload for conversational interaction endpoint."""
    messages: List[ChatMessage]
    is_voice_mode: Optional[bool] = False


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serve the single-page testing chat interface."""
    index_path = os.path.join(os.path.dirname(__file__), "web", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return "<h1>Cedar Lane Auto Detailing AI Receptionist</h1>"


@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """Run chat agent turn with tool execution loop."""
    msgs = [{"role": m.role, "content": m.content} for m in request.messages]
    reply, actions = agent.chat(msgs, is_voice=request.is_voice_mode or False)
    return {
        "reply": reply,
        "actions": actions,
        "calendar_events_count": len(calendar_service.list_upcoming_events(max_results=50)),
        "contacts_count": len(sheets_service.get_contacts()),
    }


@app.get("/api/calendar/events")
async def get_calendar_events():
    """Retrieve current calendar appointments from Google Calendar."""
    events = calendar_service.list_upcoming_events(max_results=50)
    return {
        "calendar_id": settings.GOOGLE_CALENDAR_ID,
        "is_live_google": calendar_service.service is not None,
        "events": events,
    }


@app.get("/api/contacts")
async def get_contacts():
    """Fetch call log entries from the Google Sheet contacts tab."""
    contacts = sheets_service.get_contacts()
    return {
        "sheet_id": settings.GOOGLE_SHEET_ID,
        "is_live_sheet": sheets_service.service is not None and bool(settings.GOOGLE_SHEET_ID),
        "contacts": contacts,
    }


@app.get("/api/health")
async def health_check():
    """Check connectivity to core services and return health status."""
    return {
        "status": "ok",
        "shop": settings.SHOP_NAME,
        "calendar_connected": calendar_service.service is not None,
        "sheets_connected": sheets_service.service is not None,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
