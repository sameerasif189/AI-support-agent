"""ERP and prompt access control: customers see only their own data; admin sees all."""

from __future__ import annotations

import copy
import json
import re
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from .models import RetrievalChunk

_ACCOUNT_SPECIFIC_KB = re.compile(
    r"\bORD-\d+\b|\bINV-\d{4,}\b|\bcustomer\s+id\s+\d+|\bfor\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}\s*\(",
    re.I,
)
_BILLING_LOOKUP = re.compile(
    r"\b(highest|largest|most expensive|biggest)\b.*\b(bill|invoice|order|charge)\b|"
    r"\b(bill|invoice)\b.*\b(highest|largest|most expensive|biggest)\b|"
    r"\bwhat is my (bill|invoice)\b",
    re.I,
)


def user_has_global_erp_access(user: Dict[str, Any]) -> bool:
    return user.get("role") == "admin"


def erp_user_id_for(user: Dict[str, Any]) -> str:
    if user["role"] == "admin":
        return "admin"
    cid = user.get("customer_id")
    if cid is not None:
        return str(cid)
    if user["role"] == "agent":
        return f"agent:{user['id']}"
    return str(user["id"])


def assert_customer_record_access(user: Dict[str, Any], customer_id: int) -> None:
    if user_has_global_erp_access(user):
        return
    if user.get("role") == "customer":
        if user.get("customer_id") == customer_id:
            return
        raise HTTPException(status_code=403, detail="You can only access your own account.")
    raise HTTPException(
        status_code=403,
        detail="Only administrators can browse other customers' records.",
    )


def assert_order_record_access(user: Dict[str, Any], order: Dict[str, Any]) -> None:
    assert_customer_record_access(user, int(order["customer_id"]))


def filter_erp_ctx_for_prompt(erp_ctx: Dict[str, Any], *, is_admin: bool) -> Dict[str, Any]:
    """Remove cross-customer / global fields before sending context to the LLM."""
    if is_admin:
        return erp_ctx
    ctx = copy.deepcopy(erp_ctx)
    for key in (
        "highest_order_global",
        "highest_invoice_global",
        "global_totals",
        "recent_orders",
    ):
        ctx.pop(key, None)
    if ctx.get("scope") == "global":
        ctx.pop("scope", None)
    for blob_key in ("highest_order", "highest_invoice", "last_invoice"):
        blob = ctx.get(blob_key)
        if isinstance(blob, dict):
            blob.pop("customer_name", None)
            blob.pop("customer_id", None)
    return ctx


def erp_ctx_for_json(erp_ctx: Dict[str, Any], *, is_admin: bool) -> str:
    return json.dumps(filter_erp_ctx_for_prompt(erp_ctx, is_admin=is_admin), default=str)


def is_account_specific_text(text: str) -> bool:
    return bool(_ACCOUNT_SPECIFIC_KB.search(text or ""))


def is_personal_billing_query(message: str) -> bool:
    return bool(_BILLING_LOOKUP.search(message or ""))


def customer_allowed_order_refs(erp_ctx: Dict[str, Any]) -> set[str]:
    refs: set[str] = set()
    for key in ("highest_order", "highest_invoice", "last_invoice"):
        blob = erp_ctx.get(key)
        if isinstance(blob, dict):
            for field in ("order_number", "invoice_number"):
                val = blob.get(field)
                if val:
                    refs.add(str(val))
    for row in erp_ctx.get("recent_orders") or []:
        if isinstance(row, dict) and row.get("order_number"):
            refs.add(str(row["order_number"]))
    last = erp_ctx.get("last_order_id")
    if last:
        refs.add(str(last))
    return refs


def filter_kb_chunks_for_customer(
    chunks: List[RetrievalChunk],
    *,
    erp_ctx: Dict[str, Any],
    message: str,
    intent_class: str,
) -> List[RetrievalChunk]:
    """Drop KB snippets that leak another account's orders/invoices (e.g. learned admin chats)."""
    if intent_class == "erp_lookup" and is_personal_billing_query(message):
        return []
    allowed = customer_allowed_order_refs(erp_ctx)
    kept: List[RetrievalChunk] = []
    for chunk in chunks:
        text = chunk.text or ""
        if not is_account_specific_text(text):
            kept.append(chunk)
            continue
        refs = set(re.findall(r"\bORD-\d+\b", text, flags=re.I))
        refs |= {m.upper() for m in re.findall(r"\bINV-\d+\b", text, flags=re.I)}
        if refs and refs.issubset({r.upper() for r in allowed}):
            kept.append(chunk)
    return kept


def format_customer_billing_answer(erp_ctx: Dict[str, Any]) -> Optional[str]:
    """Deterministic scoped answer for 'my highest bill' style questions."""
    hi = erp_ctx.get("highest_invoice")
    if isinstance(hi, dict) and hi.get("amount") is not None:
        inv = hi.get("invoice_number") or "your latest invoice"
        ord_num = hi.get("order_number") or ""
        ord_bit = f", linked to order {ord_num}" if ord_num else ""
        return (
            f"Your highest bill is ${float(hi['amount']):,.2f} "
            f"({inv}{ord_bit}). Open Billing → Invoices for the PDF."
        )
    ho = erp_ctx.get("highest_order")
    if isinstance(ho, dict) and ho.get("total") is not None:
        return (
            f"Your largest order is {ho.get('order_number')} "
            f"at ${float(ho['total']):,.2f}. Open Orders for line items and status."
        )
    return None
