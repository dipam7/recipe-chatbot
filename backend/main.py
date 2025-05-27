from __future__ import annotations

"""FastAPI application entry-point for the recipe chatbot."""

import os
from pathlib import Path
from typing import Final, List, Dict, Optional
import uuid

from fastapi import FastAPI, HTTPException, status, Cookie, Response, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.utils import get_agent_response, MODEL_NAME  # noqa: WPS433 import from parent
from backend.db import save_conversation, get_conversation, log_user_query, get_query_stats

# -----------------------------------------------------------------------------
# Application setup
# -----------------------------------------------------------------------------

APP_TITLE: Final[str] = "Recipe Chatbot"
app = FastAPI(title=APP_TITLE)

# Enable CORS for all origins in development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your actual domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static assets (currently just the HTML) under `/static/*`.
STATIC_DIR = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# -----------------------------------------------------------------------------
# Request / response models
# -----------------------------------------------------------------------------

class ChatMessage(BaseModel):
    """Schema for a single message in the chat history."""
    role: str = Field(..., description="Role of the message sender (system, user, or assistant).")
    content: str = Field(..., description="Content of the message.")

class ChatRequest(BaseModel):
    """Schema for incoming chat messages."""
    messages: List[ChatMessage] = Field(..., description="The entire conversation history.")
    user_id: str = Field(None, description="Optional user ID for retrieving conversation history.")


class ChatResponse(BaseModel):
    """Schema for the assistant's reply returned to the front-end."""
    messages: List[ChatMessage] = Field(..., description="The updated conversation history.")


class StatsResponse(BaseModel):
    """Schema for query statistics."""
    total_queries: int
    unique_users: int
    daily_counts: List[Dict]


# -----------------------------------------------------------------------------
# Authentication dependency for admin routes
# -----------------------------------------------------------------------------

def verify_admin_token(admin_token: str = Cookie(None)) -> bool:
    """Verify admin token for protected routes."""
    valid_token = os.environ.get("ADMIN_TOKEN")
    if not valid_token or admin_token != valid_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token",
        )
    return True


# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    payload: ChatRequest,
    response: Response,
    user_id: str = Cookie(None)
) -> ChatResponse:  # noqa: WPS430
    """Main conversational endpoint with conversation persistence.

    It proxies the user's message list to the underlying agent and returns the updated list.
    """
    # Generate user_id if not provided
    if not user_id and not payload.user_id:
        user_id = str(uuid.uuid4())
        response.set_cookie(key="user_id", value=user_id)
    elif payload.user_id:
        user_id = payload.user_id
        response.set_cookie(key="user_id", value=user_id)
    
    # Convert Pydantic models to simple dicts for the agent
    request_messages: List[Dict[str, str]] = [msg.model_dump() for msg in payload.messages]
    
    # Extract the user's latest query (for logging)
    latest_user_message = next((msg for msg in reversed(request_messages) if msg["role"] == "user"), None)
    
    try:
        updated_messages_dicts = get_agent_response(request_messages)
        
        # Get the model's response (for logging)
        latest_assistant_message = next((msg for msg in reversed(updated_messages_dicts) if msg["role"] == "assistant"), None)
        
        # Save the conversation to the database
        save_conversation(user_id, updated_messages_dicts)
        
        # Log the query if we have both user query and assistant response
        if latest_user_message and latest_assistant_message:
            metadata = {
                "conversation_length": len(updated_messages_dicts),
                "timestamp": uuid.uuid4().hex[:8]  # Add a unique identifier for the interaction
            }
            log_user_query(
                user_id=user_id,
                query=latest_user_message["content"],
                response=latest_assistant_message["content"],
                model_name=MODEL_NAME,
                metadata=metadata
            )
            
    except Exception as exc:  # noqa: BLE001 broad; surface as HTTP 500
        # In production you would log the traceback here.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    # Convert dicts back to Pydantic models for the response
    response_messages: List[ChatMessage] = [ChatMessage(**msg) for msg in updated_messages_dicts]
    return ChatResponse(messages=response_messages)


@app.get("/history/{user_id}", response_model=ChatResponse)
async def get_history(user_id: str) -> ChatResponse:
    """Retrieve conversation history for a user."""
    messages = get_conversation(user_id)
    response_messages = [ChatMessage(**msg) for msg in messages]
    return ChatResponse(messages=response_messages)


@app.get("/admin/stats", response_model=StatsResponse)
async def get_admin_stats(days: int = 7) -> StatsResponse:
    """Get query statistics for admin dashboard.
    
    Public endpoint with no authentication required.
    """
    stats = get_query_stats(days)
    return StatsResponse(**stats)


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:  # noqa: WPS430
    """Serve the chat UI."""

    html_path = STATIC_DIR / "index.html"
    if not html_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Frontend not found. Did you forget to build it?",
        )

    return HTMLResponse(html_path.read_text(encoding="utf-8"))

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard() -> HTMLResponse:
    """Serve the admin dashboard UI."""

    html_path = STATIC_DIR / "admin.html"
    if not html_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin dashboard not found.",
        )

    return HTMLResponse(html_path.read_text(encoding="utf-8")) 


@app.get("/test-db")
async def test_database():
    """Test database connectivity."""
    try:
        from backend.db import client
        # Test the connection
        client.admin.command('ping')
        return {"status": "success", "message": "Database connection successful"}
    except Exception as e:
        return {"status": "error", "message": f"Database connection failed: {str(e)}"}