"""Relevance gates and customer-memory extraction for chat learning."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx

from .rag_learn import api_expansion_enabled
from .settings import LLM_API_BASE, LLM_API_KEY, LLM_API_TIMEOUT_SEC, LLM_MODEL

logger = logging.getLogger(__name__)

_PROCEDURAL = re.compile(
    r"\b(how to|you can|open |go to |navigate|steps? to|download|reset password|"
    r"contact support|billing ->|orders ->|settings)\b",
    re.I,
)
_HOW_QUESTION = re.compile(r"\b(how|why|can i|where do i|what is the way)\b", re.I)

_MEMORY_SYSTEM = (
    "You extract durable facts about ONE customer from a support chat turn. "
    "Output ONLY valid JSON: {\"facts\": [{\"category\": \"preference|issue|note|interaction\", "
    "\"fact\": \"...\"}]}. "
    "Include 0-3 facts. Each fact is one short sentence the agent should remember next time. "
    "Store: stated preferences, recurring issues, resolutions promised, communication notes. "
    "Do NOT store raw order totals, invoice numbers, or facts already in ERP (those come from the database). "
    "Do NOT invent facts not stated in the exchange."
)


_ORD_INV = re.compile(r"\bORD-\d+\b|\bINV-\d+\b", re.I)
_PERSONAL_BILLING = re.compile(
    r"\b(highest|largest|my)\b.*\b(bill|invoice|order)\b|\b(bill|invoice)\b.*\b(highest|largest)\b",
    re.I,
)


def should_learn_global_kb(
    *,
    intent_class: str,
    question: str,
    answer: str,
    sources_used: int,
    erp_ctx: Optional[Dict[str, Any]] = None,
) -> bool:
    """Only add to shared KB when the exchange teaches reusable guidance, not bare ERP lookups."""
    if intent_class == "human_required":
        return False
    ctx = erp_ctx or {}
    if ctx.get("role") == "admin" or ctx.get("scope") == "global":
        return False
    q, a = question.strip(), answer.strip()
    if len(q) < 12 or len(a) < 24:
        return False
    if _ORD_INV.search(a) or _PERSONAL_BILLING.search(q):
        return False
    if intent_class == "erp_lookup":
        if _PERSONAL_BILLING.search(q):
            return False
        if _HOW_QUESTION.search(q) or _PROCEDURAL.search(a):
            return True
        return False
    if intent_class == "auto_answer":
        return True
    if intent_class != "erp_lookup":
        return True
    if _HOW_QUESTION.search(q) or _PROCEDURAL.search(a):
        return True
    return False


def memory_key_for_fact(fact: str) -> str:
    norm = re.sub(r"\s+", " ", fact.strip().lower())[:200]
    return hashlib.md5(norm.encode()).hexdigest()[:16]


async def extract_customer_memory_facts(
    question: str,
    answer: str,
    erp_ctx: Dict[str, Any],
) -> List[Dict[str, str]]:
    """Use hosted LLM to distill per-customer memory from a chat turn."""
    if not api_expansion_enabled():
        return _heuristic_memory_facts(question, answer, erp_ctx)
    cid = erp_ctx.get("resolved_customer_id") or erp_ctx.get("customer_id")
    if cid is None or erp_ctx.get("role") == "admin":
        return []
    name = erp_ctx.get("customer_name") or f"customer {cid}"
    user_prompt = (
        f"Customer id: {cid}\nCustomer name: {name}\n"
        f"Account tier: {erp_ctx.get('account_tier', '')}\n\n"
        f"Customer message:\n{question.strip()}\n\n"
        f"Agent reply:\n{answer.strip()}\n\n"
        "Extract JSON facts now."
    )
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": _MEMORY_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": 350,
        "temperature": 0.15,
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
            raw = (resp.json().get("choices") or [{}])[0].get("message", {}).get("content")
        if not isinstance(raw, str):
            return []
        return _parse_memory_json(raw)
    except Exception as exc:
        logger.warning("Customer memory extraction failed: %s", exc)
        return _heuristic_memory_facts(question, answer, erp_ctx)


def _heuristic_memory_facts(
    question: str, answer: str, erp_ctx: Dict[str, Any]
) -> List[Dict[str, str]]:
    """Lightweight fallback when API expansion is off."""
    if erp_ctx.get("role") == "admin":
        return []
    if erp_ctx.get("resolved_customer_id") is None and erp_ctx.get("customer_id") is None:
        return []
    facts: List[Dict[str, str]] = []
    ql = question.lower()
    if any(w in ql for w in ("prefer", "usually", "always", "never", "remind me")):
        facts.append({"category": "preference", "fact": question.strip()[:400]})
    if any(w in ql for w in ("frustrated", "again", "still waiting", "third time")):
        facts.append({"category": "issue", "fact": question.strip()[:400]})
    return facts[:2]


def _parse_memory_json(raw: str) -> List[Dict[str, str]]:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
        text = re.sub(r"\s*```$", "", text)
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return []
    items = obj.get("facts") if isinstance(obj, dict) else None
    if not isinstance(items, list):
        return []
    out: List[Dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        fact = str(item.get("fact", "")).strip()
        if len(fact) < 8:
            continue
        cat = str(item.get("category", "note")).strip().lower()
        if cat not in ("preference", "issue", "note", "interaction"):
            cat = "note"
        out.append({"category": cat, "fact": fact[:2000]})
    return out[:3]
