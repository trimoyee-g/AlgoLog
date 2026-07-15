from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import require_user
from app.services.agent import build_agent

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


@router.post("")
def chat(req: ChatRequest, db: Session = Depends(get_db), user_id: str = Depends(require_user)):
    """Chat with the practice coach. Runs a LangGraph ReAct agent over your own data
    via the local Ollama model. Disabled (503) when OLLAMA_MODEL is unset."""
    if not settings.OLLAMA_MODEL:
        raise HTTPException(503, "Chat is disabled — set OLLAMA_MODEL to a tool-capable Ollama model.")

    agent = build_agent(db, user_id)
    messages = [(m.role, m.content) for m in req.history] + [("user", req.message)]
    # Sync endpoint → FastAPI runs it in a threadpool, so the blocking Ollama call
    # and sync DB session don't stall the event loop.
    try:
        result = agent.invoke({"messages": messages})
    except Exception as e:
        raise HTTPException(502, f"Agent run failed: {e}")
    return {"reply": result["messages"][-1].content}
