# Lean ERP AI Support Agent

Budget-controlled AI support backend for an existing ERP website with web, WhatsApp, and Slack channels. The lean stack uses **Neon Postgres** (synthetic ERP + KB data), a **free Groq** OpenAI-compatible LLM, and optional **Vercel** deployment.

## What is implemented

- Intent policy and escalation guardrails
- **Full RAG on Neon**: chunking → OpenAI-compatible embeddings → **pgvector** (`knowledge_chunks`) → hybrid vector + FTS retrieval at chat time; customer memory + ERP SQL unchanged
- KB retrieval fallback: token overlap if DB/vector unavailable; static fallback if `DATABASE_URL` is unset
- ERP context from linked tables: customers, orders, order_items, products, invoices, support_tickets
- LLM routing (Groq or any OpenAI-compatible API) with local fallback when no API key
- Answer caching and monthly budget tracking
- Channel endpoints for web, WhatsApp, and Slack
- UAT checklist and deployment runbook

## Project structure

- `app/main.py`: FastAPI app, `/chat`, channel webhooks, `/erp/*` inspection routes
- `app/services.py`: intent router, retriever, ERP client, cache, LLM, budget tracker
- `app/db.py`: async Neon connection pool
- `app/repositories.py`: SQL access (parameterized)
- `scripts/init_schema.sql`: 7 linked ERP tables
- `scripts/seed_db.py`: ~270 deterministic synthetic rows
- `config/guardrails.json`: token and budget limits
- `config/intents_policy.json`: intent classes and sensitive keywords
- `index.py` + `vercel.json`: Vercel serverless entry (root FastAPI ASGI)
- `docs/`: runbook and UAT checklist

## Database (Neon)

1. Create a Neon project and copy the **pooled** connection string (`…pooler.neon.tech`). Add `?sslmode=require` if not present.
2. Apply schema:

   ```bash
   psql "$DATABASE_URL" -f scripts/init_schema.sql
   ```

   Existing databases created before the KB RAG column was added should run once:

   ```bash
   psql "$DATABASE_URL" -f scripts/migrate_kb_rag_fts.sql
   psql "$DATABASE_URL" -f scripts/migrate_customer_memory.sql
   psql "$DATABASE_URL" -f scripts/migrate_pgvector_rag.sql
   ```

3. Set **embedding** credentials (Groq does not provide embeddings; use OpenAI or compatible):

   ```env
   EMBEDDING_API_KEY=sk-...
   EMBEDDING_MODEL=text-embedding-3-small
   ```

4. Seed synthetic data:

   ```bash
   set DATABASE_URL=postgresql://...
   python scripts/seed_db.py
   python scripts/reindex_vector_rag.py
   ```

Tables: `customers` (25), `products` (30), `orders` (40), `order_items` (~80+), `invoices` (40), `support_tickets` (30), `kb_articles` (25).

## Environment variables

Copy `.env.example` to `.env`.

| Variable        | Purpose                                      |
| --------------- | -------------------------------------------- |
| `DATABASE_URL`  | Neon Postgres (pooled URL for serverless)   |
| `LLM_API_BASE`  | e.g. `https://api.groq.com/openai/v1`        |
| `LLM_API_KEY`   | Groq API key                                 |
| `LLM_MODEL`     | e.g. `llama-3.1-8b-instant`                  |

Without `DATABASE_URL`, ERP + KB use built-in stubs so the API still runs locally.

## Run locally

1. Copy `.env.example` to `.env` and fill keys (optional DB + Groq).
2. Install deps and start:
   - `powershell -ExecutionPolicy Bypass -File scripts/run_dev.ps1`
3. Smoke test (second terminal):
   - `powershell -ExecutionPolicy Bypass -File scripts/smoke_test.ps1`

Use `user_id` as the numeric **customer id** from the seeded data (e.g. `"1"` … `"25"`) for realistic ERP context.

## Deploy to Vercel

1. Push the repo and import the project in Vercel.
2. Set environment variables: `DATABASE_URL`, `LLM_API_BASE`, `LLM_API_KEY`, `LLM_MODEL` (same as `.env.example`).
3. For WhatsApp demo also set `WHATSAPP_*` vars and `LLM_ORDER=api`, `RAG_FEED_SYNC_ENABLED=false`.
4. Deploy. The ASGI app is exposed via root `index.py` (see `vercel.json` rewrites).

**WhatsApp on Vercel:** step-by-step in [`docs/vercel_whatsapp_demo.md`](docs/vercel_whatsapp_demo.md). Env template: `vercel.env.example`. Local DB prep: `scripts/setup_vercel_whatsapp_demo.ps1`. Smoke: `scripts/smoke_whatsapp.ps1 -BaseUrl https://your-app.vercel.app`.

**Note:** Serverless cold starts and static file serving differ from local `uvicorn`; verify `/` and `/static` in your target environment.

## API routes

- `GET /health` — includes `database: true/false` when pool is configured
- `POST /chat` — main support chat (`user_id`, `channel`, `message`)
- `GET /erp/customers/{id}` — customer profile
- `GET /erp/customers/{id}/orders` — orders list
- `GET /erp/orders/{id}` — order + line items
- `GET /erp/invoices/unpaid?user_id=1` — unpaid / non-paid invoices for that customer
- `POST /channels/whatsapp`, `POST /channels/slack` — channel wrappers

## Integration points

- ERP website should call `POST /chat`
- WhatsApp provider webhook → `POST /channels/whatsapp`
- Slack events webhook → `POST /channels/slack`

## Lean cost controls

- Output token cap: 180
- Retrieval chunk cap: 3
- Budget endpoint: `GET /metrics/budget`
- Cache first for repeated FAQs
- Handoff when confidence is low or query is sensitive
