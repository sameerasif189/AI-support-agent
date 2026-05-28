-- Auth + user RAG tables (run once on existing Neon DBs)
-- psql "$DATABASE_URL" -f scripts/migrate_auth_rag.sql

BEGIN;

CREATE TABLE IF NOT EXISTS app_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    first_name VARCHAR(100) NOT NULL,
    role VARCHAR(32) NOT NULL CHECK (role IN ('admin', 'agent', 'customer')),
    customer_id INTEGER REFERENCES customers (id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS app_sessions (
    token VARCHAR(64) PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES app_users (id) ON DELETE CASCADE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_app_sessions_user ON app_sessions (user_id);
CREATE INDEX IF NOT EXISTS idx_app_sessions_expires ON app_sessions (expires_at);

CREATE TABLE IF NOT EXISTS rag_documents (
    id SERIAL PRIMARY KEY,
    owner_user_id INTEGER REFERENCES app_users (id) ON DELETE SET NULL,
    title VARCHAR(300) NOT NULL,
    body TEXT NOT NULL,
    source_type VARCHAR(32) NOT NULL CHECK (source_type IN ('text', 'file', 'api')),
    source_ref VARCHAR(500),
    category VARCHAR(64) NOT NULL DEFAULT 'user',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rag_documents_owner ON rag_documents (owner_user_id);
CREATE INDEX IF NOT EXISTS idx_rag_documents_created ON rag_documents (created_at DESC);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'rag_documents' AND column_name = 'search_vector'
    ) THEN
        ALTER TABLE rag_documents ADD COLUMN search_vector tsvector
          GENERATED ALWAYS AS (to_tsvector('english', coalesce(title, '') || ' ' || coalesce(body, ''))) STORED;
        CREATE INDEX idx_rag_search_vector ON rag_documents USING GIN (search_vector);
    END IF;
END $$;

COMMIT;
