# Deployment Runbook (Lean)

## 1. Prepare server
- Install Miniconda Python 3.13+.
- Create directory `C:\srv\erp-ai-agent`.
- Copy project files and `.env` (from `.env.example`).

## 2. Environment setup
- Fill ERP and LLM credentials in `.env`.
- Set `MONTHLY_BUDGET_USD=100`.
- Keep `MAX_OUTPUT_TOKENS<=180` and `MAX_RETRIEVAL_CHUNKS<=3`.

## 3. Start service
- Install dependencies from `requirements.txt`.
- Run `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
- Put behind reverse proxy (Nginx/IIS/Caddy) with TLS.

## 4. Channel hooks
- Configure WhatsApp webhook to `/channels/whatsapp`.
- Configure Slack event endpoint to `/channels/slack`.
- Add webhook secret validation before production.

## 5. Monitoring and budget control
- Poll `/metrics/budget` every 5 minutes.
- Alert when `alert_triggered=true`.
- Track daily conversations and cost/conversation.

## 6. Go-live stages
- Stage 1: Web channel only for first 48 hours.
- Stage 2: Enable WhatsApp.
- Stage 3: Enable Slack.
- If spend spikes, lower token caps and increase handoff frequency.
