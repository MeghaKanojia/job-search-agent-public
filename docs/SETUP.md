# One-time setup

These are the accounts/keys only you can create — an agent can't sign up on your behalf.
Everything below is free tier.

## 1. Neon (Postgres)
1. Create a free project at neon.tech (pick an EU region).
2. Copy the connection string → `DATABASE_URL`.
3. Run `backend/db/schema.sql` against it once (e.g. `psql $DATABASE_URL -f backend/db/schema.sql`, or paste it into Neon's SQL editor). This also runs `CREATE EXTENSION IF NOT EXISTS vector;` -- Neon supports pgvector natively, used for the RAG skill-retrieval pipeline (see step 4b).

## 2. Encryption key
Generate once, store as a secret, never commit it:
```
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
→ `ENCRYPTION_KEY`

## 3. Adzuna (dropped -- confirmed not usable for Ireland, keeping this section as a record)
Tried and confirmed broken for this project's purposes (2026-09-03), in order:
1. `ie` country code: doesn't exist. Adzuna's supported codes are at, au, be, br, ca,
   ch, de, es, fr, gb, in, it, mx, nl, nz, pl, sg, us, za -- no Ireland.
2. `gb` country + `where=Ireland` location filter: returns results, but Adzuna's
   free-text location geocoder resolves "Ireland" to a small hamlet of that name in
   Shefford, Bedfordshire, ENGLAND -- not the country. Every result came back
   located in England, wrongly tagged.
3. A per-city workaround (e.g. `where=Dublin`) might disambiguate correctly, but
   wasn't worth pursuing: the free tier is ~1000 calls/month (~33/day), already
   nearly saturated by the 6 role search terms run every 4 hours without any
   per-city fan-out, so there's no quota room left to query multiple cities anyway.

**Conclusion: Adzuna was removed from the codebase entirely (2026-09-05)**, not just left
unconfigured -- there's no `AdzunaConnector`, no `ADZUNA_APP_ID`/`ADZUNA_APP_KEY` anywhere
in config/CI, and no toggle for it in the dashboard's Settings page. Indeed and LinkedIn
via JobSpy are the real, confirmed-working sources for this pipeline. This section stays
only so nobody re-attempts the same investigation from scratch.

## 4. LLM providers — cover letters, status classification, relevance reasoning
Two providers are supported (`pipeline/llm/`, `backend/app/services/llm/`), selectable
per call (the dashboard's cover-letter drafting lets you pick one). Every call site falls
back to deterministic rule-based logic if no provider is configured or a call fails, so
the pipeline works with zero of these set up -- they're a v1 enhancement layer, not a
hard dependency. **Only Groq has an ongoing free tier; set it up first, Gemini is an
optional bonus option.**

Claude/Anthropic and Cerebras were both evaluated (2026-09-04) and deliberately excluded:
neither has an ongoing free tier, only a one-time trial credit (~$5), which doesn't meet
this project's free-only requirement. Don't re-add either without first confirming
they've introduced a genuine ongoing free tier, not just a bigger trial credit.

### 4a. Groq (recommended default, ongoing free tier)
1. Sign up free at console.groq.com (no credit card).
2. Create an API key → `GROQ_API_KEY`.
3. Confirmed limits for the model this project uses (`openai/gpt-oss-120b`): 30
   requests/min, 8,000 tokens/min, and a tight **1,000 requests/day**. The pipeline
   paces itself and caps how many postings get an LLM call per run to respect this
   (see `pipeline/landing/land_to_postgres.py`'s `MAX_LLM_JUDGMENTS_PER_RUN`).

### 4b. RAG skill-retrieval backfill (do this once Groq -- or any provider -- is set up)
The LLM prompts are built from the top-15 most relevant skills for each JD (retrieved
via vector similarity search), not your entire skill profile -- this keeps token usage
low regardless of provider or how large your profile grows. This needs embeddings
computed once:
```
python -c "
from sqlalchemy import create_engine
from pipeline.rag import backfill_skill_embeddings
import os
engine = create_engine(os.environ['DATABASE_URL'])
print(backfill_skill_embeddings(engine), 'skills embedded')
"
```
Re-run this any time you add/edit skills in `skill_profile_items` (only rows with a
NULL `embedding` get processed, so it's safe to re-run anytime). Uses `fastembed`
(ONNX-based, no torch) locally -- no API calls, no rate limits for this part.

### 4c. Gemini (optional bonus, free tier exists but details are account-specific)
1. Get a key at aistudio.google.com (no credit card required for the free tier).
2. → `GEMINI_API_KEY`.
3. **Important**: enabling billing on the underlying Google Cloud project removes the
   free tier entirely and permanently. Never do this if you want Gemini to stay free.
   Google doesn't publish a fixed rate-limit table for this tier -- check your actual
   limits at aistudio.google.com/rate-limit if you see frequent 429s, and adjust
   `min_interval_seconds` in `pipeline/llm/gemini_provider.py` accordingly.

## 5. Google Cloud (Gmail API — no email password ever used)
1. Create a project at console.cloud.google.com, enable the **Gmail API**.
2. Configure the OAuth consent screen (External, Testing mode is fine for personal use).
3. Create an OAuth Client ID (type: Desktop app) → `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET`.
4. Once these + `DATABASE_URL` + `ENCRYPTION_KEY` are set, run once:
   ```
   python -m pipeline.gmail_status_sync.authorize
   ```
   This opens a browser, you approve read-only Gmail access, and a refresh token is stored encrypted in `oauth_tokens`. Your Gmail password is never seen by this project.

## 6. LinkedIn job alerts
Set up saved searches on linkedin.com for your target roles and subscribe to email alerts (a Gmail filter/label helps). `gmail_linkedin_connector.py` parses these.

## 7. IrishJobs.ie / Jobs.ie (opt-in, low-volume, best-effort)
Both sites `Disallow` their RSS path in robots.txt, so there's no clean official integration.
1. Manually create a saved search in your browser.
2. Grab that search's URL → `IRISH_BOARDS_SEARCH_URL`.
3. The connector caps itself to 3 runs/day regardless of how often the GitHub Actions cron fires, and backs off immediately on any 429. Leave `IRISH_BOARDS_SEARCH_URL` empty to disable this source entirely.

## 8. GitHub repo secrets
Add these as **Settings → Secrets and variables → Actions** on your repo:
`DATABASE_URL`, `ENCRYPTION_KEY`, `GROQ_API_KEY`, `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `IRISH_BOARDS_SEARCH_URL`.

Optional (only if you set up section 4c): `GEMINI_API_KEY`.

## 9. Deploy (once Phase 1 is working locally/in Codespaces)

Render and Vercel are two separate domains with no proxy between them, unlike the
Codespace dev setup where Vite's proxy makes frontend→backend calls same-origin
(see vite.config.ts) and CORS never actually applies. Deployed, the browser makes
a genuine cross-origin call from the Vercel domain to the Render domain, so both
sides need to know about each other explicitly -- that's what `CORS_ALLOW_ORIGINS`
and `VITE_API_BASE_URL` below are for.

**Render (backend):**
1. New Web Service → connect this repo → root directory `backend/` → runtime **Docker** (uses `backend/Dockerfile`, which already installs WeasyPrint's system libs).
2. Auto-Deploy: on (default) -- every push to `main` rebuilds and redeploys automatically.
3. Environment variables: same as the GitHub Actions secrets in section 8 (`DATABASE_URL`, `ENCRYPTION_KEY`, `GROQ_API_KEY`, `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`; `GEMINI_API_KEY` optional), **plus**:
   - `CORS_ALLOW_ORIGINS` = your Vercel production URL once you have it (comma-separated if more than one, e.g. previews too): `https://<your-app>.vercel.app`
   - `DASHBOARD_USERNAME` / `DASHBOARD_PASSWORD` = a real, unique credential (see `backend/app/core/auth.py`) -- **required**, the app returns 500 on every route until both are set. This is the only thing gating the whole API once it's a public URL: without it, anyone who finds the URL can read your resume PDFs (phone number, email, full work history), your application tracker, and your profile data, or burn your LLM quota / delete your data via the write endpoints. Pick something you don't reuse elsewhere.
4. Free tier spins down after ~15 min idle; first request after that takes 30-60s to wake up. Nothing in this repo mitigates that yet (`.github/workflows/keepalive.yml` is unrelated -- it's a monthly dummy commit that stops GitHub disabling the cron workflows after 60 days of repo inactivity, not a Render ping). If the cold start becomes annoying, a small scheduled workflow hitting `/health` every ~10 minutes would fix it, at the cost of using free tier hours faster.

**Vercel (frontend):**
1. Import this repo → root directory `frontend/` → framework preset **Vite** (auto-detected).
2. Auto-Deploy: on by default -- every push to `main` redeploys automatically, live in under a minute.
3. Environment variable: `VITE_API_BASE_URL` = your Render backend's URL + `/api`, e.g. `https://<your-service>.onrender.com/api` (see `frontend/.env.example`). This is a **build-time** variable -- changing it requires a redeploy, not just a page refresh.

**Order matters the first time:** deploy Render first (you need its URL for Vercel's `VITE_API_BASE_URL`), then Vercel (you need its URL for Render's `CORS_ALLOW_ORIGINS`), then go back and set `CORS_ALLOW_ORIGINS` on Render and redeploy it once you have the real Vercel URL.

## 10. Databricks Free Edition (analytics layer — not required to see the pipeline work end-to-end)
1. Create a free workspace at databricks.com (Free Edition).
2. Create a secret scope holding your Neon `DATABASE_URL`.
3. Deploy `pipeline/databricks/` as a Workflow and set its **native** schedule inside the workspace UI — it pulls from Postgres on its own; nothing external triggers it.
4. This step can come after you've verified ingestion → dashboard works via the rule-based `matching.py` scorer alone.

## 11. Codespaces
Once the repo is pushed to GitHub: **Code → Codespaces → Create codespace on main**. The `.devcontainer` installs Python/Node deps automatically. Then, inside the Codespace terminal:
```
cd backend && uvicorn app.main:app --reload
cd frontend && npm run dev
```
