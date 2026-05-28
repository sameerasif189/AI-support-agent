"""Sync registered API feeds into rag_documents; governed chat learning + customer memory."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .feed_curate import curate_feed_to_topics, format_topics_as_document
from .ingest import fetch_api_feed, normalize_feed_url, normalize_title
from .memory_learn import (
    extract_customer_memory_facts,
    should_learn_global_kb,
)
from .rag_learn import expand_chat_to_kb_article
from .repositories import (
    get_feed_by_url,
    get_feeds_due_for_sync,
    insert_rag_document,
    insert_rag_feed,
    list_rag_feeds,
    update_feed_after_sync,
    update_rag_document_body,
    upsert_customer_memory_facts_conn,
    upsert_learned_qa_conn,
)
from .settings import (
    LEARN_CUSTOMER_MEMORY,
    RAG_FEED_AUTO_BOOTSTRAP,
    RAG_FEED_DEFAULT_URL,
)

logger = logging.getLogger(__name__)


async def sync_feed(pool: Any, feed: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch one feed URL and insert or update its rag_documents row."""
    url = normalize_feed_url(feed["url"])
    title = feed["title"]
    try:
        text = await fetch_api_feed(url)
        if not text.strip():
            raise ValueError("URL returned empty content")
        topics = await curate_feed_to_topics(text)
        if topics is not None:
            curated = format_topics_as_document(topics, source_label=title or url)
            body = curated if curated else text.strip()
        else:
            body = text.strip()
        body = body[:50000]
        doc_id = feed.get("document_id")
        if doc_id:
            await update_rag_document_body(pool, doc_id, title[:300], body)
            doc = {"id": doc_id, "title": title, "source_type": "feed", "source_ref": url}
        else:
            doc = await insert_rag_document(
                pool,
                owner_user_id=feed.get("created_by"),
                title=normalize_title(title, url),
                body=body,
                source_type="feed",
                source_ref=url,
                category="feed",
            )
            doc_id = doc["id"]
        await update_feed_after_sync(pool, feed["id"], doc_id, None)
        return {
            "feed_id": feed["id"],
            "ok": True,
            "kb_indexed": True,
            "document_id": doc_id,
            "document": doc,
            "message": f"Indexed in knowledge base as document #{doc_id}",
        }
    except Exception as exc:
        logger.warning("Feed sync failed id=%s: %s", feed["id"], exc)
        await update_feed_after_sync(pool, feed["id"], feed.get("document_id"), str(exc)[:500])
        return {
            "feed_id": feed["id"],
            "ok": False,
            "kb_indexed": False,
            "error": str(exc),
            "message": "Not indexed — sync failed",
        }


async def sync_all_due_feeds(pool: Any) -> List[Dict[str, Any]]:
    feeds = await get_feeds_due_for_sync(pool)
    results = []
    for feed in feeds:
        results.append(await sync_feed(pool, feed))
    return results


async def sync_all_enabled_feeds(pool: Any) -> List[Dict[str, Any]]:
    feeds = await list_rag_feeds(pool, enabled_only=True)
    results = []
    for feed in feeds:
        results.append(await sync_feed(pool, feed))
    return results


async def bootstrap_default_site_feed(pool: Any) -> Optional[Dict[str, Any]]:
    """Ensure the local site feed is registered and synced (no manual UI click)."""
    if not RAG_FEED_AUTO_BOOTSTRAP:
        return None
    url = normalize_feed_url(RAG_FEED_DEFAULT_URL)
    existing = await get_feed_by_url(pool, url)
    if existing:
        feed = existing
    else:
        feed = await insert_rag_feed(
            pool,
            url=url,
            title="Local site (auto)",
            poll_interval_minutes=30,
            created_by=None,
        )
    sync_row = {
        "id": feed["id"],
        "url": feed.get("url") or url,
        "title": feed.get("title") or "Local site (auto)",
        "document_id": feed.get("document_id"),
        "created_by": feed.get("created_by"),
    }
    return await sync_feed(pool, sync_row)


async def maybe_learn_from_chat_conn(
    conn: Any,
    *,
    question: str,
    answer: str,
    confidence: float,
    llm_source: str,
    min_confidence: float,
    owner_user_id: Optional[int] = None,
    intent_class: str = "auto_answer",
    erp_ctx: Optional[Dict[str, Any]] = None,
    sources_used: int = 0,
) -> Dict[str, Any]:
    """Save high-confidence chats: per-customer memory + shared KB when relevant."""
    result: Dict[str, Any] = {"kb_learned": False, "memory_updated": False, "doc": None}
    if llm_source in ("rules", "cache"):
        return result
    if confidence < min_confidence:
        return result
    q = question.strip()
    a = answer.strip()
    if len(q) < 12 or len(a) < 20:
        return result

    ctx = erp_ctx or {}
    cid = ctx.get("resolved_customer_id") or ctx.get("customer_id")

    if LEARN_CUSTOMER_MEMORY and cid is not None and ctx.get("role") != "admin":
        facts = await extract_customer_memory_facts(q, a, ctx)
        if facts:
            n = await upsert_customer_memory_facts_conn(
                conn,
                int(cid),
                facts,
                app_user_id=owner_user_id,
                source_ref=f"chat:{q[:40]}",
            )
            if n > 0:
                result["memory_updated"] = True
                logger.info("Customer memory updated: customer_id=%s facts=%s", cid, n)

    if not should_learn_global_kb(
        intent_class=intent_class,
        question=q,
        answer=a,
        sources_used=sources_used,
        erp_ctx=ctx,
    ):
        return result

    title: Optional[str] = None
    body: Optional[str] = None
    expanded = await expand_chat_to_kb_article(
        q, a, intent_class=intent_class, erp_ctx=ctx
    )
    if expanded:
        title, body = expanded
        logger.info("KB expanded via API for learned article: %s", title[:80])

    doc = await upsert_learned_qa_conn(
        conn, q, a, title=title, body=body, owner_user_id=owner_user_id
    )
    result["kb_learned"] = True
    result["doc"] = doc
    return result


async def maybe_learn_from_chat(
    pool: Any,
    *,
    question: str,
    answer: str,
    confidence: float,
    llm_source: str,
    min_confidence: float,
    owner_user_id: Optional[int] = None,
    intent_class: str = "auto_answer",
    erp_ctx: Optional[Dict[str, Any]] = None,
    sources_used: int = 0,
) -> Dict[str, Any]:
    async with pool.connection() as conn:
        return await maybe_learn_from_chat_conn(
            conn,
            question=question,
            answer=answer,
            confidence=confidence,
            llm_source=llm_source,
            min_confidence=min_confidence,
            owner_user_id=owner_user_id,
            intent_class=intent_class,
            erp_ctx=erp_ctx,
            sources_used=sources_used,
        )
