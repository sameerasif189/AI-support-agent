-- Lean ERP synthetic schema for Neon Postgres
-- Run: psql "$DATABASE_URL" -f scripts/init_schema.sql

BEGIN;

DROP TABLE IF EXISTS chat_messages CASCADE;
DROP TABLE IF EXISTS chat_sessions CASCADE;
DROP TABLE IF EXISTS app_sessions CASCADE;
DROP TABLE IF EXISTS rag_feeds CASCADE;
DROP TABLE IF EXISTS rag_documents CASCADE;
DROP TABLE IF EXISTS app_users CASCADE;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS invoices CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS support_tickets CASCADE;
DROP TABLE IF EXISTS kb_articles CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS customers CASCADE;

CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    tier VARCHAR(32) NOT NULL DEFAULT 'starter',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    category VARCHAR(64) NOT NULL,
    price NUMERIC(12, 2) NOT NULL CHECK (price >= 0)
);

CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers (id) ON DELETE CASCADE,
    order_number VARCHAR(32) NOT NULL UNIQUE,
    status VARCHAR(32) NOT NULL,
    total NUMERIC(12, 2) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders (id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products (id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(12, 2) NOT NULL CHECK (unit_price >= 0)
);

CREATE TABLE invoices (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders (id) ON DELETE CASCADE,
    invoice_number VARCHAR(32) NOT NULL UNIQUE,
    status VARCHAR(32) NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    due_date DATE NOT NULL
);

CREATE TABLE support_tickets (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers (id) ON DELETE CASCADE,
    subject VARCHAR(300) NOT NULL,
    status VARCHAR(32) NOT NULL,
    category VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE kb_articles (
    id SERIAL PRIMARY KEY,
    title VARCHAR(300) NOT NULL,
    body TEXT NOT NULL,
    category VARCHAR(64) NOT NULL
);

CREATE INDEX idx_orders_customer ON orders (customer_id);
CREATE INDEX idx_orders_created ON orders (created_at DESC);
CREATE INDEX idx_order_items_order ON order_items (order_id);
CREATE INDEX idx_invoices_order ON invoices (order_id);
CREATE INDEX idx_tickets_customer ON support_tickets (customer_id);
CREATE INDEX idx_kb_category ON kb_articles (category);

-- Native Postgres full-text RAG over KB (title + body); auto-updates when rows change
ALTER TABLE kb_articles ADD COLUMN search_vector tsvector
  GENERATED ALWAYS AS (to_tsvector('english', coalesce(title, '') || ' ' || coalesce(body, ''))) STORED;
CREATE INDEX idx_kb_search_vector ON kb_articles USING GIN (search_vector);

CREATE TABLE app_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    first_name VARCHAR(100) NOT NULL,
    role VARCHAR(32) NOT NULL CHECK (role IN ('admin', 'agent', 'customer')),
    customer_id INTEGER REFERENCES customers (id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE app_sessions (
    token VARCHAR(64) PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES app_users (id) ON DELETE CASCADE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_app_sessions_user ON app_sessions (user_id);
CREATE INDEX idx_app_sessions_expires ON app_sessions (expires_at);

CREATE TABLE rag_documents (
    id SERIAL PRIMARY KEY,
    owner_user_id INTEGER REFERENCES app_users (id) ON DELETE SET NULL,
    title VARCHAR(300) NOT NULL,
    body TEXT NOT NULL,
    source_type VARCHAR(32) NOT NULL CHECK (source_type IN ('text', 'file', 'api', 'feed', 'learned', 'webhook')),
    source_ref VARCHAR(500),
    category VARCHAR(64) NOT NULL DEFAULT 'user',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_rag_documents_owner ON rag_documents (owner_user_id);
CREATE INDEX idx_rag_documents_created ON rag_documents (created_at DESC);

ALTER TABLE rag_documents ADD COLUMN search_vector tsvector
  GENERATED ALWAYS AS (to_tsvector('english', coalesce(title, '') || ' ' || coalesce(body, ''))) STORED;
CREATE INDEX idx_rag_search_vector ON rag_documents USING GIN (search_vector);

CREATE TABLE rag_feeds (
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

CREATE INDEX idx_rag_feeds_enabled ON rag_feeds (enabled) WHERE enabled = TRUE;

CREATE TABLE chat_sessions (
    id VARCHAR(36) PRIMARY KEY,
    user_id INTEGER REFERENCES app_users (id) ON DELETE SET NULL,
    erp_uid VARCHAR(64) NOT NULL,
    channel VARCHAR(32) NOT NULL DEFAULT 'web',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_chat_sessions_user ON chat_sessions (user_id);
CREATE INDEX idx_chat_sessions_updated ON chat_sessions (updated_at DESC);

CREATE TABLE chat_messages (
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

CREATE INDEX idx_chat_messages_session ON chat_messages (session_id, created_at);

CREATE TABLE customer_memory (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers (id) ON DELETE CASCADE,
    app_user_id INTEGER REFERENCES app_users (id) ON DELETE SET NULL,
    memory_key VARCHAR(48) NOT NULL,
    category VARCHAR(32) NOT NULL DEFAULT 'note'
        CHECK (category IN ('preference', 'issue', 'note', 'interaction')),
    fact TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0.85,
    source_ref VARCHAR(120),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (customer_id, memory_key)
);

CREATE INDEX idx_customer_memory_customer ON customer_memory (customer_id);
CREATE INDEX idx_customer_memory_updated ON customer_memory (customer_id, updated_at DESC);

ALTER TABLE customer_memory ADD COLUMN search_vector tsvector
  GENERATED ALWAYS AS (to_tsvector('english', coalesce(fact, ''))) STORED;
CREATE INDEX idx_customer_memory_search ON customer_memory USING GIN (search_vector);

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE knowledge_chunks (
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

CREATE INDEX idx_knowledge_chunks_source ON knowledge_chunks (source_table, source_id);
CREATE INDEX idx_knowledge_chunks_embedding ON knowledge_chunks USING hnsw (embedding vector_cosine_ops);

COMMIT;
