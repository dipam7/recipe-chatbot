from __future__ import annotations

import os
from pathlib import Path
from typing import Final, List, Dict
import uuid
import ssl

from fastapi import FastAPI, HTTPException, status, Cookie, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.utils import get_agent_response
from backend.db import save_conversation, get_conversation

# -----------------------------------------------------------------------------
# Application setup
# -----------------------------------------------------------------------------

APP_TITLE: Final[str] = "Recipe Chatbot"
app = FastAPI(title=APP_TITLE)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# -----------------------------------------------------------------------------
# Request / response models
# -----------------------------------------------------------------------------

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    user_id: str | None = None

class ChatResponse(BaseModel):
    messages: List[ChatMessage]

# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    payload: ChatRequest,
    response: Response,
    user_id: str = Cookie(None)
) -> ChatResponse:
    if not user_id and not payload.user_id:
        user_id = str(uuid.uuid4())
        response.set_cookie(key="user_id", value=user_id)
    elif payload.user_id:
        user_id = payload.user_id
        response.set_cookie(key="user_id", value=user_id)

    request_messages = [msg.model_dump() for msg in payload.messages]

    try:
        updated_messages_dicts = get_agent_response(request_messages)
        save_conversation(user_id, updated_messages_dicts)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    response_messages = [ChatMessage(**msg) for msg in updated_messages_dicts]
    return ChatResponse(messages=response_messages)


@app.get("/history/{user_id}", response_model=ChatResponse)
async def get_history(user_id: str) -> ChatResponse:
    messages = get_conversation(user_id)
    return ChatResponse(messages=[ChatMessage(**msg) for msg in messages])


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    html_path = STATIC_DIR / "index.html"
    if not html_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Frontend not found. Did you forget to build it?",
        )
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard() -> HTMLResponse:
    html_path = STATIC_DIR / "admin.html"
    if not html_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin dashboard not found.",
        )
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.get("/test-db")
async def test_database():
    from backend.db import client

    # Print CA cert path to logs
    print("Default CA certs path:", ssl.get_default_verify_paths().cafile)

    try:
        client.admin.command('ping')
        return {"status": "success", "message": "Database connection successful"}
    except Exception as e:
        return {"status": "error", "message": f"Database connection failed: {str(e)}"}
