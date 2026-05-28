import asyncio
import datetime as dt
import hashlib
import logging
import re
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import httpx

from .db_util import db_connection
from .models import RetrievalChunk
from .repositories import (
    create_support_ticket_conn,
    get_customer_context_conn,
    search_kb_conn,
)
from .settings import DATABASE_URL
from .local_llm import get_native_engine, native_local_configured
from .settings import (
    GUARDRAILS,
    INTENTS_POLICY,
    LLM_API_BASE,
    LLM_API_KEY,
    LLM_API_TIMEOUT_SEC,
    LLM_MODEL,
    LLM_ORDER,
    LOCAL_GGUF_PATH,
    LOCAL_LLM_BACKEND,
    LOCAL_LLM_MODEL,
    LOCAL_LLM_TIMEOUT_SEC,
)

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
    """KB RAG: Postgres full-text `search_vector` when migrated; else token-overlap fallback."""

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

    async def retrieve(
        self, query: str, k: int, *, customer_id: Optional[int] = None
    ) -> List[RetrievalChunk]:
        if not DATABASE_URL:
            return self._fallback_retrieve(query, k)
        try:
            async with db_connection(timeout=15.0) as conn:
                chunks = await search_kb_conn(conn, query, k, customer_id=customer_id)
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
        if not DATABASE_URL:
            return self._fallback_context(user_id, text)
        try:
            async with db_connection(timeout=15.0) as conn:
                ctx = await get_customer_context_conn(conn, user_id, text)
            ctx["source"] = "database"
            return ctx
        except Exception as exc:
            logger.warning("ERP context query failed, using stub: %s", exc)
            out = self._fallback_context(user_id, text)
            out["error"] = str(exc)
            return out

    async def create_ticket(self, user_id: str, summary: str) -> str:
        if not DATABASE_URL:
            return self._fallback_ticket(user_id, summary)
        try:
            async with db_connection(timeout=15.0) as conn:
                return await create_support_ticket_conn(conn, user_id, summary)
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
    def __init__(self) -> None:
        self.api_enabled = bool(LLM_API_KEY and LLM_API_KEY.strip() and LLM_API_KEY != "replace-me")
        self.native_local = LOCAL_LLM_BACKEND == "native" and native_local_configured()
        self.ollama_local = LOCAL_LLM_BACKEND == "ollama" and bool(
            LOCAL_LLM_API_BASE and LOCAL_LLM_API_BASE.strip()
        )
        self.local_enabled = self.native_local or self.ollama_local
        self.local_model = LOCAL_LLM_MODEL
        order = [p.strip().lower() for p in LLM_ORDER.split(",") if p.strip()]
        self.auto_order = [m for m in order if m in ("api", "local")] or ["api", "local"]

    async def probe_local(self) -> dict:
        if not self.local_enabled:
            return {
                "reachable": False,
                "model": self.local_model,
                "error": "Local LLM not configured (set LOCAL_LLM_BACKEND and LOCAL_GGUF_PATH)",
            }
        if self.native_local:
            eng = get_native_engine()
            if not eng._ready:
                try:
                    await asyncio.wait_for(asyncio.to_thread(eng.ensure_loaded), timeout=3.0)
                except Exception as exc:
                    return {**eng.status(), "error": str(exc)}
            return eng.status()
        base = LOCAL_LLM_API_BASE.rstrip("/").removesuffix("/v1")
        try:
            timeout = httpx.Timeout(5.0, connect=3.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                tags = await client.get(f"{base}/api/tags")
                tags.raise_for_status()
                names = [m.get("name", "") for m in (tags.json().get("models") or [])]
                has_model = any(
                    self.local_model == n or n.startswith(f"{self.local_model}:")
                    for n in names
                )
                gpu_active = False
                size_vram = 0
                try:
                    ps = await client.get(f"{base}/api/ps")
                    if ps.status_code == 200:
                        for m in ps.json().get("models") or []:
                            vr = int(m.get("size_vram") or 0)
                            if vr > 0:
                                gpu_active = True
                                size_vram = max(size_vram, vr)
                except Exception:
                    pass
                return {
                    "backend": "ollama",
                    "engine": "ollama",
                    "reachable": True,
                    "model": self.local_model,
                    "model_ready": has_model,
                    "gpu_active": gpu_active,
                    "size_vram": size_vram,
                    "installed_models": names[:12],
                    "hint": (
                        None
                        if gpu_active
                        else "Ollama is on CPU. Use LOCAL_LLM_BACKEND=native + download_native_model.ps1 for in-app CUDA, or ensure NVIDIA drivers for Ollama GPU."
                    ),
                }
        except Exception as exc:
            return {"backend": "ollama", "reachable": False, "model": self.local_model, "error": str(exc)}

    @staticmethod
    def _sanitize_answer(answer: str, *, is_admin: bool = False) -> str:
        text = answer.strip()
        # Strip common model/meta leakage
        text = re.sub(
            r"^based on (the )?(information )?(retrieved )?(from )?"
            r"(the )?(erp context|knowledge base|context and knowledge)[^.]*\.?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\([^)]*(?:knowledge base|erp context|prefix|irrelevant|omitted|internal|"
            r"displayed at the start|subsequent messages)[^)]*\)",
            "",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        text = re.sub(
            r"(?im)^(please note|note that|for your information)[,:]?\s*.*$",
            "",
            text,
        )
        text = re.sub(r"(?i)\b(?:erp context|knowledge base|retrieved from)\b[,:]?\s*", "", text)
        text = re.sub(r"(?i)^next step:\s*", "", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()

        if is_admin or re.search(r"\badmin\b", text, flags=re.IGNORECASE):
            text = re.sub(r"^\s*(hello|hi|hey)\s+[A-Za-z][A-Za-z\s'-]{0,40},?\s*", "Hello Admin, ", text, flags=re.IGNORECASE)
            if not re.match(r"^\s*hello admin,", text, flags=re.IGNORECASE):
                text = f"Hello Admin, {text}"
            return text.strip()
        text = re.sub(r"^\s*(hello|hi|hey)\s+[A-Za-z][A-Za-z\s'-]{0,40},?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(
            r"log(?:\s*in|\s*into)\s+to\s+your\s+account",
            "open your Orders page",
            text,
            flags=re.IGNORECASE,
        )
        return text.strip() or answer.strip()

    @staticmethod
    def _local_fallback_answer(
        user_message: str, intent_class: str, erp_ctx: dict, *, is_admin: bool = False
    ) -> str:
        text = user_message.lower()
        role = erp_ctx.get("role")
        if role == "agent" and erp_ctx.get("scope") == "support":
            return (
                "I can help with general ERP guidance from our knowledge base. "
                "To look up a specific customer's billing or orders, an administrator must assist."
            )
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
        if "invoice" in text or "bill" in text:
            hi = erp_ctx.get("highest_invoice")
            if is_admin and not hi:
                hi = erp_ctx.get("highest_invoice_global")
            if hi and hi.get("amount"):
                extra = ""
                if is_admin and hi.get("customer_name"):
                    extra = f" (customer {hi.get('customer_name')})"
                return (
                    f"The highest bill is ${hi['amount']:,.2f} "
                    f"(invoice {hi.get('invoice_number', '')}, order {hi.get('order_number', '')}){extra}. "
                    "Open Billing -> Invoices for details."
                )
            inv = erp_ctx.get("last_invoice") or {}
            if inv.get("invoice_number"):
                return (
                    f"Your latest invoice is {inv['invoice_number']} ({inv.get('status', 'unknown')} status), "
                    f"amount ${inv.get('amount', 0):,.2f}. "
                    "Open Billing -> Invoices to download the PDF."
                )
            return (
                "You can download invoices from Billing -> Invoices. "
                "If you need a specific invoice number, tell me and I can look it up."
            )
        if any(w in text for w in ("total amount", "total order", "sum of")):
            total_sum = erp_ctx.get("orders_total_sum")
            count = erp_ctx.get("order_count")
            if total_sum is not None and count is not None:
                return (
                    f"You have {count} order(s) totaling ${float(total_sum):,.2f}. "
                    "Open Orders for line-item detail."
                )
        if "highest" in text or "largest" in text or "most expensive" in text:
            ho = erp_ctx.get("highest_order")
            if is_admin and not ho:
                ho = erp_ctx.get("highest_order_global")
            if ho and ho.get("total"):
                who = ""
                if is_admin and ho.get("customer_name"):
                    who = f" for {ho['customer_name']} (customer id {ho.get('customer_id')})"
                return (
                    f"The highest order is {ho.get('order_number')} at ${ho['total']:,.2f}{who}."
                )
        if "order" in text or "status" in text:
            recent = erp_ctx.get("recent_orders") or []
            if recent:
                ro = recent[0]
                num = ro.get("order_number", "")
                st = (ro.get("status") or "").lower()
                total = ro.get("total")
                if st == "cancelled":
                    amt = f" (${total:,.2f})" if total else ""
                    return (
                        f"Order {num} was cancelled{amt}, so it was not charged or shipped. "
                        "You can place a new order anytime from Orders, or tell me if you want a ticket to review why it was cancelled."
                    )
                return (
                    f"Your most recent order is {num} — status: {ro.get('status')}. "
                    "Open Orders for line items and tracking."
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

    async def _call_openai_compatible(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        system_prompt: str,
        user_prompt: str,
        max_output_tokens: int,
        timeout_seconds: float = 25.0,
        is_admin: bool = False,
    ) -> str | None:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": max_output_tokens,
        }
        headers = {"Authorization": f"Bearer {api_key}"}
        timeout = httpx.Timeout(timeout_seconds, connect=min(10.0, timeout_seconds))
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(f"{base_url.rstrip('/')}/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices") or []
            if not choices:
                return None
            msg_obj = choices[0].get("message") or {}
            raw = msg_obj.get("content")
            if isinstance(raw, str) and raw.strip():
                return self._sanitize_answer(raw, is_admin=is_admin)
        return None

    async def answer(
        self,
        system_prompt: str,
        user_prompt: str,
        max_output_tokens: int,
        user_message: str,
        intent_class: str,
        erp_ctx: dict,
        llm_mode: str = "auto",
        is_admin: bool = False,
    ) -> tuple[str, str]:
        """Returns (answer, source) where source is api | local | rules."""
        modes: list[str]
        if llm_mode == "api":
            modes = ["api"]
        elif llm_mode == "local":
            modes = ["local"]
        else:
            modes = self.auto_order

        if llm_mode == "local" and not self.local_enabled:
            gguf = LOCAL_GGUF_PATH or "models/Qwen2.5-7B-Instruct-Q4_K_M.gguf"
            return (
                "Local GPU is not ready yet. Run: powershell -ExecutionPolicy Bypass -File "
                f"scripts\\download_native_model.ps1 — then restart the server. "
                f"(Run scripts/download_gguf.py — HF: bartowski/Qwen2.5-7B-Instruct-GGUF)",
                "rules",
            )

        for mode in modes:
            if mode == "api" and self.api_enabled:
                try:
                    text = await self._call_openai_compatible(
                        base_url=LLM_API_BASE,
                        api_key=LLM_API_KEY,
                        model=LLM_MODEL,
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        max_output_tokens=max_output_tokens,
                        timeout_seconds=LLM_API_TIMEOUT_SEC,
                        is_admin=is_admin,
                    )
                    if text:
                        return text, "api"
                except Exception as exc:
                    logger.warning("Hosted LLM API failed: %s", exc)
            if mode == "local" and self.local_enabled:
                try:
                    if self.native_local:
                        raw = await asyncio.wait_for(
                            get_native_engine().generate(
                                system_prompt, user_prompt, max_output_tokens
                            ),
                            timeout=LOCAL_LLM_TIMEOUT_SEC,
                        )
                        text = self._sanitize_answer(raw, is_admin=is_admin)
                        if text:
                            return text, "local"
                    elif self.ollama_local:
                        text = await self._call_openai_compatible(
                            base_url=LOCAL_LLM_API_BASE,
                            api_key=LOCAL_LLM_API_KEY or "ollama",
                            model=LOCAL_LLM_MODEL,
                            system_prompt=system_prompt,
                            user_prompt=user_prompt,
                            max_output_tokens=max_output_tokens,
                            timeout_seconds=LOCAL_LLM_TIMEOUT_SEC,
                            is_admin=is_admin,
                        )
                        if text:
                            return text, "local"
                except Exception as exc:
                    logger.warning("Local LLM failed: %s", exc)

        return (
            self._local_fallback_answer(user_message, intent_class, erp_ctx, is_admin=is_admin),
            "rules",
        )
