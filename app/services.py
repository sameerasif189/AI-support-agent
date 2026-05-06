import datetime as dt
import hashlib
import logging
import re
from collections import defaultdict
from typing import Dict, List, Tuple

import httpx

from .db import get_pool
from .models import RetrievalChunk
from .repositories import create_support_ticket, get_customer_context, search_kb
from .settings import GUARDRAILS, INTENTS_POLICY, LLM_API_BASE, LLM_API_KEY, LLM_MODEL

logger = logging.getLogger(__name__)

_FALLBACK_DOCS: List[Tuple[str, str, str]] = [
    ("kb-1", "faq", "To get invoice copy, open Billing and click Download Invoice."),
    ("kb-2", "faq", "Order status is visible under Orders in your account dashboard."),
    ("kb-3", "policy", "Sensitive account deletion requests require human verification."),
    ("kb-4", "faq", "Support is available 24/7 via web, WhatsApp, and Slack."),
]


class BudgetTracker:
    def __init__(self, monthly_budget: float) -> None:
        self.monthly_budget = monthly_budget
        self.monthly_spend: Dict[str, float] = defaultdict(float)

    def add(self, usd: float) -> None:
        month = dt.datetime.utcnow().strftime("%Y-%m")
        self.monthly_spend[month] += usd

    def snapshot(self) -> Tuple[str, float, bool]:
        month = dt.datetime.utcnow().strftime("%Y-%m")
        total = self.monthly_spend[month]
        alert = total >= (self.monthly_budget * GUARDRAILS["monthly_alert_percent"] / 100)
        return month, total, alert


class SimpleRetriever:
    """KB retrieval from Postgres `kb_articles`, with static fallback when DB is offline."""

    @staticmethod
    def _fallback_retrieve(query: str, k: int) -> List[RetrievalChunk]:
        tokens = set(query.lower().split())
        scored = []
        for doc_id, src, text in _FALLBACK_DOCS:
            score = len(tokens.intersection(set(text.lower().split()))) / (len(tokens) + 1)
            scored.append((score, doc_id, src, text))
        scored.sort(reverse=True, key=lambda x: x[0])
        return [
            RetrievalChunk(id=d[1], source=d[2], text=d[3], score=float(round(d[0], 3)))
            for d in scored[:k]
        ]

    async def retrieve(self, query: str, k: int) -> List[RetrievalChunk]:
        pool = get_pool()
        if pool is None:
            return self._fallback_retrieve(query, k)
        try:
            chunks = await search_kb(pool, query, k)
            if chunks:
                return chunks
        except Exception as exc:
            logger.warning("KB search failed, using fallback: %s", exc)
        return self._fallback_retrieve(query, k)


class IntentRouter:
    def route(self, text: str) -> str:
        t = text.lower()
        for keyword in INTENTS_POLICY["sensitive_keywords"]:
            if keyword in t:
                return "human_required"
        if any(w in t for w in ["order", "invoice", "ticket", "account", "payment"]):
            return "erp_lookup"
        return "auto_answer"


class ERPClient:
    """Loads customer/order/ticket context from Neon; falls back when DATABASE_URL is unset."""

    @staticmethod
    def _fallback_context(user_id: str, text: str) -> dict:
        return {
            "user_id": user_id,
            "account_tier": "starter",
            "last_order_id": "ORD-10421",
            "open_tickets": 1,
            "query": text,
            "source": "stub",
        }

    @staticmethod
    def _fallback_ticket(user_id: str, summary: str) -> str:
        digest = hashlib.md5(f"{user_id}:{summary}".encode("utf-8")).hexdigest()[:8]
        return f"TKT-{digest.upper()}"

    async def get_context(self, user_id: str, text: str) -> dict:
        pool = get_pool()
        if pool is None:
            return self._fallback_context(user_id, text)
        try:
            ctx = await get_customer_context(pool, user_id, text)
            ctx["source"] = "database"
            return ctx
        except Exception as exc:
            logger.warning("ERP context query failed, using stub: %s", exc)
            out = self._fallback_context(user_id, text)
            out["error"] = str(exc)
            return out

    async def create_ticket(self, user_id: str, summary: str) -> str:
        pool = get_pool()
        if pool is None:
            return self._fallback_ticket(user_id, summary)
        try:
            return await create_support_ticket(pool, user_id, summary)
        except Exception as exc:
            logger.warning("Ticket insert failed, using stub id: %s", exc)
            return self._fallback_ticket(user_id, summary)


class AnswerCache:
    def __init__(self) -> None:
        self._cache: Dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self._cache.get(key)

    def set(self, key: str, value: str) -> None:
        self._cache[key] = value


class LLMClient:
    @staticmethod
    def _sanitize_answer(answer: str) -> str:
        text = answer.strip()
        if re.search(r"\badmin\b", text, flags=re.IGNORECASE):
            text = re.sub(r"^\s*(hello|hi|hey)\s+[A-Za-z][A-Za-z\s'-]{0,40},?\s*", "Hello Admin, ", text, flags=re.IGNORECASE)
            if not re.match(r"^\s*hello admin,", text, flags=re.IGNORECASE):
                text = f"Hello Admin, {text}"
            return text.strip()
        # Keep replies neutral: do not greet with customer names by default.
        text = re.sub(r"^\s*(hello|hi|hey)\s+[A-Za-z][A-Za-z\s'-]{0,40},?\s*", "", text, flags=re.IGNORECASE)
        # Avoid generic login instructions in authenticated support flows.
        text = re.sub(
            r"log(?:\s*in|\s*into)\s+to\s+your\s+account",
            "open your Orders page",
            text,
            flags=re.IGNORECASE,
        )
        return text.strip() or answer.strip()

    def __init__(self) -> None:
        self.enabled = bool(LLM_API_KEY and LLM_API_KEY.strip() and LLM_API_KEY != "replace-me")

    @staticmethod
    def _local_fallback_answer(user_message: str, intent_class: str, erp_ctx: dict) -> str:
        text = user_message.lower()
        if erp_ctx.get("error") == "invalid_customer_id":
            return (
                "I could not verify your account because the customer id format is invalid. "
                "Please sign in again and use a numeric ERP customer id."
            )
        if erp_ctx.get("error") == "customer_not_found":
            return (
                "I could not find an account for this user id. "
                "Please sign in with the same customer id used in the ERP, or contact support."
            )
        if "invoice" in text:
            inv = erp_ctx.get("last_invoice") or {}
            if inv.get("invoice_number"):
                return (
                    f"Your latest invoice is {inv['invoice_number']} ({inv.get('status', 'unknown')} status). "
                    "Open Billing -> Invoices to download the PDF."
                )
            return (
                "You can download invoices from Billing -> Invoices. "
                "If you need a specific invoice number, tell me and I can look it up."
            )
        if "order" in text or "status" in text:
            recent = erp_ctx.get("recent_orders") or []
            if recent:
                ro = recent[0]
                return (
                    f"Your most recent order is {ro.get('order_number')} — status: {ro.get('status')}. "
                    "Open Orders for full line items and tracking."
                )
            order_id = erp_ctx.get("last_order_id", "your latest order")
            return (
                f"I can help with that. Please check Orders -> Details for {order_id}. "
                "If it still looks unclear, I can raise a ticket for a manual status check."
            )
        if "ticket" in text:
            open_tickets = erp_ctx.get("open_tickets", 0)
            return (
                f"You currently have {open_tickets} open support ticket(s). "
                "If you'd like, tell me the issue and I can open a new one now."
            )
        if intent_class == "erp_lookup":
            return (
                "I can check this with your ERP account data. "
                "Please share the specific order, invoice, or ticket detail you want to verify."
            )
        return (
            "Got it. I can help with that. Please share one more detail so I can give you the most accurate answer."
        )

    async def answer(self, prompt: str, max_output_tokens: int, user_message: str, intent_class: str, erp_ctx: dict) -> str:
        if not self.enabled:
            return self._local_fallback_answer(user_message, intent_class, erp_ctx)
        payload = {
            "model": LLM_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_output_tokens,
        }
        headers = {"Authorization": f"Bearer {LLM_API_KEY}"}
        # Keep well under typical Vercel Hobby function limits (~10s) so the browser does not hang.
        timeout = httpx.Timeout(7.0, connect=4.0)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(f"{LLM_API_BASE}/chat/completions", json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                choices = data.get("choices") or []
                if not choices:
                    logger.warning("LLM response missing choices, using local fallback")
                    return self._local_fallback_answer(user_message, intent_class, erp_ctx)
                msg_obj = choices[0].get("message") or {}
                raw = msg_obj.get("content")
                if isinstance(raw, str) and raw.strip():
                    return self._sanitize_answer(raw)
                logger.warning(
                    "LLM returned empty/null content (finish_reason=%s), using local fallback",
                    choices[0].get("finish_reason"),
                )
                return self._local_fallback_answer(user_message, intent_class, erp_ctx)
        except Exception as exc:
            logger.warning("LLM request failed, using local fallback: %s", exc)
            return self._local_fallback_answer(user_message, intent_class, erp_ctx)
