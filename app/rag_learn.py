"""Expand successful chats into KB articles using the hosted LLM API (Groq)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Optional, Tuple

import httpx

from .settings import LLM_API_BASE, LLM_API_KEY, LLM_API_TIMEOUT_SEC, LLM_MODEL, LEARN_EXPAND_WITH_API

logger = logging.getLogger(__name__)

_EXPAND_SYSTEM = (
    "You are a knowledge-base editor for an ERP support product. "
    "Turn a single support chat exchange into a reusable help article for future customers. "
    "Output ONLY valid JSON with keys title and body (no markdown fences). "
    "title: concise topic, max 120 characters. "
    "body: 2-4 clear sentences of actionable guidance (steps, where to click, policy). "
    "Generalize: omit customer names and one-off order/invoice numbers unless the policy is inherently numeric. "
    "Skip if the exchange is only reporting account-specific order status with no reusable lesson — output "
    '{"title":"","body":""} in that case.'
)


def api_expansion_enabled() -> bool:
    key = (LLM_API_KEY or "").strip()
    return LEARN_EXPAND_WITH_API and bool(key) and key != "replace-me"


async def expand_chat_to_kb_article(
    question: str,
    answer: str,
    *,
    intent_class: str = "auto_answer",
    erp_ctx: Optional[Dict[str, Any]] = None,
) -> Optional[Tuple[str, str]]:
    """Use Groq/OpenAI-compatible API to distill Q&A into title + body for RAG."""
    if not api_expansion_enabled():
        return None
    q = question.strip()
    a = answer.strip()
    if len(q) < 12 or len(a) < 20:
        return None
    ctx_note = ""
    if erp_ctx and erp_ctx.get("role") == "admin":
        ctx_note = "\n(Admin view — write global guidance only.)\n"
    elif intent_class == "erp_lookup":
        ctx_note = "\n(ERP lookup — only write an article if the reply teaches a reusable process, not raw account data.)\n"
    user_prompt = (
        f"Intent: {intent_class}\n"
        f"{ctx_note}"
        f"Customer question:\n{q}\n\n"
        f"Support agent reply:\n{a}\n\n"
        "Write the JSON article now."
    )
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": _EXPAND_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": 400,
        "temperature": 0.2,
    }
    headers = {"Authorization": f"Bearer {LLM_API_KEY}"}
    timeout = httpx.Timeout(LLM_API_TIMEOUT_SEC, connect=min(10.0, LLM_API_TIMEOUT_SEC))
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{LLM_API_BASE.rstrip('/')}/chat/completions",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            return None
        raw = (choices[0].get("message") or {}).get("content")
        if not isinstance(raw, str) or not raw.strip():
            return None
        parsed = _parse_article_json(raw)
        if not parsed:
            return None
        title, body = parsed
        if len(title) < 5 or len(body) < 20:
            return None
        if not title and not body:
            return None
        return title[:300], body[:50000]
    except Exception as exc:
        logger.warning("KB expansion via API failed: %s", exc)
        return None


def _parse_article_json(raw: str) -> Optional[Tuple[str, str]]:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[^{}]*\"title\"[^{}]*\}", text, re.DOTALL)
        if not match:
            return None
        try:
            obj = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    if not isinstance(obj, dict):
        return None
    title = str(obj.get("title", "")).strip()
    body = str(obj.get("body", "")).strip()
    if title and body:
        return title, body
    return None
