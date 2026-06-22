from pydantic import BaseModel, Field, HttpUrl
from typing import Literal, Optional


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=100)


class UserInfo(BaseModel):
    id: int
    username: str
    first_name: str
    role: Literal["admin", "agent", "customer"]
    customer_id: Optional[int] = None


class LoginResponse(BaseModel):
    token: str
    expires_at: str
    user: UserInfo


class ChatRequest(BaseModel):
    user_id: Optional[str] = None
    channel: Literal["web", "whatsapp", "slack", "site"] = "web"
    message: str = Field(min_length=1, max_length=4000)
    session_id: Optional[str] = None
    llm_mode: Literal["auto", "api", "local"] = "auto"


class PublicChatRequest(BaseModel):
    """Visitor chat from embedded widget on marketing site (no login)."""
    message: str = Field(min_length=1, max_length=4000)
    session_id: Optional[str] = None
    visitor_name: Optional[str] = Field(default=None, max_length=120)
    visitor_email: Optional[str] = Field(default=None, max_length=254)
    llm_mode: Literal["auto", "api", "local"] = "api"


class ChatResponse(BaseModel):
    answer: str
    confidence: float
    action: Literal["answered", "handoff", "clarify"]
    ticket_id: Optional[str] = None
    est_cost_usd: float
    llm_source: Optional[str] = None
    sources_used: int = 0
    session_id: Optional[str] = None
    kb_learned: bool = False
    memory_updated: bool = False
    booking_url: Optional[str] = None
    contact_email: Optional[str] = None
    proposal_hint: Optional[str] = None


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


class KnowledgeTextRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1, max_length=50000)
    category: str = Field(default="user", max_length=64)


class KnowledgeApiFeedRequest(BaseModel):
    url: HttpUrl
    title: Optional[str] = Field(default=None, max_length=300)


class KnowledgeFeedRegisterRequest(BaseModel):
    url: HttpUrl
    title: str = Field(min_length=1, max_length=300)
    poll_interval_minutes: int = Field(default=60, ge=5, le=10080)
    sync_now: bool = True


class KnowledgeWebhookRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1, max_length=50000)
    category: str = Field(default="webhook", max_length=64)
