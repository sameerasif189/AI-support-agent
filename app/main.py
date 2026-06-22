import asyncio
import logging
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, Request, Response, UploadFile
import json

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .access import (
    assert_customer_record_access,
    assert_order_record_access,
    erp_ctx_for_json,
    filter_erp_ctx_for_prompt,
    filter_kb_chunks_for_customer,
    format_customer_billing_answer,
    is_personal_billing_query,
)
from .auth import erp_user_id_for, login_user, logout_user, require_ingest_role, require_user, resolve_user
from .db import close_db_pool, database_ready, get_pool, init_db_pool
from .db_util import db_connection
from .ingest import SITE_FEED_JSON, extract_text_from_bytes, fetch_api_feed, normalize_title
from .models import (
    BudgetSnapshot,
    ChatRequest,
    ChatResponse,
    PublicChatRequest,
    KnowledgeApiFeedRequest,
    KnowledgeFeedRegisterRequest,
    KnowledgeTextRequest,
    KnowledgeWebhookRequest,
    LoginRequest,
    LoginResponse,
    UserInfo,
)
from .chat_store import persist_chat_turn_conn
from .rag_sync import (
    bootstrap_default_site_feed,
    maybe_learn_from_chat,
    maybe_learn_from_chat_conn,
    sync_all_due_feeds,
    sync_all_enabled_feeds,
    sync_feed,
)
from .repositories import (
    get_customer_row,
    get_order_detail,
    get_rag_feed,
    insert_rag_document,
    insert_rag_feed,
    is_admin_user,
    get_customer_memory_lines_conn,
    get_chat_session_erp_uid_conn,
    get_recent_chat_for_prompt_conn,
    list_chat_messages_conn,
    list_orders_for_customer,
    parse_customer_id,
    list_rag_documents,
    list_rag_feeds,
    list_unpaid_invoices,
)
from .services import AnswerCache, BudgetTracker, ERPClient, IntentRouter, LLMClient, SimpleRetriever
from .local_llm import get_native_engine, native_local_configured
from .settings import (
    CORS_ALLOWED_ORIGINS,
    DATABASE_URL,
    GUARDRAILS,
    KNOWLEDGE_WEBHOOK_KEY,
    CHAT_HISTORY_TURNS,
    CHAT_MEMORY_IN_PROMPT,
    LEARN_CUSTOMER_MEMORY,
    LEARN_EXPAND_WITH_API,
    LEARN_FROM_CHAT,
    LEARN_MIN_CONFIDENCE,
    PUBLIC_CHAT_API_KEY,
    RAG_RETRIEVAL_MODE,
    RAG_VECTOR_ENABLED,
    LLM_ORDER,
    LOCAL_LLM_BACKEND,
    LOCAL_LLM_MODEL,
    LOCAL_LLM_PRELOAD,
    RAG_FEED_SYNC_ENABLED,
    RAG_FEED_SYNC_TICK_SEC,
    SITE_BOOKING_URL,
    SITE_BOT_ENABLED,
    SITE_COMPANY_NAME,
    SITE_CONTACT_EMAIL,
    SITE_PROPOSAL_URL,
    SITE_RAG_FEED_URL,
    WHATSAPP_APP_SECRET,
    WHATSAPP_DEMO_ERP_UID,
    WHATSAPP_VERIFY_TOKEN,
)
from .site_bot import (
    append_booking_link_if_needed,
    booking_reply,
    build_site_erp_context,
    build_site_system_prompt,
    build_site_user_prompt,
    site_public_erp_uid,
    site_response_meta,
)
from .whatsapp_meta import (
    erp_uid_for_whatsapp_sender,
    extract_inbound_messages,
    is_legacy_test_payload,
    mark_message_read,
    send_text_message,
    validate_signature,
    verify_webhook,
    whatsapp_configured,
)

logger = logging.getLogger(__name__)
_feed_sync_task: Optional[asyncio.Task] = None

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

router = IntentRouter()
retriever = SimpleRetriever()
erp = ERPClient()
llm = LLMClient()
cache = AnswerCache()
budget = BudgetTracker(monthly_budget=float(GUARDRAILS["monthly_budget_usd"]))


async def _rag_feed_sync_loop() -> None:
    while True:
        await asyncio.sleep(RAG_FEED_SYNC_TICK_SEC)
        pool = get_pool()
        if not pool or not RAG_FEED_SYNC_ENABLED:
            continue
        try:
            results = await sync_all_due_feeds(pool)
            if results:
                logger.info("RAG feed sync: %s feed(s) processed", len(results))
        except Exception as exc:
            logger.warning("RAG feed sync loop error: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _feed_sync_task
    await init_db_pool()
    if LOCAL_LLM_BACKEND == "native" and LOCAL_LLM_PRELOAD and native_local_configured():
        try:
            await asyncio.to_thread(get_native_engine().ensure_loaded)
            logger.info("Native local model preloaded")
        except Exception as exc:
            logger.warning("Native model preload failed: %s", exc)
    if RAG_FEED_SYNC_ENABLED:
        _feed_sync_task = asyncio.create_task(_rag_feed_sync_loop())
    pool = get_pool()
    if pool and DATABASE_URL:
        try:
            from .repositories import purge_account_specific_learned_kb_conn

            async with db_connection(timeout=20.0) as conn:
                n = await purge_account_specific_learned_kb_conn(conn)
            if n:
                logger.info("Purged %s leaked learned KB document(s)", n)
        except Exception as exc:
            logger.warning("Learned KB purge skipped: %s", exc)
        try:
            result = await bootstrap_default_site_feed(pool)
            if result and result.get("ok"):
                logger.info("Default site feed indexed: doc #%s", result.get("document_id"))
        except Exception as exc:
            logger.warning("Default site feed bootstrap skipped: %s", exc)
    yield
    if _feed_sync_task is not None:
        _feed_sync_task.cancel()
        try:
            await _feed_sync_task
        except asyncio.CancelledError:
            pass
    await close_db_pool()


app = FastAPI(title="ERP AI Support Agent (RAG + Auth)", version="2.0.0", lifespan=lifespan)
_cors_origins = [o.strip() for o in CORS_ALLOWED_ORIGINS.split(",") if o.strip()]
if _cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Site-Api-Key"],
    )
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _estimate_cost(text: str, output: str) -> float:
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
    if not database_ready():
        raise HTTPException(
            status_code=503,
            detail="Database not configured. Set DATABASE_URL (Neon pooled connection string).",
        )
    return pool


async def _finalize_chat(
    *,
    session_id: Optional[str],
    app_user_id: Optional[int],
    erp_uid: str,
    channel: str,
    user_message: str,
    response: ChatResponse,
    intent_class: str,
    try_learn: bool = True,
    erp_ctx: Optional[Dict[str, Any]] = None,
    sources_used: int = 0,
) -> ChatResponse:
    """Persist chat turn to Neon; optionally expand KB via Groq API."""
    if not DATABASE_URL:
        return response
    rag_doc_id: Optional[int] = None
    kb_learned = False
    memory_updated = False
    try:
        async with db_connection(timeout=15.0) as conn:
            if try_learn and LEARN_FROM_CHAT and response.action == "answered":
                learn_result = await maybe_learn_from_chat_conn(
                    conn,
                    question=user_message,
                    answer=response.answer,
                    confidence=response.confidence,
                    llm_source=response.llm_source or "rules",
                    min_confidence=LEARN_MIN_CONFIDENCE,
                    owner_user_id=app_user_id,
                    intent_class=intent_class,
                    erp_ctx=erp_ctx,
                    sources_used=sources_used,
                )
                doc = learn_result.get("doc")
                kb_learned = bool(learn_result.get("kb_learned"))
                memory_updated = bool(learn_result.get("memory_updated"))
                if doc:
                    rag_doc_id = doc.get("id")
            sid = await persist_chat_turn_conn(
                conn,
                session_id=session_id,
                user_id=app_user_id,
                erp_uid=erp_uid,
                channel=channel,
                user_message=user_message,
                assistant_message=response.answer,
                llm_source=response.llm_source,
                confidence=response.confidence,
                intent_class=intent_class,
                sources_used=response.sources_used,
                rag_document_id=rag_doc_id,
            )
        return response.model_copy(
            update={
                "session_id": sid,
                "kb_learned": kb_learned,
                "memory_updated": memory_updated,
            }
        )
    except Exception as exc:
        logger.warning("Chat persist/learn skipped: %s", exc)
        return response


async def _run_chat(
    *,
    erp_uid: str,
    channel: str,
    message: str,
    llm_mode: str,
    session_id: Optional[str] = None,
    app_user_id: Optional[int] = None,
    site_mode: bool = False,
    site_visitor: Optional[Dict[str, str]] = None,
) -> ChatResponse:
    if len(message) > 4000:
        raise HTTPException(status_code=400, detail="Message too long")

    def _site_meta() -> Dict[str, Optional[str]]:
        return site_response_meta(message, visitor=site_visitor)

    def _wrap_site(response: ChatResponse, **kwargs: Any) -> ChatResponse:
        meta = _site_meta()
        answer = append_booking_link_if_needed(response.answer, message, site_visitor)
        return response.model_copy(
            update={
                "answer": answer,
                "booking_url": meta.get("booking_url"),
                "contact_email": meta.get("contact_email"),
                "proposal_hint": meta.get("proposal_hint"),
                **kwargs,
            }
        )

    if site_mode:
        booked = booking_reply(message, site_visitor)
        if booked:
            return await _finalize_chat(
                session_id=session_id,
                app_user_id=None,
                erp_uid=erp_uid,
                channel=channel,
                user_message=message,
                intent_class="auto_answer",
                try_learn=False,
                response=_wrap_site(
                    ChatResponse(
                        answer=booked,
                        confidence=0.95,
                        action="answered",
                        est_cost_usd=0.0,
                        llm_source="rules",
                        sources_used=0,
                    )
                ),
            )
    intent_class = router.route(message)
    if intent_class == "human_required" and GUARDRAILS["handoff_on_sensitive_intent"]:
        if site_mode:
            contact = SITE_CONTACT_EMAIL or "the Contact form on this website"
            handoff_answer = (
                f"This needs a human from our team. Please reach us via {contact} "
                "and describe your request."
            )
            return await _finalize_chat(
                session_id=session_id,
                app_user_id=None,
                erp_uid=erp_uid,
                channel=channel,
                user_message=message,
                intent_class=intent_class,
                try_learn=False,
                response=_wrap_site(
                    ChatResponse(
                        answer=handoff_answer,
                        confidence=0.35,
                        action="handoff",
                        est_cost_usd=0.0,
                        llm_source="rules",
                        sources_used=0,
                    )
                ),
            )
        ticket_id = await erp.create_ticket(erp_uid, f"Sensitive request: {message[:140]}")
        return await _finalize_chat(
            session_id=session_id,
            app_user_id=app_user_id,
            erp_uid=erp_uid,
            channel=channel,
            user_message=message,
            intent_class=intent_class,
            try_learn=False,
            response=ChatResponse(
                answer="This request needs a human agent for safety. I have created a support ticket.",
                confidence=0.35,
                action="handoff",
                ticket_id=ticket_id,
                est_cost_usd=0.0,
                llm_source="rules",
                sources_used=0,
            ),
        )

    customer_id = (
        None
        if site_mode
        else (parse_customer_id(erp_uid) if not is_admin_user(erp_uid) else None)
    )
    chunks = await retriever.retrieve(
        message,
        int(GUARDRAILS["max_retrieval_chunks"]),
        customer_id=customer_id,
    )
    is_admin = False if site_mode else is_admin_user(erp_uid)
    confidence = _confidence_from_chunks(len(chunks), intent_class)

    if (
        site_mode
        and confidence < float(GUARDRAILS["min_confidence_to_answer"])
        and GUARDRAILS.get("handoff_on_low_confidence", True)
    ):
        contact = SITE_CONTACT_EMAIL or "our Contact page"
        return await _finalize_chat(
            session_id=session_id,
            app_user_id=None,
            erp_uid=erp_uid,
            channel=channel,
            user_message=message,
            intent_class=intent_class,
            try_learn=False,
            response=_wrap_site(
                ChatResponse(
                    answer=(
                        f"I am not fully sure from our help articles. "
                        f"Please email {contact} or use the contact form and our team will assist you."
                    ),
                    confidence=confidence,
                    action="handoff",
                    est_cost_usd=0.0,
                    llm_source="rules",
                    sources_used=len(chunks),
                )
            ),
        )

    if confidence < float(GUARDRAILS["min_confidence_to_answer"]) and GUARDRAILS["handoff_on_low_confidence"]:
        ticket_id = await erp.create_ticket(erp_uid, f"Low confidence handoff: {message[:140]}")
        return await _finalize_chat(
            session_id=session_id,
            app_user_id=app_user_id,
            erp_uid=erp_uid,
            channel=channel,
            user_message=message,
            intent_class=intent_class,
            try_learn=False,
            response=ChatResponse(
                answer="I want to avoid giving you wrong information. I created a human support ticket.",
                confidence=round(confidence, 2),
                action="handoff",
                ticket_id=ticket_id,
                est_cost_usd=0.0,
                llm_source="rules",
                sources_used=len(chunks),
            ),
        )

    cache_key = f"v5:{channel}:{erp_uid}:{message.strip().lower()}"
    cached = cache.get(cache_key)
    if cached:
        cost = _estimate_cost(message, cached) * 0.2
        budget.add(cost)
        cached_resp = ChatResponse(
            answer=cached,
            confidence=round(confidence + 0.05, 2),
            action="answered",
            est_cost_usd=round(cost, 6),
            llm_source="cache",
            sources_used=len(chunks),
        )
        if site_mode:
            cached_resp = _wrap_site(cached_resp)
        return await _finalize_chat(
            session_id=session_id,
            app_user_id=app_user_id,
            erp_uid=erp_uid,
            channel=channel,
            user_message=message,
            intent_class=intent_class,
            try_learn=False,
            response=cached_resp,
        )

    if site_mode:
        erp_ctx = build_site_erp_context(site_visitor)
        prompt_ctx = erp_ctx
    else:
        erp_ctx = await erp.get_context(erp_uid, message)
        prompt_ctx = filter_erp_ctx_for_prompt(erp_ctx, is_admin=is_admin)
    if not is_admin and not site_mode:
        chunks = filter_kb_chunks_for_customer(
            chunks, erp_ctx=prompt_ctx, message=message, intent_class=intent_class
        )
    kb_context = "\n".join([f"- {c.text}" for c in chunks]) if chunks else "(none)"

    if (
        not site_mode
        and not is_admin
        and intent_class == "erp_lookup"
        and is_personal_billing_query(message)
    ):
        scoped = format_customer_billing_answer(prompt_ctx)
        if scoped:
            cost = _estimate_cost(message, scoped)
            budget.add(cost * 0.1)
            return await _finalize_chat(
                session_id=session_id,
                app_user_id=app_user_id,
                erp_uid=erp_uid,
                channel=channel,
                user_message=message,
                intent_class=intent_class,
                response=ChatResponse(
                    answer=scoped,
                    confidence=0.9,
                    action="answered",
                    est_cost_usd=round(cost * 0.1, 6),
                    llm_source="rules",
                    sources_used=0,
                ),
            )

    memory_block = ""
    chat_history_block = ""
    if DATABASE_URL and CHAT_MEMORY_IN_PROMPT and (customer_id is not None or (site_mode and session_id)):
        try:
            async with db_connection(timeout=12.0) as conn:
                if customer_id is not None and not site_mode:
                    mem_lines = await get_customer_memory_lines_conn(
                        conn, customer_id, message, limit=5
                    )
                    if mem_lines:
                        memory_block = (
                            "\nWhat you already know about this customer (use naturally, do not list as 'memory'):\n"
                            + "\n".join(f"- {line}" for line in mem_lines)
                            + "\n"
                        )
                if session_id and CHAT_HISTORY_TURNS > 0:
                    sess_uid = await get_chat_session_erp_uid_conn(conn, session_id)
                    if sess_uid and sess_uid != erp_uid:
                        session_id = None
                    prior = (
                        await get_recent_chat_for_prompt_conn(
                            conn, session_id, CHAT_HISTORY_TURNS
                        )
                        if session_id
                        else []
                    )
                    if prior:
                        lines = []
                        for role, content in prior:
                            label = "Customer" if role == "user" else "You"
                            lines.append(f"{label}: {content[:500]}")
                        chat_history_block = (
                            "\nRecent conversation in this session:\n"
                            + "\n".join(lines)
                            + "\n"
                        )
        except Exception as exc:
            logger.warning("Memory/history load skipped: %s", exc)

    if site_mode:
        system_prompt = build_site_system_prompt(visitor=site_visitor)
        user_prompt = build_site_user_prompt(
            message, kb_context, chat_history_block=chat_history_block
        )
    else:
        system_prompt = (
            "You are a human customer support agent for an ERP product. "
            "Reply in plain, professional language as if speaking to the customer in chat.\n"
            "STRICT RULES:\n"
            "- Output ONLY the customer-facing message. No meta-commentary.\n"
            "- NEVER say: 'Based on', 'ERP Context', 'Knowledge base', 'retrieved', 'I found that', "
            "'internal data', 'policy number', or explain your reasoning.\n"
            "- NEVER use parenthetical asides about instructions, irrelevant articles, or prefixes.\n"
            "- Do not name KB article titles unless the customer explicitly asked for policy text.\n"
            "- First sentence = direct answer with concrete facts (order number, status, amounts).\n"
            "- Optional: one short sentence with a clear next action. Max 3 sentences total.\n"
            "- Use recent conversation and remembered customer facts when relevant; do not contradict ERP data.\n"
            + ("- Start with exactly: Hello Admin,\n" if is_admin else "- Do not use the customer's name in the greeting.\n")
        )
        if not is_admin:
            system_prompt += (
                "- The customer may ONLY see their own account data. "
                "Never mention other customers' names, ids, invoices, or orders.\n"
            )
        billing_hint = ""
        ml = message.lower()
        if any(w in ml for w in ("bill", "invoice", "highest", "largest", "total amount", "most expensive")):
            if is_admin:
                billing_hint = (
                    "\nFor billing/total/highest questions: use highest_order_global / highest_invoice_global "
                    "for cross-customer highs, or scoped fields when a specific customer is implied.\n"
                )
            else:
                billing_hint = (
                    "\nFor billing/total/highest questions: use highest_order, highest_invoice, "
                    "and orders_total_sum for THIS customer only. Ignore any global or other-account fields.\n"
                )
        user_prompt = (
            f"Customer question:\n{message}\n"
            f"{chat_history_block}"
            f"{memory_block}\n"
            f"Account and order facts (use silently, do not label):\n{erp_ctx_for_json(prompt_ctx, is_admin=is_admin)}\n"
            f"{billing_hint}\n"
            f"Help articles (use only if relevant, do not quote titles):\n{kb_context}"
        )
    answer, llm_source = await llm.answer(
        system_prompt,
        user_prompt,
        int(GUARDRAILS["max_output_tokens"]),
        message,
        intent_class,
        prompt_ctx,
        llm_mode,
        is_admin=is_admin,
    )
    cache.set(cache_key, answer)

    cost = _estimate_cost(system_prompt + user_prompt, answer)
    budget.add(cost)

    final = ChatResponse(
        answer=answer,
        confidence=round(confidence, 2),
        action="answered",
        est_cost_usd=round(cost, 6),
        llm_source=llm_source,
        sources_used=len(chunks),
    )
    if site_mode:
        final = _wrap_site(final)
    return await _finalize_chat(
        session_id=session_id,
        app_user_id=app_user_id,
        erp_uid=erp_uid,
        channel=channel,
        user_message=message,
        intent_class=intent_class,
        try_learn=not site_mode,
        erp_ctx=erp_ctx if not site_mode else None,
        sources_used=len(chunks),
        response=final,
    )


async def _build_health_payload() -> Dict[str, Any]:
    pool = get_pool()
    local: Dict[str, Any] = {
        "reachable": False,
        "model": LOCAL_LLM_MODEL,
        "model_ready": False,
    }
    try:
        async with asyncio.timeout(2.5):
            local = await llm.probe_local()
    except TimeoutError:
        local["error"] = "probe timed out"
    except Exception as exc:
        local["error"] = str(exc)

    feed_count: Optional[int] = 0
    feeds_ok = True
    if pool:
        try:
            async with asyncio.timeout(2.0):

                async def _count_feeds() -> int:
                    async with pool.connection() as conn:
                        async with conn.cursor() as cur:
                            await cur.execute(
                                "SELECT COUNT(*) FROM rag_feeds WHERE enabled = TRUE"
                            )
                            return int((await cur.fetchone())[0])

                feed_count = await _count_feeds()
        except Exception as exc:
            feeds_ok = False
            feed_count = None
            logger.debug("rag_feeds check skipped: %s", exc)

    from .embeddings import embeddings_configured
    from .rag_vector import chunk_count_conn, vector_index_ready

    vector_chunks = 0
    if pool and vector_index_ready():
        try:
            async with asyncio.timeout(3.0):

                async def _count_chunks() -> int:
                    async with pool.connection() as conn:
                        return await chunk_count_conn(conn)

                vector_chunks = await _count_chunks()
        except Exception as exc:
            logger.debug("vector chunk count skipped: %s", exc)

    retrieval = (
        f"{RAG_RETRIEVAL_MODE}_pgvector_fts"
        if vector_index_ready()
        else "postgres_fts"
    )

    return {
        "status": "ok",
        "database": database_ready(),
        "llm_api": llm.api_enabled,
        "llm_local": llm.local_enabled,
        "llm_order": LLM_ORDER,
        "local_model": LOCAL_LLM_MODEL,
        "local_ollama": local,
        "rag": {
            "retrieval": retrieval,
            "vector_enabled": RAG_VECTOR_ENABLED,
            "embeddings_configured": embeddings_configured(),
            "vector_chunks_indexed": vector_chunks,
            "feed_sync_enabled": RAG_FEED_SYNC_ENABLED,
            "learn_from_chat": LEARN_FROM_CHAT,
            "learn_customer_memory": LEARN_CUSTOMER_MEMORY,
            "chat_memory_in_prompt": CHAT_MEMORY_IN_PROMPT,
            "learn_expand_with_api": LEARN_EXPAND_WITH_API,
            "active_feeds": feed_count if feeds_ok else None,
            "feeds_table_ready": feeds_ok,
        },
    }


def _health_html(data: Dict[str, Any]) -> str:
    o = data.get("local_ollama") or {}
    rag = data.get("rag") or {}
    if not o and data.get("local_model"):
        gpu = f"{data['local_model']} (use ?full=1 to probe Ollama)"
    elif o.get("error"):
        gpu = str(o.get("error"))[:80]
    else:
        gpu = "Ready" if o.get("model_ready") else ("Online" if o.get("reachable") else "Offline")
    rows = [
        ("API", "ok" if data.get("status") == "ok" else "error"),
        ("Database", "connected" if data.get("database") else "not connected"),
        ("Groq API", "on" if data.get("llm_api") else "off"),
        ("Local LLM", f"{data.get('local_model', '')} — {gpu}"),
        ("RAG feeds", str(rag.get("active_feeds") if rag.get("feeds_table_ready") else "run migrate_rag_feeds.sql")),
        ("Learn from chat", "on" if rag.get("learn_from_chat") else "off"),
        ("Customer memory", "on" if rag.get("learn_customer_memory") else "off"),
        ("Vector RAG", f"{rag.get('vector_chunks_indexed', 0)} chunks" if rag.get("vector_enabled") else "off"),
    ]
    tr = "".join(
        f'<tr><td>{k}</td><td><span class="pill">{v}</span></td></tr>' for k, v in rows
    )
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Nexus Support — Status</title>
<style>
  body{{font-family:system-ui,sans-serif;background:#06080f;color:#e2e8f0;margin:0;padding:32px}}
  .card{{max-width:520px;margin:0 auto;background:rgba(15,23,42,.9);border:1px solid #334155;
    border-radius:16px;padding:28px;box-shadow:0 20px 50px rgba(0,0,0,.4)}}
  h1{{font-size:1.4rem;margin:0 0 8px}} p{{color:#94a3b8;font-size:14px}}
  table{{width:100%;margin-top:20px;border-collapse:collapse;font-size:14px}}
  td{{padding:10px 0;border-bottom:1px solid #1e293b}} td:first-child{{color:#94a3b8}}
  .pill{{background:#1e293b;padding:4px 10px;border-radius:8px;font-size:13px}}
  a{{color:#818cf8}} pre{{background:#0f172a;padding:12px;border-radius:8px;font-size:11px;
    overflow:auto;margin-top:16px}}
</style></head><body>
<div class="card">
  <h1>System status</h1>
  <p>API is running. <a href="/">Open chat</a> · <a href="/health?format=json">JSON</a></p>
  <table>{tr}</table>
  <pre>{json.dumps(data, indent=2)}</pre>
</div>
</body></html>"""


@app.get("/health")
async def health(
    request: Request,
    fmt: Optional[str] = Query(default=None, alias="format"),
    full: bool = Query(default=False),
) -> Any:
    if full:
        data = await _build_health_payload()
    else:
        local: Dict[str, Any] = {
            "backend": LOCAL_LLM_BACKEND,
            "reachable": False,
            "model_ready": False,
        }
        try:
            async with asyncio.timeout(4.0):
                local = await llm.probe_local()
        except TimeoutError:
            local["error"] = "probe timed out"
        except Exception as exc:
            local["error"] = str(exc)
        data = {
            "status": "ok",
            "database": database_ready(),
            "llm_api": llm.api_enabled,
            "llm_local": llm.local_enabled,
            "llm_order": LLM_ORDER,
            "local_model": LOCAL_LLM_MODEL,
            "local_backend": LOCAL_LLM_BACKEND,
            "native_configured": native_local_configured(),
            "local_ollama": local,
            "rag": {
                "feed_sync_enabled": RAG_FEED_SYNC_ENABLED,
                "learn_from_chat": LEARN_FROM_CHAT,
                "learn_customer_memory": LEARN_CUSTOMER_MEMORY,
                "chat_memory_in_prompt": CHAT_MEMORY_IN_PROMPT,
                "learn_expand_with_api": LEARN_EXPAND_WITH_API,
            },
            "hint": "Use /health?full=1 to load native GGUF on GPU",
        }
    accept = request.headers.get("accept", "")
    wants_html = "text/html" in accept and not accept.strip().startswith("application/json")
    if fmt == "json" or not wants_html:
        return JSONResponse(content=data)
    return HTMLResponse(content=_health_html(data) if full else _health_html(data))


@app.get("/")
def demo_ui() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/auth/login", response_model=LoginResponse)
async def auth_login(body: LoginRequest) -> LoginResponse:
    result = await login_user(body.username, body.password)
    u = result["user"]
    return LoginResponse(
        token=result["token"],
        expires_at=result["expires_at"],
        user=UserInfo(
            id=u["id"],
            username=u["username"],
            first_name=u["first_name"],
            role=u["role"],
            customer_id=u.get("customer_id"),
        ),
    )


@app.post("/auth/logout")
async def auth_logout(request: Request, user: Dict[str, Any] = Depends(require_user)) -> dict:
    auth = request.headers.get("Authorization", "")
    token = auth.replace("Bearer ", "").strip() if auth.startswith("Bearer ") else ""
    if token:
        await logout_user(token)
    return {"ok": True}


@app.get("/auth/me", response_model=UserInfo)
async def auth_me(user: Dict[str, Any] = Depends(require_user)) -> UserInfo:
    return UserInfo(
        id=user["id"],
        username=user["username"],
        first_name=user["first_name"],
        role=user["role"],
        customer_id=user.get("customer_id"),
    )


@app.post("/knowledge/reindex")
async def knowledge_reindex_vectors(
    user: Dict[str, Any] = Depends(require_ingest_role),
) -> Dict[str, Any]:
    """Re-chunk and embed all KB + RAG documents into Neon pgvector."""
    from .embeddings import embeddings_configured
    from .rag_vector import reindex_all_conn, vector_index_ready

    if not vector_index_ready():
        raise HTTPException(
            status_code=503,
            detail="Vector RAG disabled or EMBEDDING_API_KEY not set (OpenAI-compatible)",
        )
    if not embeddings_configured():
        raise HTTPException(status_code=503, detail="Set EMBEDDING_API_KEY for embeddings")
    async with db_connection(timeout=180.0) as conn:
        stats = await reindex_all_conn(conn)
    return {"ok": True, "stats": stats}


@app.get("/knowledge")
async def knowledge_list(
    user: Dict[str, Any] = Depends(require_ingest_role),
) -> List[Dict[str, Any]]:
    pool = _require_pool()
    return await list_rag_documents(pool)


@app.post("/knowledge/text")
async def knowledge_add_text(
    body: KnowledgeTextRequest,
    user: Dict[str, Any] = Depends(require_ingest_role),
) -> Dict[str, Any]:
    pool = _require_pool()
    doc = await insert_rag_document(
        pool,
        owner_user_id=user["id"],
        title=body.title,
        body=body.body,
        source_type="text",
        source_ref=None,
        category=body.category,
    )
    return {"ok": True, "document": doc}


@app.post("/knowledge/file")
async def knowledge_upload_file(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    user: Dict[str, Any] = Depends(require_ingest_role),
) -> Dict[str, Any]:
    pool = _require_pool()
    data = await file.read()
    if len(data) > 2_000_000:
        raise HTTPException(status_code=400, detail="File too large (max 2MB)")
    try:
        text = extract_text_from_bytes(file.filename or "upload.txt", data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    doc_title = normalize_title(title, file.filename or "Uploaded file")
    doc = await insert_rag_document(
        pool,
        owner_user_id=user["id"],
        title=doc_title,
        body=text,
        source_type="file",
        source_ref=file.filename,
    )
    return {"ok": True, "document": doc}


@app.post("/knowledge/api-feed")
async def knowledge_api_feed(
    body: KnowledgeApiFeedRequest,
    user: Dict[str, Any] = Depends(require_ingest_role),
) -> Dict[str, Any]:
    pool = _require_pool()
    url = str(body.url)
    try:
        text = await fetch_api_feed(url)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not fetch URL: {exc}") from exc
    if not text.strip():
        raise HTTPException(status_code=400, detail="URL returned empty content")
    doc_title = normalize_title(body.title, url)
    doc = await insert_rag_document(
        pool,
        owner_user_id=user["id"],
        title=doc_title,
        body=text,
        source_type="api",
        source_ref=url,
    )
    return {"ok": True, "document": doc}


@app.get("/knowledge/site-feed")
async def knowledge_site_feed() -> JSONResponse:
    """Public JSON feed polled from http://localhost:8000/ for automatic KB indexing."""
    return JSONResponse(json.loads(SITE_FEED_JSON))


@app.get("/knowledge/demo-feed")
async def knowledge_demo_feed() -> JSONResponse:
    """Public sample JSON feed for testing Live feed sync (reachable from this server)."""
    return JSONResponse(
        {
            "title": "ERP Help API (demo)",
            "topics": [
                {
                    "id": "invoices",
                    "title": "Invoices and billing",
                    "body": "Download invoices under Billing > Invoices. Unpaid invoices show status and due date.",
                },
                {
                    "id": "orders",
                    "title": "Order status",
                    "body": "Track orders under Orders. Status values include pending, processing, shipped, and delivered.",
                },
                {
                    "id": "tickets",
                    "title": "Support tickets",
                    "body": "Create tickets from Support or Help Center. Open tickets appear in your dashboard.",
                },
            ],
        }
    )


@app.get("/knowledge/feeds")
async def knowledge_list_feeds(user: Dict[str, Any] = Depends(require_ingest_role)) -> List[Dict[str, Any]]:
    pool = _require_pool()
    return await list_rag_feeds(pool)


@app.post("/knowledge/feeds")
async def knowledge_register_feed(
    body: KnowledgeFeedRegisterRequest,
    user: Dict[str, Any] = Depends(require_ingest_role),
) -> Dict[str, Any]:
    """Register an API URL to poll; updates the same RAG document on each sync."""
    pool = _require_pool()
    feed = await insert_rag_feed(
        pool,
        url=str(body.url),
        title=body.title,
        poll_interval_minutes=body.poll_interval_minutes,
        created_by=user["id"],
    )
    sync_result = None
    if body.sync_now:
        row = await get_rag_feed(pool, feed["id"])
        if row:
            sync_result = await sync_feed(pool, {**row, "created_by": user["id"]})
    return {"ok": True, "feed": feed, "sync": sync_result}


@app.post("/knowledge/feeds/{feed_id}/sync")
async def knowledge_sync_feed(
    feed_id: int,
    user: Dict[str, Any] = Depends(require_ingest_role),
) -> Dict[str, Any]:
    pool = _require_pool()
    feed = await get_rag_feed(pool, feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
    result = await sync_feed(pool, {**feed, "created_by": user["id"]})
    return {"ok": result.get("ok", False), **result}


@app.post("/knowledge/sync-all")
async def knowledge_sync_all(user: Dict[str, Any] = Depends(require_ingest_role)) -> Dict[str, Any]:
    pool = _require_pool()
    results = await sync_all_enabled_feeds(pool)
    return {"ok": True, "synced": len(results), "results": results}


@app.post("/knowledge/webhook")
async def knowledge_webhook(
    body: KnowledgeWebhookRequest,
    x_webhook_key: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    """External systems push docs in real time (set KNOWLEDGE_WEBHOOK_KEY in .env)."""
    if KNOWLEDGE_WEBHOOK_KEY and x_webhook_key != KNOWLEDGE_WEBHOOK_KEY:
        raise HTTPException(status_code=401, detail="Invalid webhook key")
    pool = _require_pool()
    doc = await insert_rag_document(
        pool,
        owner_user_id=None,
        title=body.title,
        body=body.body,
        source_type="webhook",
        source_ref="webhook",
        category=body.category,
    )
    return {"ok": True, "document": doc, "message": "Indexed for immediate RAG retrieval"}


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
async def erp_customer(customer_id: int, user: Dict[str, Any] = Depends(require_user)) -> Dict[str, Any]:
    assert_customer_record_access(user, customer_id)
    pool = _require_pool()
    row = await get_customer_row(pool, customer_id)
    if not row:
        raise HTTPException(status_code=404, detail="Customer not found")
    return row


@app.get("/erp/customers/{customer_id}/orders")
async def erp_customer_orders(
    customer_id: int, user: Dict[str, Any] = Depends(require_user)
) -> List[Dict[str, Any]]:
    assert_customer_record_access(user, customer_id)
    pool = _require_pool()
    return await list_orders_for_customer(pool, customer_id)


@app.get("/erp/orders/{order_id}")
async def erp_order(order_id: int, user: Dict[str, Any] = Depends(require_user)) -> Dict[str, Any]:
    pool = _require_pool()
    detail = await get_order_detail(pool, order_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Order not found")
    assert_order_record_access(user, detail)
    return detail


@app.get("/erp/invoices/unpaid")
async def erp_unpaid_invoices(
    user: Dict[str, Any] = Depends(require_user),
) -> List[Dict[str, Any]]:
    pool = _require_pool()
    return await list_unpaid_invoices(pool, erp_user_id_for(user))


@app.get("/chat/sessions/{session_id}/messages")
async def chat_session_messages(
    session_id: str,
    user: Dict[str, Any] = Depends(require_user),
) -> List[Dict[str, Any]]:
    if user["role"] not in ("admin", "agent"):
        raise HTTPException(status_code=403, detail="Only admin or agent can view chat history")
    async with db_connection(timeout=12.0) as conn:
        return await list_chat_messages_conn(conn, session_id)


@app.post("/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    user: Optional[Dict[str, Any]] = Depends(resolve_user),
) -> ChatResponse:
    if user is not None:
        erp_uid = erp_user_id_for(user)
    elif req.user_id:
        erp_uid = req.user_id
    else:
        raise HTTPException(status_code=401, detail="Login required or provide user_id for legacy mode")
    return await _run_chat(
        erp_uid=erp_uid,
        channel=req.channel,
        message=req.message,
        llm_mode=req.llm_mode,
        session_id=req.session_id,
        app_user_id=user["id"] if user else None,
    )


def _verify_public_chat_key(x_site_api_key: Optional[str]) -> None:
    if not SITE_BOT_ENABLED:
        raise HTTPException(status_code=503, detail="Public site chat is disabled")
    if PUBLIC_CHAT_API_KEY:
        if not x_site_api_key or x_site_api_key != PUBLIC_CHAT_API_KEY:
            raise HTTPException(status_code=401, detail="Invalid or missing X-Site-Api-Key header")


@app.post("/chat/public", response_model=ChatResponse)
async def chat_public(
    req: PublicChatRequest,
    x_site_api_key: Optional[str] = Header(default=None, alias="X-Site-Api-Key"),
) -> ChatResponse:
    """Marketing-site widget (e.g. infigosolutions.com) — no login; RAG from company KB."""
    _verify_public_chat_key(x_site_api_key)
    visitor: Dict[str, str] = {}
    if req.visitor_name:
        visitor["name"] = req.visitor_name.strip()
    if req.visitor_email:
        visitor["email"] = req.visitor_email.strip()
    return await _run_chat(
        erp_uid=site_public_erp_uid(),
        channel="site",
        message=req.message,
        llm_mode=req.llm_mode,
        session_id=req.session_id,
        app_user_id=None,
        site_mode=True,
        site_visitor=visitor or None,
    )


@app.get("/integrations/site/status")
async def site_integration_status() -> dict:
    return {
        "site_bot_enabled": SITE_BOT_ENABLED,
        "public_chat_key_required": bool(PUBLIC_CHAT_API_KEY),
        "company": SITE_COMPANY_NAME,
        "contact_email_configured": bool(SITE_CONTACT_EMAIL),
        "booking_url_configured": bool(SITE_BOOKING_URL),
        "proposal_url": SITE_PROPOSAL_URL or None,
        "cors_origins": _cors_origins,
        "embed_script": "/static/infigo-embed.js",
        "chat_endpoint": "/chat/public",
        "database": database_ready(),
    }


@app.get("/integrations/whatsapp/status")
async def whatsapp_integration_status() -> dict:
    return {
        "whatsapp_send_configured": whatsapp_configured(),
        "verify_token_set": bool(WHATSAPP_VERIFY_TOKEN),
        "demo_erp_uid": WHATSAPP_DEMO_ERP_UID,
        "database": database_ready(),
        "webhook_url_hint": "/channels/whatsapp",
        "serverless": bool(__import__("os").getenv("VERCEL")),
    }


@app.get("/channels/whatsapp")
async def whatsapp_webhook_verify(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
) -> Response:
    challenge = verify_webhook(hub_mode, hub_verify_token, hub_challenge, WHATSAPP_VERIFY_TOKEN)
    if challenge is None:
        raise HTTPException(status_code=403, detail="Verification failed")
    return Response(content=challenge, media_type="text/plain")


@app.post("/channels/whatsapp")
async def whatsapp_webhook(request: Request) -> dict:
    raw = await request.body()
    if WHATSAPP_APP_SECRET and not validate_signature(raw, request.headers.get("X-Hub-Signature-256"), WHATSAPP_APP_SECRET):
        raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        body = json.loads(raw.decode("utf-8") if raw else "{}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    if is_legacy_test_payload(body):
        erp_uid = erp_uid_for_whatsapp_sender(str(body.get("from", "unknown")))
        text = str(body.get("message", ""))
        result = await _run_chat(erp_uid=erp_uid, channel="whatsapp", message=text, llm_mode="api")
        return {"reply": result.answer, "ticket_id": result.ticket_id, "action": result.action}

    replies: List[dict] = []
    for wa_from, msg_id, text, kind in extract_inbound_messages(body):
        if kind == "unsupported":
            hint = "Please send a text message. Voice notes and images are not supported in this demo."
            await mark_message_read(msg_id)
            sent = await send_text_message(to_wa_id=wa_from, body=hint)
            replies.append({"from": wa_from, "reply": hint, "sent": sent, "kind": "unsupported"})
            continue
        erp_uid = erp_uid_for_whatsapp_sender(wa_from)
        result = await _run_chat(erp_uid=erp_uid, channel="whatsapp", message=text, llm_mode="api")
        await mark_message_read(msg_id)
        sent = await send_text_message(to_wa_id=wa_from, body=result.answer)
        replies.append(
            {
                "from": wa_from,
                "erp_uid": erp_uid,
                "reply": result.answer,
                "sent": sent,
                "action": result.action,
                "ticket_id": result.ticket_id,
            }
        )
    return {"ok": True, "processed": len(replies), "replies": replies}


@app.post("/channels/slack")
async def slack_webhook(request: Request) -> dict:
    body = await request.json()
    event = body.get("event", {})
    user_id = event.get("user", "unknown")
    text = event.get("text", "")
    result = await _run_chat(erp_uid=user_id, channel="slack", message=text, llm_mode="auto")
    return {"text": result.answer, "metadata": {"action": result.action, "ticket_id": result.ticket_id}}
