-- Chat history (separate from auth sessions) + link to learned RAG docs
-- Run: python scripts/apply_sql.py scripts/migrate_chat_history.sql

BEGIN;

CREATE TABLE IF NOT EXISTS chat_sessions (
    id VARCHAR(36) PRIMARY KEY,
    user_id INTEGER REFERENCES app_users (id) ON DELETE SET NULL,
    erp_uid VARCHAR(64) NOT NULL,
    channel VARCHAR(32) NOT NULL DEFAULT 'web',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions (user_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated ON chat_sessions (updated_at DESC);

CREATE TABLE IF NOT EXISTS chat_messages (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL REFERENCES chat_sessions (id) ON DELETE CASCADE,
    role VARCHAR(16) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    llm_source VARCHAR(32),
    confidence REAL,
    intent_class VARCHAR(64),
    sources_used INTEGER DEFAULT 0,
    rag_document_id INTEGER REFERENCES rag_documents (id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages (session_id, created_at);

COMMIT;
