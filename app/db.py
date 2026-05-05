"""Async Postgres connection pool (Neon). Skips initialization when DATABASE_URL is unset."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from .settings import DATABASE_URL

if TYPE_CHECKING:
    from psycopg_pool import AsyncConnectionPool

_pool: Optional["AsyncConnectionPool"] = None


async def init_db_pool() -> None:
    global _pool
    if not DATABASE_URL:
        return
    from psycopg_pool import AsyncConnectionPool

    _pool = AsyncConnectionPool(
        conninfo=DATABASE_URL,
        min_size=1,
        max_size=10,
        kwargs={"connect_timeout": 10},
        open=False,
    )
    await _pool.open()


async def close_db_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> Optional["AsyncConnectionPool"]:
    return _pool
