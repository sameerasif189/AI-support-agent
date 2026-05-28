"""Use the hosted LLM API (Groq) to pull only reusable help topics from feed HTML/JSON."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

import httpx

from .rag_learn import api_expansion_enabled
from .settings import LLM_API_BASE, LLM_API_KEY, LLM_API_TIMEOUT_SEC, LLM_MODEL, RAG_FEED_CURATE_WITH_API

logger = logging.getLogger(__name__)

_CURATE_SYSTEM = (
    "You extract reusable ERP customer-support knowledge from feed text (HTML, JSON, or plain text). "
    "Output ONLY valid JSON: {\"topics\":[{\"title\":\"...\",\"body\":\"...\"}]}. "
    "Include ONLY general help: navigation, billing, orders, tickets, policies, how-to steps. "
    "EXCLUDE login forms, UI chrome, marketing, placeholders, and any specific person's account data. "
    "If nothing is useful for a help center, output {\"topics\":[]}. Maximum 10 topics; "
    "each body is 1-3 sentences."
)


def _parse_topics_payload(raw: str) -> List[Dict[str, str]]:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    data = json.loads(text)
    topics = data.get("topics") if isinstance(data, dict) else None
    if not isinstance(topics, list):
        return []
    out: List[Dict[str, str]] = []
    for item in topics:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()[:200]
        body = str(item.get("body") or "").strip()[:4000]
        if title and body:
            out.append({"title": title, "body": body})
    return out


def format_topics_as_document(topics: List[Dict[str, str]], *, source_label: str) -> str:
    if not topics:
        return ""
    lines = [f"# Knowledge from {source_label}", ""]
    for t in topics:
        lines.append(f"## {t['title']}")
        lines.append(t["body"])
        lines.append("")
    return "\n".join(lines).strip()[:50000]


async def curate_feed_to_topics(raw_feed_text: str) -> Optional[List[Dict[str, str]]]:
    """Return curated topics, or None to fall back to raw ingest text."""
    if not RAG_FEED_CURATE_WITH_API or not api_expansion_enabled():
        return None
    sample = raw_feed_text.strip()[:12000]
    if len(sample) < 40:
        return []
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": _CURATE_SYSTEM},
            {"role": "user", "content": f"Feed content:\n\n{sample}\n\nWrite JSON now."},
        ],
        "max_tokens": 1200,
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
            data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            return None
        content = (choices[0].get("message") or {}).get("content") or ""
        topics = _parse_topics_payload(content)
        logger.info("Feed curated to %s topic(s)", len(topics))
        return topics
    except Exception as exc:
        logger.warning("Feed curation failed, using raw text: %s", exc)
        return None
