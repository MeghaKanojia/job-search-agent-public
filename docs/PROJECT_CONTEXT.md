# Project Context & Architecture Reference

> **Purpose of this file**: a self-contained technical briefing on this project. If something
> breaks and you need help from any LLM (ChatGPT, a fresh Claude session, etc.), paste this
> whole file in first, it gives enough context to debug without needing prior conversation
> history. It's also written to double as interview prep: the "why" behind each decision is
> exactly the kind of thing an interviewer will probe on.

## What this is

An end-to-end, zero-budget job-search automation platform for Data/Analytics/ML roles. It
ingests real job postings from multiple sources, scores them against a personal skill profile,
generates AI-tailored resumes and cover letters, tracks every application through to outcome,
and syncs status updates from Gmail replies. Built as a real personal tool and, secondarily, as
a full-stack + RAG/LLM portfolio piece.

**This is the public demo repo** (`job-search-agent-public`): a sanitized fork of a private
original, with fictional profile data (fake employer, fake contact details, fake work history)
and no Gmail integration. Its login screen deliberately publishes its own throwaway credentials
(`public`/`12345`) right on the page, since there's no real data behind this instance, it's meant
to be linked from a CV/resume as a clickable, walk-up-and-explore live demo. The private original
has the same codebase (near-byte-identical outside a handful of sanitized files) but real
personal data, real Gmail integration, and a login gate that never publishes its credentials.

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Backend | FastAPI + SQLAlchemy (Python) | Async-friendly, good typing, minimal boilerplate |
| Database | Postgres via Neon (free tier) + pgvector extension | One database for both relational data and vector similarity search, no separate vector-store service needed |
| Frontend | React + Vite + TypeScript, styled with Tailwind CSS | Fast dev loop, type safety, utility-first styling that's easy to restyle without touching component logic |
| Pipeline | Python connectors, orchestrated by GitHub Actions cron (every 6 hours) | No server needed to run scheduled jobs; free compute |
| LLM | Groq (primary, free tier, ~1000 req/day cap) with Gemini fallback | Genuine ongoing free tiers only; Claude/Anthropic and Cerebras were evaluated and excluded, no ongoing free tier, only trial credits |
| RAG | pgvector cosine-similarity search over fastembed (`BAAI/bge-small-en-v1.5`) embeddings | Free, local embedding model; no OpenAI embeddings API needed |
| PDF generation | WeasyPrint + Jinja2 templates | Renders resume/cover-letter HTML to PDF server-side |
| Backend deployment | Render (Docker), free instance | Genuine Docker support (needed for WeasyPrint's system libraries) unlike serverless platforms |
| Frontend deployment | Vercel (Hobby/free) | Standard for Vite/React static builds |
| Auth | Custom HTTP Basic-style login, `secrets.compare_digest` | No per-user account system needed for a single-user tool; this is the only thing gating the API once it's a public URL |

## Repository layout

```
backend/
  app/
    api/routes/        FastAPI route modules (matches, applications, documents, profile, settings)
    core/               config.py (pydantic-settings), auth.py, security.py (Fernet encryption), db.py
    models/             SQLAlchemy ORM models
    schemas/            Pydantic request/response schemas
    services/           tailoring.py (LLM + no-fabrication rules), rag.py, llm/ (provider abstraction)
  db/
    schema.sql           Full DDL, run once against a fresh Postgres
    seed_profile.sql      Seed data for education/experience/projects/skills/certifications
  Dockerfile
  requirements.txt
frontend/
  src/
    pages/               One component per dashboard page (NewMatches, ReviewQueue, etc.)
    components/          Shared components (Login, Toast, Pagination, SectionManager)
    api/client.ts        Single fetch wrapper + typed API methods
    index.css            Tailwind directives + @layer components (design system)
pipeline/
  connectors/            One file per ingestion source (jobspy, gmail_linkedin, irish_boards)
  gmail_status_sync/      Scans Gmail for interview/rejection/offer signals
  landing/               Dedup + insert into Postgres
  llm/                   Duplicate of backend's LLM abstraction (pipeline runs as a separate process)
  run_ingest.py           Entrypoint called by the GitHub Actions cron
.github/workflows/       CI (backend/frontend/pipeline) + scheduled ingestion + Gmail sync + keepalive
docs/
  SETUP.md                One-time account/key setup walkthrough
  PROJECT_CONTEXT.md       This file
```

## End-to-end data flow

1. **Ingestion** (GitHub Actions cron, every 6 hours, `pipeline/run_ingest.py`):
   - `JobSpyConnector`: unauthenticated search across Indeed/LinkedIn/Glassdoor/ZipRecruiter/Google. No credentials needed.
   - `GmailLinkedInConnector`: parses LinkedIn's own job-alert emails via Gmail OAuth (`gmail.readonly` scope only). Company names are extracted via a single LLM call per email (not per posting, to conserve Groq's daily quota), not regex, since LinkedIn's email template isn't documented and regex would silently break on any layout change. **Not configured in this public demo instance** (deliberately, no real Gmail account is wired to this repo, since that would mean storing a real OAuth token in infrastructure tied to a public project for no demo benefit); it's inert here without breaking anything, same as any unconfigured LLM call.
   - `IrishBoardsConnector`: opt-in scraper for jobs.ie/irishjobs.ie, rate-limited to 3 runs/day, requires a manually-obtained saved-search URL (`IRISH_BOARDS_SEARCH_URL`). Its CSS selectors are unverified placeholders, best-effort.
   - Each source runs in isolation (one failing never blocks the others). Postings are deduplicated by a content hash (company + title + location), inserted with `ON CONFLICT DO NOTHING`.
   - A keyword filter (`pipeline/keyword_filter.py`) gates what gets landed at all: a posting must match a configured role keyword OR a role-noun + domain-qualifier heuristic (catches "Analytics Consultant" even without an exact keyword match).
   - Relevance scoring happens at landing time against `skill_profile_items`.

2. **Dashboard** (React SPA, calls the FastAPI backend):
   - **New Matches**: browse/filter/sort scored postings, "Stage for review" creates an `Application` row.
   - **Review Queue**: generate a tailored resume and/or cover letter per staged application, preview inline, hand-edit a cover letter directly, or supply plain-English tweak instructions that get threaded into the next LLM regeneration. Approve or reject.
   - **Applications Tracker**: full status lifecycle, bulk actions (checkbox multi-select + bulk delete), a "resume used" column, and the ability to upload an externally-built resume PDF instead of the generated one.
   - **Resume Library**: paginated, versioned document history across all applications.
   - **Profile**: the single source of truth for tailoring (skills/education/experience/projects/certifications), full CRUD.
   - **Settings**: per-source pipeline kill switches (reads `pipeline_settings` table, checked by `run_ingest.py` before each connector runs), keyword filter management, LLM provider status.

3. **Document generation** (`backend/app/api/routes/documents.py`):
   - **Skill relevance**: a hybrid, non-LLM approach: exact keyword matching UNION pgvector cosine-similarity search over embedded skills. Deterministic, free, fast. This replaced an earlier LLM-based approach specifically to cut Groq API usage, since skills are numerous/short/already-embedded, exactly what a vector search is good at.
   - **Project relevance**: an LLM call (Groq/Gemini) asks which of the real project titles are relevant to this JD. This is a *selection* task, not generation, the model can only choose from the exact titles given, never invent one; any hallucinated title is dropped by the caller regardless.
   - **Project bullets**: rewritten per-JD into Google's XYZ format ("Accomplished X, as measured by Y, by doing Z") via LLM, strictly grounded in the project's stored facts. Falls back to the raw stored description if the LLM is unconfigured or fails.
   - **Cover letters**: drafted via LLM, grounded in RAG-retrieved top-K relevant skills (not the full profile, keeps the prompt small).
   - **The no-fabrication rule** (`backend/app/services/tailoring.py`): the single most load-bearing constraint in the whole project. Tailoring may only ever reorder/select from the user's own truthful `skill_profile_items`/`projects` data, never invent a skill, employer, or metric. Enforced by prompt design AND automated tests (`test_tailoring.py`, `test_relevance_selection.py`).
   - **Transparency**: every generation response carries a transient `warnings` list describing anything that fell back this run (LLM unavailable, embeddings not backfilled), surfaced as a toast, so a less-AI-tailored document never silently looks normal.

4. **Gmail status sync** (`pipeline/gmail_status_sync/status_scanner.py`): scans Gmail for signals of interview/rejection/offer on tracked applications, surfaces them as *proposals* the user must confirm in the dashboard, never auto-applies a status change.

## Key design decisions (the "why")

- **No LLM call is ever a hard dependency.** Every single LLM integration point (`app/services/llm/`, `pipeline/llm/`) degrades to deterministic rule-based or static-template behavior if a provider is unconfigured, rate-limited, or the call fails. This is tested, not just hoped for.
- **No-fabrication is enforced twice**: once by prompt design (explicit hard rules in every system prompt), once by code (the caller only reads back items from the exact list it gave the LLM; anything else is dropped regardless of what the model says).
- **Adzuna was evaluated and removed entirely** (not just left unconfigured): its own investigation (documented in `docs/SETUP.md` section 3) found it has no Ireland country code, and its `gb + where=Ireland` workaround geocodes to a village in Bedfordshire, England, not the country. Kept as a documented dead end so nobody re-attempts it.
- **The API has authentication now, but didn't originally.** A full security audit (triggered by explicit concern about privacy/secrets) found the entire API was unauthenticated, fine while only reachable inside a GitHub-authenticated Codespace, a real problem once deployed to a public Render URL. Fixed with a shared-credential login gate (`app/core/auth.py`), `secrets.compare_digest` to avoid a timing side-channel, applied to every router except `/health`.
- **CORS and the frontend's API base URL are environment-driven**, not hardcoded, specifically because Render and Vercel are separate domains with no proxy between them (unlike the Codespace dev setup, where Vite's dev-server proxy makes API calls same-origin and CORS never actually applies there).
- **The public demo repo publishes its own login credentials on the login screen itself.** Deliberate: there's no real data behind that instance, so the usual reason to keep credentials secret doesn't apply, and a recruiter needs to actually get in without emailing anyone first.

## Known gotchas (troubleshooting reference)

| Symptom | Cause | Fix |
|---|---|---|
| `OSError: cannot load library 'libpango-1.0-0'` | WeasyPrint's system dependencies aren't installed | `sudo apt-get install libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0` — see WeasyPrint's own current docs; earlier versions of this project installed a broader, outdated list that included packages WeasyPrint doesn't actually need |
| Render build fails: `Package 'libgdk-pixbuf2.0-0' has no installation candidate` | The floating `python:3.11-slim` Docker tag can land on a newer Debian release where that package was renamed; also, it was never actually required by current WeasyPrint | Pin `FROM python:3.11-slim-bookworm`, and use the corrected package list above |
| `psycopg2.OperationalError: connection to server at "localhost" ... Connection refused` | `DATABASE_URL` isn't set in the process environment; exported shell vars don't persist across Codespace terminal tabs/restarts | Put `DATABASE_URL` in a `.env` file the app actually loads (pydantic-settings reads `backend/.env` relative to where the process starts), not just a one-off `export` |
| CORS error in browser console, or a generic `TypeError: Failed to fetch` | `CORS_ALLOW_ORIGINS` on Render doesn't include the deployed frontend's exact origin | Set it to `https://<vercel-domain>` exactly (no trailing slash, correct scheme), then let Render restart |
| Login screen 500s on every request | `DASHBOARD_USERNAME`/`DASHBOARD_PASSWORD` aren't set wherever the backend is running | Add them to that specific environment (Codespace `.env` or Render env vars, these are two independent systems) |
| SQLAlchemy `Enum` inserts fail against a Postgres native enum | SQLAlchemy's `Enum(SomePythonEnum)` stores the enum's `.name` by default, not `.value`, even for a `(str, Enum)` mixin | Add `values_callable=lambda enum_cls: [e.value for e in enum_cls]` to any `Enum()` column |
| Vercel tries to deploy the backend too | Vercel's monorepo auto-detection finds both `frontend/` and `backend/` and offers to deploy both as "services" | Don't let it; the backend needs system libraries Vercel's serverless runtime can't install. Set Root Directory to `frontend` directly instead of accepting the auto-detected multi-service config |
| Doubled/tripled whitespace in a generated PDF | WeasyPrint applies its own default `@page` margin (~2cm, from its UA stylesheet) *in addition to* any `body` margin in your CSS | Declare `@page { margin: ...; }` explicitly and set `body { margin: 0; }`, don't rely on the UA default |

## Security posture (as of the last audit)

- No hardcoded secrets anywhere in source (verified by repo-wide grep for common key patterns).
- No secret is ever put in a `VITE_`-prefixed frontend env var (those get compiled into the public JS bundle).
- Every raw SQL query uses bound `:parameter` syntax, no string interpolation, no injection surface.
- Gmail access uses OAuth with `gmail.readonly` scope only (can't send/delete/modify anything); tokens are Fernet-encrypted at rest; no API route touches the `oauth_tokens`/`credentials` tables, that data never reaches the public-facing backend.
- The whole API (except `/health`) requires a shared credential, compared with `secrets.compare_digest`.
- Resume uploads are capped at 10MB and validated as `application/pdf`.

## Deployment

Both repos deploy the same way: Render (backend, Docker, free instance, `/health` as the health check path, spins down after ~15 min idle causing a 30-60s cold start on the next request) + Vercel (frontend, free Hobby plan, root directory `frontend`, `VITE_API_BASE_URL` set at build time to the Render URL + `/api`) + Neon (Postgres, free tier, pgvector extension). Both platforms auto-redeploy on every push to `main`.

Order matters the first time: deploy Render first (need its URL for Vercel's env var), then Vercel (need its URL for Render's `CORS_ALLOW_ORIGINS`), then set that on Render and let it restart.

Scheduled pipeline runs (`ingest-professional.yml`, `gmail-status-sync.yml`) are entirely separate from both Render and Vercel, they run on GitHub's own Actions runners and read GitHub repository secrets (Settings → Secrets and variables → Actions), not Render environment variables. `GOOGLE_OAUTH_CLIENT_ID`/`SECRET` only need to exist there (and in the Codespace, for manual runs), never on Render, the backend web service never touches Gmail.

## Testing & CI

Separate GitHub Actions workflows for backend (`pytest`), frontend (`vite build`), and pipeline (`pytest`) tests, triggered on every push/PR touching that directory. Notable test coverage: the no-fabrication guarantee (`test_tailoring.py`), hallucination-guarding on LLM-driven selection tasks (`test_relevance_selection.py`, `test_gmail_linkedin_connector.py`), and RAG's fallback behavior when embeddings are missing (`test_rag.py`).

## What's not done / known limitations

- Irish boards scraper's CSS selectors were never verified against the live site's real markup.
- No automated keepalive for Render's free-tier cold start (would need an external uptime pinger like UptimeRobot; a GitHub Actions cron was considered and rejected, a ping every 10 minutes would exceed the private repo's free Actions-minutes budget).
- Databricks analytics layer (bronze/silver/gold, MLflow-tracked model) was scaffolded but never fully built out.

## Interview prep: likely questions and honest answers

**"Walk me through the architecture."** Use the data-flow section above: ingestion (GitHub Actions cron → 3 connectors → dedup → Postgres) → dashboard (FastAPI + React) → generation (RAG + LLM, grounded, tested) → tracking (Gmail-derived proposals, human-confirmed).

**"How do you prevent the LLM from hallucinating?"** Two layers: prompt-level hard rules in every system prompt, and code-level enforcement, the caller only accepts model output that matches an exact, pre-known set of names/titles it supplied; anything else is silently dropped regardless of what the model returns. This is tested directly (mock an LLM response containing a hallucinated entry, assert it never surfaces).

**"Why RAG instead of just prompting with everything?"** Keeps prompts small and cheap (important on a free-tier rate limit), and lets a cheap deterministic vector search do the filtering work an LLM would otherwise need a full call for, only project selection actually needs an LLM judgment call, since skills are numerous/short/already embedded.

**"What would you do differently / what's the biggest weakness?"** The Irish boards scraper is genuinely fragile (unverified selectors against an undocumented site), and there's no automated way to detect when it silently starts returning nothing or garbage. A more robust version would validate scraped results against an expected shape before landing them.

**"How is this deployed / what does 'production' mean here?"** Real, live: Render (Docker backend) + Vercel (frontend) + Neon (Postgres), auto-deploying on every push, genuinely $0/month across all three, with a small, known cold-start tradeoff on the free Render tier.

**Metrics you can defend, and what they actually mean:**
- "4 ingestion sources refreshed every 6 hours" — literal, verifiable fact (GitHub Actions cron schedule, connector count after Adzuna's removal).
- "~90% reduction in per-application effort" — an *estimate* built on a commonly-cited manual-application baseline (~20-30 min: search, read JD, tailor resume, write cover letter, log it), not a measured before/after result. Be upfront about this if asked, it's a reasonable estimate, not a measured claim.
