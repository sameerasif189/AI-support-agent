"""Simple session auth: password equals user's first name (case-insensitive)."""

from __future__ import annotations

import asyncio
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .db_util import db_connection
from .access import erp_user_id_for, user_has_global_erp_access
from .repositories import (
    create_session_conn,
    delete_session_conn,
    get_user_by_username_conn,
    get_user_for_token_conn,
)
from .settings import DATABASE_URL

_bearer = HTTPBearer(auto_error=False)


def verify_password(first_name: str, password: str) -> bool:
    return password.strip().lower() == first_name.strip().lower()


async def login_user(username: str, password: str) -> Dict[str, Any]:
    if not DATABASE_URL:
        raise HTTPException(status_code=503, detail="Database not configured")
    try:
        async with db_connection(timeout=12.0) as conn:
            user = await get_user_by_username_conn(conn, username)
            if not user or not verify_password(user["first_name"], password):
                raise HTTPException(status_code=401, detail="Invalid username or password")
            token = secrets.token_urlsafe(32)
            expires = datetime.now(timezone.utc) + timedelta(hours=24)
            await create_session_conn(conn, token, user["id"], expires)
    except HTTPException:
        raise
    except asyncio.TimeoutError:
        raise HTTPException(status_code=503, detail="Database connection timed out. Retry in a few seconds.")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database error: {exc}") from exc
    return {
        "token": token,
        "expires_at": expires.isoformat(),
        "user": {
            "id": user["id"],
            "username": user["username"],
            "first_name": user["first_name"],
            "role": user["role"],
            "customer_id": user.get("customer_id"),
        },
    }


async def logout_user(token: str) -> None:
    if not DATABASE_URL:
        return
    try:
        async with db_connection(timeout=10.0) as conn:
            await delete_session_conn(conn, token)
    except Exception:
        return


async def resolve_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> Optional[Dict[str, Any]]:
    if credentials is None or not credentials.credentials:
        return None
    if not DATABASE_URL:
        return None
    try:
        async with db_connection(timeout=10.0) as conn:
            return await get_user_for_token_conn(conn, credentials.credentials)
    except Exception:
        return None


async def require_user(user: Optional[Dict[str, Any]] = Depends(resolve_user)) -> Dict[str, Any]:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login required. Use POST /auth/login (password = your first name).",
        )
    return user


async def require_ingest_role(user: Dict[str, Any] = Depends(require_user)) -> Dict[str, Any]:
    if user["role"] not in ("admin", "agent"):
        raise HTTPException(status_code=403, detail="Only admin or agent can add knowledge")
    return user


