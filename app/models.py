from pydantic import BaseModel, Field
from typing import Literal, Optional


class ChatRequest(BaseModel):
    user_id: str
    channel: Literal["web", "whatsapp", "slack"]
    message: str = Field(min_length=1, max_length=4000)
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    confidence: float
    action: Literal["answered", "handoff", "clarify"]
    ticket_id: Optional[str] = None
    est_cost_usd: float


class RetrievalChunk(BaseModel):
    id: str
    source: str
    text: str
    score: float


class BudgetSnapshot(BaseModel):
    month: str
    total_usd: float
    budget_usd: float
    alert_triggered: bool
