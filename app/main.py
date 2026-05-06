from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .db import close_db_pool, get_pool, init_db_pool
from .models import BudgetSnapshot, ChatRequest, ChatResponse
from .repositories import (
    get_customer_row,
    get_order_detail,
    is_admin_user,
    list_orders_for_customer,
    list_unpaid_invoices,
)
from .services import AnswerCache, BudgetTracker, ERPClient, IntentRouter, LLMClient, SimpleRetriever
from .settings import GUARDRAILS

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

router = IntentRouter()
retriever = SimpleRetriever()
erp = ERPClient()
llm = LLMClient()
cache = AnswerCache()
budget = BudgetTracker(monthly_budget=float(GUARDRAILS["monthly_budget_usd"]))


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db_pool()
    yield
    await close_db_pool()


app = FastAPI(title="Lean ERP AI Support Agent", version="1.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _estimate_cost(text: str, output: str) -> float:
    # Lean cost estimator with low-cost model assumptions.
    in_tokens = max(1, int(len(text) / 4))
    out_tokens = max(1, int(len(output) / 4))
    return round((in_tokens / 1_000_000) * 0.4 + (out_tokens / 1_000_000) * 1.6, 6)


def _confidence_from_chunks(chunks_len: int, intent: str) -> float:
    base = 0.55 + min(0.3, chunks_len * 0.07)
    if intent == "human_required":
        return 0.35
    if intent == "erp_lookup":
        return min(0.78, base)
    return min(0.9, base + 0.08)


def _require_pool() -> Any:
    pool = get_pool()
    if pool is None:
        raise HTTPException(
            status_code=503,
            detail="Database not configured. Set DATABASE_URL (Neon pooled connection string).",
        )
    return pool


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "database": get_pool() is not None}


@app.get("/")
def demo_ui() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/metrics/budget", response_model=BudgetSnapshot)
def budget_metrics() -> BudgetSnapshot:
    month, total, alert = budget.snapshot()
    return BudgetSnapshot(
        month=month,
        total_usd=round(total, 4),
        budget_usd=float(GUARDRAILS["monthly_budget_usd"]),
        alert_triggered=alert,
    )


@app.get("/erp/customers/{customer_id}")
async def erp_customer(customer_id: int) -> Dict[str, Any]:
    pool = _require_pool()
    row = await get_customer_row(pool, customer_id)
    if not row:
        raise HTTPException(status_code=404, detail="Customer not found")
    return row


@app.get("/erp/customers/{customer_id}/orders")
async def erp_customer_orders(customer_id: int) -> List[Dict[str, Any]]:
    pool = _require_pool()
    return await list_orders_for_customer(pool, customer_id)


@app.get("/erp/orders/{order_id}")
async def erp_order(order_id: int) -> Dict[str, Any]:
    pool = _require_pool()
    detail = await get_order_detail(pool, order_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Order not found")
    return detail


@app.get("/erp/invoices/unpaid")
async def erp_unpaid_invoices(user_id: str = Query(..., description="Maps to customer id (numeric string)")) -> List[Dict[str, Any]]:
    pool = _require_pool()
    return await list_unpaid_invoices(pool, user_id)


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    if len(req.message) > 4000:
        raise HTTPException(status_code=400, detail="Message too long")

    intent_class = router.route(req.message)
    if intent_class == "human_required" and GUARDRAILS["handoff_on_sensitive_intent"]:
        ticket_id = await erp.create_ticket(req.user_id, f"Sensitive request: {req.message[:140]}")
        return ChatResponse(
            answer="This request needs a human agent for safety. I have created a support ticket.",
            confidence=0.35,
            action="handoff",
            ticket_id=ticket_id,
            est_cost_usd=0.0,
        )

    chunks = await retriever.retrieve(req.message, int(GUARDRAILS["max_retrieval_chunks"]))
    confidence = _confidence_from_chunks(len(chunks), intent_class)

    if confidence < float(GUARDRAILS["min_confidence_to_answer"]) and GUARDRAILS["handoff_on_low_confidence"]:
        ticket_id = await erp.create_ticket(req.user_id, f"Low confidence handoff: {req.message[:140]}")
        return ChatResponse(
            answer="I want to avoid giving you wrong information. I created a human support ticket.",
            confidence=round(confidence, 2),
            action="handoff",
            ticket_id=ticket_id,
            est_cost_usd=0.0,
        )

    cache_key = f"{req.channel}:{req.message.strip().lower()}"
    cached = cache.get(cache_key)
    if cached:
        cost = _estimate_cost(req.message, cached) * 0.2
        budget.add(cost)
        return ChatResponse(
            answer=cached,
            confidence=round(confidence + 0.05, 2),
            action="answered",
            est_cost_usd=round(cost, 6),
        )

    erp_ctx = await erp.get_context(req.user_id, req.message)
    admin_prefix = "Hello Admin, " if is_admin_user(req.user_id) else ""
    kb_context = "\n".join([f"[{c.source}] {c.text}" for c in chunks])
    prompt = (
        "You are a professional ERP customer support representative for a business software product.\n"
        "Tone and style:\n"
        "- Polite, clear, and confident; suitable for enterprise customers.\n"
        "- If the user is admin, start the response with exactly 'Hello Admin,'.\n"
        "- Use plain language; avoid jargon unless the customer used it first.\n"
        "- Do not narrate your process (no 'Based on the query', no 'I see that you asked').\n"
        "- Lead with the answer in one sentence, then add at most one short sentence with the next step or clarification.\n"
        "- Avoid filler, excessive enthusiasm, or casual slang.\n"
        "- Offer a human handoff only when required (missing data, policy/Sensitive matters, or high uncertainty).\n"
        "Grounding rules (critical):\n"
        "- ERP Context comes from our live ERP database connector. Prefer its facts over general product advice.\n"
        "- If ERP Context contains customer_name, recent_orders (with order_number/status), last_invoice, or open_tickets, "
        "you MUST cite those concrete values when answering. Do NOT reply with vague 'log in to your account' waffle when those fields exist.\n"
        "- For order-status questions: if recent_orders has an entry, name that order_number and its status in your first sentence.\n"
        "- If ERP Context includes error equal to invalid_customer_id, explain the id format is invalid and ask for a numeric ERP customer id.\n"
        "- If ERP Context includes error equal to customer_not_found, say we could not match this user id to a customer and ask for the correct ERP customer id (numeric).\n"
        f"ERP Context: {erp_ctx}\n"
        f"Knowledge: {kb_context}\n"
        f"User Message: {req.message}\n"
        f"Response Prefix: {admin_prefix}\n"
        "If something is unknown from ERP Context plus Knowledge, state the limitation briefly and propose one specific next action."
    )
    answer = await llm.answer(prompt, int(GUARDRAILS["max_output_tokens"]), req.message, intent_class, erp_ctx)
    cache.set(cache_key, answer)

    cost = _estimate_cost(prompt, answer)
    budget.add(cost)
    return ChatResponse(
        answer=answer,
        confidence=round(confidence, 2),
        action="answered",
        est_cost_usd=round(cost, 6),
    )


@app.post("/channels/whatsapp")
async def whatsapp_webhook(request: Request) -> dict:
    body = await request.json()
    user_id = body.get("from", "unknown")
    text = body.get("message", "")
    result = await chat(ChatRequest(user_id=user_id, channel="whatsapp", message=text))
    return {"reply": result.answer, "ticket_id": result.ticket_id, "action": result.action}


@app.post("/channels/slack")
async def slack_webhook(request: Request) -> dict:
    body = await request.json()
    event = body.get("event", {})
    user_id = event.get("user", "unknown")
    text = event.get("text", "")
    result = await chat(ChatRequest(user_id=user_id, channel="slack", message=text))
    return {"text": result.answer, "metadata": {"action": result.action, "ticket_id": result.ticket_id}}
