# Infigo Solutions website — AI chat integration

Target site: [https://infigosolutions.com/](https://infigosolutions.com/)

The marketing website **does not** connect to your database. It loads a small JavaScript widget that calls your hosted API (`POST /chat/public`). All RAG, LLM, and Neon data stay on the API server.

---

## How this maps to the “general” no-code flow

| Step (typical SaaS) | This project |
| ------------------- | ------------ |
| **1. Sign up / create bot** | Deploy this FastAPI app (Vercel + Neon + Groq). Enable `SITE_BOT_ENABLED=true`. |
| **2. Train bot (RAG)** | Upload PDFs/Word (`POST /knowledge/file`), paste text (`POST /knowledge/text`), run `python scripts/seed_infigo_kb.py`, optional website feed URL in `SITE_RAG_FEED_URL`. |
| **3. Configure booking** | Set `SITE_BOOKING_URL` to your Calendly (or site scheduling) link. Widget asks for name + email before sharing the link. Full Calendly API/OAuth is optional later. |
| **4. Embed on website** | One `<script>` tag — see [Embed code](#embed-code) below. |

Meta’s Jan 2026 policy on general-purpose bots applies to **WhatsApp Business**, not this web widget. Still, keep answers scoped to **Infigo services** (RAG + prompts), not open-ended chat.

---

## What you still need from Infigo (content)

When ready, collect:

- Approved FAQ (PDF/Word/Google Doc)
- Startup + enterprise one-pagers
- Contact email and “how to get a proposal” wording
- Booking link (Calendly or on-site scheduler URL)

Load into the API knowledge base (admin) or update `config/infigo_kb_seed.md` and run `scripts/seed_infigo_kb.py`.

---

## Phase 1 — API setup (your side)

### 1. Environment variables

Copy from `.env.example`:

```env
DATABASE_URL=postgresql://...-pooler.neon.tech/...?sslmode=require
LLM_API_BASE=https://api.groq.com/openai/v1
LLM_API_KEY=gsk_...
LLM_MODEL=llama-3.1-8b-instant
LLM_ORDER=api
RAG_FEED_SYNC_ENABLED=false

SITE_BOT_ENABLED=true
PUBLIC_CHAT_API_KEY=generate-a-long-random-secret
SITE_COMPANY_NAME=Infigo Solutions
SITE_CONTACT_EMAIL=hello@infigosolutions.com
SITE_BOOKING_URL=https://calendly.com/your-team/30min
SITE_PROPOSAL_URL=https://infigosolutions.com/
CORS_ALLOWED_ORIGINS=https://infigosolutions.com,https://www.infigosolutions.com
SITE_RAG_FEED_URL=https://infigosolutions.com/
```

Optional: `EMBEDDING_API_KEY` for vector RAG.

### 2. Database + KB

```powershell
cd "c:\Users\PC\AI Support agent"
powershell -ExecutionPolicy Bypass -File scripts/setup_infigo_site.ps1
```

### 3. Deploy (Vercel)

Push repo, set the same env vars in Vercel Production, deploy.

### 4. Verify

- `GET https://YOUR-API.vercel.app/health` → `"database": true`
- `GET https://YOUR-API.vercel.app/integrations/site/status` → booking/contact flags

---

## Phase 2 — Train the bot (RAG)

**Ground answers in real content:**

1. **Seed file** — `config/infigo_kb_seed.md` (starter copy from the public site).
2. **Files** — After admin login on the API UI, upload FAQ PDFs under Knowledge.
3. **Website feed** — Register `SITE_RAG_FEED_URL` via `POST /knowledge/feeds` (admin) and sync (HTML must be fetchable as text; SPAs may need manual docs instead).
4. **Reindex vectors** — `python scripts/reindex_vector_rag.py` if embeddings are configured.

The bot retrieves chunks at chat time (RAG); it does not “train” a custom model.

---

## Phase 3 — Booking flow (Calendly-style, no OAuth required)

1. Set `SITE_BOOKING_URL` to the live scheduling link.
2. Visitor asks to “book a meeting” → bot asks for **name and email** in one message (e.g. `Alex, alex@company.com`).
3. Bot replies with the booking URL; the embed shows a **Book a meeting** button when `booking_url` is returned.

**Optional later:** Calendly API + OAuth to create events automatically (not implemented in v1).

For proposals / contact: set `SITE_CONTACT_EMAIL` and `SITE_PROPOSAL_URL`; the bot routes “quote / proposal / contact” intents there.

---

## Phase 4 — Embed on infigosolutions.com (custom React)

The live site is a **custom React** app. You still do **not** need Neon or ERP on the frontend — only `fetch` to your API. Two integration options:

### Option A — React component (recommended)

1. Copy [`docs/examples/InfigoChatWidget.tsx`](examples/InfigoChatWidget.tsx) into the Infigo repo (e.g. `src/components/InfigoChatWidget.tsx`).
2. Add env vars at **build time** (never commit secrets to git; use hosting env UI):

   **Vite**

   ```env
   VITE_INFIGO_CHAT_API_URL=https://YOUR-API.vercel.app
   VITE_INFIGO_CHAT_API_KEY=your-public-chat-key
   ```

   **Create React App**

   ```env
   REACT_APP_INFIGO_CHAT_API_URL=https://YOUR-API.vercel.app
   REACT_APP_INFIGO_CHAT_API_KEY=your-public-chat-key
   ```

3. Mount once in the root layout so it appears on every route:

   ```tsx
   // App.tsx or RootLayout.tsx
   import { InfigoChatWidget } from "./components/InfigoChatWidget";

   export default function App() {
     return (
       <>
         {/* existing routes */}
         <InfigoChatWidget />
       </>
     );
   }
   ```

4. Redeploy the React site. Chat calls `POST /chat/public` from the browser; CORS must allow your production origin.

**From the Infigo React team you need:**

- Access to the repo (or a PR) to add the component + env vars.
- Production/staging URLs for `CORS_ALLOWED_ORIGINS` on the API (e.g. `https://infigosolutions.com`, staging domain).
- No database credentials on the React side.

### Option B — Script tag in `index.html` (no React code change)

If they prefer not to touch React source, add to `public/index.html` before `</body>`:

```html
<script
  src="https://YOUR-API.vercel.app/static/infigo-embed.js"
  data-api-url="https://YOUR-API.vercel.app"
  data-api-key="YOUR_PUBLIC_CHAT_API_KEY"
  data-title="Infigo Assistant"
  data-color="#6366f1"
  defer></script>
```

Works with any React build; the widget is vanilla JS outside the React tree.

### React / SPA notes

| Topic | Implication |
| ----- | ----------- |
| **Client-side routing** | Mount the widget in `App` / layout once — not per page — so it survives route changes. |
| **RAG from `SITE_RAG_FEED_URL`** | A SPA often returns a minimal HTML shell; auto-crawling `https://infigosolutions.com/` may **not** extract page text. Prefer **FAQ PDFs + `infigo_kb_seed.md`** (and updates when marketing copy changes). |
| **Next.js** | Use the same component in `app/layout.tsx` or `_app.tsx`; env prefix `NEXT_PUBLIC_` if you adapt the example. |
| **API key in frontend** | Same as any public widget: key is visible in the bundle — use `PUBLIC_CHAT_API_KEY` + WAF/rate limits if abused. |

### CORS

`CORS_ALLOWED_ORIGINS` must list `https://infigosolutions.com` and `https://www.infigosolutions.com` so the browser can call `/chat/public`.

### Security

- Use a strong `PUBLIC_CHAT_API_KEY`; the key is visible in the page source — rate-limit at CDN/WAF if needed.
- Do not expose Neon `DATABASE_URL` on the website.

---

## API contract (for custom frontends)

```http
POST /chat/public
Content-Type: application/json
X-Site-Api-Key: <PUBLIC_CHAT_API_KEY>

{
  "message": "How long does an MVP take?",
  "session_id": "optional-uuid-from-prior-response",
  "visitor_name": "Alex",
  "visitor_email": "alex@company.com",
  "llm_mode": "api"
}
```

Response includes `answer`, `session_id`, and optionally `booking_url`, `contact_email`, `proposal_hint`.

---

## Troubleshooting

| Issue | Fix |
| ----- | --- |
| Widget cannot connect | Check CORS, API URL, Vercel deploy |
| 401 on chat | `X-Site-Api-Key` must match `PUBLIC_CHAT_API_KEY` |
| Generic / wrong answers | Run seed + upload FAQs; reindex vectors |
| Booking link missing | Set `SITE_BOOKING_URL`; visitor must send name + email |
| ERP/order answers | Should not happen in site mode; use `/chat/public` only |

---

## Checklist

- [ ] Neon + Groq on Vercel
- [ ] `scripts/setup_infigo_site.ps1`
- [ ] FAQ / one-pagers uploaded when received
- [ ] `SITE_CONTACT_EMAIL`, `SITE_BOOKING_URL` set
- [ ] `PUBLIC_CHAT_API_KEY` + CORS origins
- [ ] Embed script on [infigosolutions.com](https://infigosolutions.com/)
- [ ] Test: services question, booking flow, contact/proposal question
