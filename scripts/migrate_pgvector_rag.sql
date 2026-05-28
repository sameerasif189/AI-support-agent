-- Full vector RAG on Neon: pgvector + chunked embeddings (run once per database)
-- psql "$DATABASE_URL" -f scripts/migrate_pgvector_rag.sql

BEGIN;

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id SERIAL PRIMARY KEY,
    source_table VARCHAR(32) NOT NULL CHECK (source_table IN ('kb_articles', 'rag_documents')),
    source_id INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    title_hint VARCHAR(300) NOT NULL DEFAULT '',
    content TEXT NOT NULL,
    token_estimate INTEGER NOT NULL DEFAULT 0,
    embedding vector(1536) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (source_table, source_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_source
    ON knowledge_chunks (source_table, source_id);

CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_embedding
    ON knowledge_chunks USING hnsw (embedding vector_cosine_ops);

COMMIT;
