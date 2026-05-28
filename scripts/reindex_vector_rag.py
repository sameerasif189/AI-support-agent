#!/usr/bin/env python3
"""Chunk + embed all KB and RAG documents into Neon pgvector (knowledge_chunks).

Usage:
  set DATABASE_URL=...
  set EMBEDDING_API_KEY=sk-...   # OpenAI or compatible
  python scripts/reindex_vector_rag.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from app.db_util import db_connection
from app.embeddings import embeddings_configured
from app.rag_vector import reindex_all_conn, vector_index_ready


async def main() -> None:
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is not set")
    if not vector_index_ready():
        raise SystemExit(
            "Vector RAG not ready: set RAG_VECTOR_ENABLED=true and EMBEDDING_API_KEY "
            "(OpenAI text-embedding-3-small). Groq chat keys do not provide embeddings."
        )
    if not embeddings_configured():
        raise SystemExit("EMBEDDING_API_KEY is missing")

    async with db_connection(timeout=120.0) as conn:
        stats = await reindex_all_conn(conn)
    print(
        f"Reindexed {stats['kb_articles']} kb_articles + {stats['rag_documents']} rag_documents "
        f"-> {stats['chunks']} chunks in knowledge_chunks"
    )


if __name__ == "__main__":
    asyncio.run(main())
