-- Add full-text search column for RAG over kb_articles (safe on existing Neon DBs).
-- Run: psql "$DATABASE_URL" -f scripts/migrate_kb_rag_fts.sql

BEGIN;

ALTER TABLE kb_articles ADD COLUMN IF NOT EXISTS search_vector tsvector
  GENERATED ALWAYS AS (to_tsvector('english', coalesce(title, '') || ' ' || coalesce(body, ''))) STORED;

CREATE INDEX IF NOT EXISTS idx_kb_search_vector ON kb_articles USING GIN (search_vector);

COMMIT;
