# Deployment Runbook (Lean)

## 1. Prepare server
- Install Miniconda Python 3.13+.
- Create directory `C:\srv\erp-ai-agent`.
- Copy project files and `.env` (from `.env.example`).

## 2. Environment setup
- Fill ERP and LLM credentials in `.env`.
- Set `MONTHLY_BUDGET_USD=100`.
- Keep `MAX_OUTPUT_TOKENS<=180` and `MAX_RETRIEVAL_CHUNKS<=3`.

## 3. Database schema
- Apply schema: `psql "$DATABASE_URL" -f scripts/init_schema.sql`
- **Existing DBs:** enable KB RAG column: `psql "$DATABASE_URL" -f scripts/migrate_kb_rag_fts.sql`
- **Vector RAG:** `psql "$DATABASE_URL" -f scripts/migrate_pgvector_rag.sql` then `python scripts/reindex_vector_rag.py` (requires `EMBEDDING_API_KEY`)

## 4. Start service
- Install dependencies from `requirements.txt`.
- Run `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
- Put behind reverse proxy (Nginx/IIS/Caddy) with TLS.

## 5. Channel hooks
- Configure WhatsApp webhook to `/channels/whatsapp` (see `docs/vercel_whatsapp_demo.md`).
- Meta verify token must match `WHATSAPP_VERIFY_TOKEN`; set `WHATSAPP_ACCESS_TOKEN` and `WHATSAPP_PHONE_NUMBER_ID`.
- Check readiness: `GET /integrations/whatsapp/status`.
- Configure Slack event endpoint to `/channels/slack`.
- Set `WHATSAPP_APP_SECRET` for signature validation before production.

## 6. Monitoring and budget control
- Poll `/metrics/budget` every 5 minutes.
- Alert when `alert_triggered=true`.
- Track daily conversations and cost/conversation.

## 7. Go-live stages
- Stage 1: Web channel only for first 48 hours.
- Stage 2: Enable WhatsApp.
- Stage 3: Enable Slack.
- If spend spikes, lower token caps and increase handoff frequency.
