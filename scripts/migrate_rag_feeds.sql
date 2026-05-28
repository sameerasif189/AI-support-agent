-- API feeds + chat learning for RAG (run on existing DBs)
-- psql "$DATABASE_URL" -f scripts/migrate_rag_feeds.sql

BEGIN;

ALTER TABLE rag_documents DROP CONSTRAINT IF EXISTS rag_documents_source_type_check;
ALTER TABLE rag_documents ADD CONSTRAINT rag_documents_source_type_check
  CHECK (source_type IN ('text', 'file', 'api', 'feed', 'learned', 'webhook'));

CREATE TABLE IF NOT EXISTS rag_feeds (
    id SERIAL PRIMARY KEY,
    url VARCHAR(500) NOT NULL,
    title VARCHAR(300) NOT NULL,
    poll_interval_minutes INTEGER NOT NULL DEFAULT 60 CHECK (poll_interval_minutes >= 5),
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    document_id INTEGER REFERENCES rag_documents (id) ON DELETE SET NULL,
    last_synced_at TIMESTAMPTZ,
    last_error TEXT,
    created_by INTEGER REFERENCES app_users (id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rag_feeds_enabled ON rag_feeds (enabled) WHERE enabled = TRUE;

COMMIT;
