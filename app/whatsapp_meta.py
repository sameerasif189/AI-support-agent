"""Meta WhatsApp Cloud API: webhook verify, inbound parse, outbound send."""

from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any, Dict, List, Optional, Tuple

import httpx

from .settings import (
    WHATSAPP_ACCESS_TOKEN,
    WHATSAPP_API_VERSION,
    WHATSAPP_APP_SECRET,
    WHATSAPP_DEMO_ERP_UID,
    WHATSAPP_PHONE_NUMBER_ID,
)

logger = logging.getLogger(__name__)


def verify_webhook(mode: Optional[str], token: Optional[str], challenge: Optional[str], expected_token: str) -> Optional[str]:
    if mode == "subscribe" and token and expected_token and token == expected_token:
        return challenge or ""
    return None


def validate_signature(raw_body: bytes, signature_header: Optional[str], app_secret: str) -> bool:
    if not app_secret or not signature_header:
        return True
    if not signature_header.startswith("sha256="):
        return False
    expected = signature_header[7:]
    digest = hmac.new(app_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, expected)


def erp_uid_for_whatsapp_sender(wa_from: str) -> str:
    """Map WhatsApp phone to ERP user id for demo (seeded customers are numeric ids)."""
    raw = str(wa_from).strip()
    if raw.isdigit() and int(raw) <= 9999:
        return raw
    demo = (WHATSAPP_DEMO_ERP_UID or "").strip()
    if demo:
        return demo
    return raw


def extract_inbound_messages(payload: Dict[str, Any]) -> List[Tuple[str, str, str, str]]:
    """Return list of (wa_from, message_id, text, kind) — kind is text or unsupported."""
    out: List[Tuple[str, str, str, str]] = []
    if payload.get("object") != "whatsapp_business_account":
        return out
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            value = change.get("value") or {}
            for msg in value.get("messages") or []:
                wa_from = str(msg.get("from") or "").strip()
                msg_id = str(msg.get("id") or "")
                if not wa_from:
                    continue
                mtype = str(msg.get("type") or "")
                if mtype == "text":
                    text_obj = msg.get("text") or {}
                    body = (text_obj.get("body") or "").strip()
                    if body:
                        out.append((wa_from, msg_id, body, "text"))
                else:
                    out.append((wa_from, msg_id, "", "unsupported"))
    return out


def extract_inbound_text_messages(payload: Dict[str, Any]) -> List[Tuple[str, str, str]]:
    return [(a, b, c) for a, b, c, k in extract_inbound_messages(payload) if k == "text"]


def is_legacy_test_payload(payload: Dict[str, Any]) -> bool:
    return bool(payload.get("from")) and "message" in payload


def whatsapp_configured() -> bool:
    return bool(WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID)


async def mark_message_read(message_id: str) -> None:
    if not whatsapp_configured() or not message_id:
        return
    url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                url,
                headers={"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"},
                json=payload,
            )
    except Exception as exc:
        logger.debug("WhatsApp mark read skipped: %s", exc)


async def send_text_message(*, to_wa_id: str, body: str) -> bool:
    if not whatsapp_configured():
        logger.warning("WhatsApp send skipped: WHATSAPP_ACCESS_TOKEN or WHATSAPP_PHONE_NUMBER_ID not set")
        return False
    url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to_wa_id,
        "type": "text",
        "text": {"body": body[:4096]},
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"},
                json=payload,
            )
        if resp.status_code >= 400:
            logger.warning("WhatsApp send failed %s: %s", resp.status_code, resp.text[:500])
            return False
        return True
    except Exception as exc:
        logger.warning("WhatsApp send error: %s", exc)
        return False
