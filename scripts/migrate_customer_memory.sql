-- Per-customer memory (preferences, resolved issues) + FTS for RAG at chat time
BEGIN;

CREATE TABLE IF NOT EXISTS customer_memory (
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

CREATE INDEX IF NOT EXISTS idx_customer_memory_customer ON customer_memory (customer_id);
CREATE INDEX IF NOT EXISTS idx_customer_memory_updated ON customer_memory (customer_id, updated_at DESC);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'customer_memory' AND column_name = 'search_vector'
    ) THEN
        ALTER TABLE customer_memory ADD COLUMN search_vector tsvector
            GENERATED ALWAYS AS (to_tsvector('english', coalesce(fact, ''))) STORED;
        CREATE INDEX idx_customer_memory_search ON customer_memory USING GIN (search_vector);
    END IF;
END $$;

COMMIT;
