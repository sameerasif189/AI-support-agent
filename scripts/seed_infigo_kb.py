#!/usr/bin/env python3
"""Load config/infigo_kb_seed.md into Neon RAG (run after DATABASE_URL is set)."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=True)

SEED_PATH = ROOT / "config" / "infigo_kb_seed.md"
TITLE = "Infigo Solutions — website knowledge (seed)"


async def main() -> None:
    from app.db import close_db_pool, init_db_pool
    from app.ingest import normalize_title
    from app.repositories import insert_rag_document
    from app.settings import DATABASE_URL

    if not DATABASE_URL:
        print("Set DATABASE_URL in .env first.")
        sys.exit(1)
    if not SEED_PATH.is_file():
        print(f"Missing {SEED_PATH}")
        sys.exit(1)
    body = SEED_PATH.read_text(encoding="utf-8")
    await init_db_pool()
    pool = __import__("app.db", fromlist=["get_pool"]).get_pool()
    if not pool:
        print("Could not open DB pool.")
        sys.exit(1)
    doc = await insert_rag_document(
        pool,
        owner_user_id=None,
        title=normalize_title(TITLE, "infigo_kb_seed.md"),
        body=body,
        source_type="text",
        source_ref=str(SEED_PATH),
        category="infigo",
    )
    print(f"OK: indexed document id={doc.get('id')} title={doc.get('title')}")
    try:
        from app.embeddings import embeddings_configured
        from app.rag_vector import reindex_all_conn
        from app.db_util import db_connection

        if embeddings_configured():
            async with db_connection(timeout=180.0) as conn:
                stats = await reindex_all_conn(conn)
            print(f"Vector reindex: {stats}")
        else:
            print("Tip: set EMBEDDING_API_KEY and run scripts/reindex_vector_rag.py for hybrid RAG.")
    except Exception as exc:
        print(f"Vector reindex skipped: {exc}")
    await close_db_pool()


if __name__ == "__main__":
    asyncio.run(main())
