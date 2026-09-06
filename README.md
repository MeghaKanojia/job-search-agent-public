# Job Search Agent (Demo)

> **This is a sanitized, portfolio/demo replica of a private personal project.**
> The name shown throughout is real (this is my own project), but every contact
> detail, employer, and work history entry is a fictional placeholder — no real
> personal data is in this repository. The private original runs against a real
> Gmail inbox and real application data, which is exactly why that one isn't
> the thing being shown publicly.

An end-to-end, zero-budget job-search tool: ingests real postings (Indeed/Glassdoor/ZipRecruiter/Google via [JobSpy](https://github.com/speedyapply/JobSpy), LinkedIn job-alert emails, and opt-in Irish job boards), scores them against a skill profile, tailors a CV per posting, tracks every application, and syncs status from Gmail replies — all on free tiers.

## What this demonstrates

- **Full-stack ownership**: FastAPI + SQLAlchemy backend, React + Vite + TypeScript frontend, a multi-connector ingestion pipeline, and CI for all three, deployed end to end (Render + Vercel + Neon Postgres).
- **Applied RAG**: pgvector-backed semantic skill matching (`backend/app/services/rag.py`) blended with exact keyword matching, used to decide which of a candidate's real skills are relevant to a given job description — no LLM call needed for that half of resume tailoring.
- **LLM integration done defensively**: a multi-provider abstraction (Groq primary, Gemini fallback, both genuine free tiers) where every call site degrades to deterministic rule-based logic if a provider is unconfigured or a call fails — the app never breaks because a third-party API is down.
- **A hard-enforced no-fabrication guardrail**: CV tailoring can only reorder or select from a candidate's own stored profile data, never invent a skill or metric — enforced by both prompt design and test coverage (`backend/tests/test_tailoring.py`).
- **Security as a first-class concern, not an afterthought**: HTTP Basic auth gates every API route, secrets are Fernet-encrypted at rest, Gmail access uses OAuth with a read-only scope, and CORS/env-var configuration was built specifically to support a genuine cross-domain production deployment rather than assuming same-origin dev conditions.

## Screenshots

_Add screenshots here after running the app locally/in a Codespace against the
sample data seeded by `backend/db/seed_profile.sql` — see [`docs/SETUP.md`](docs/SETUP.md)._

<!--
![New Matches](screenshots/new-matches.png)
![Review Queue](screenshots/review-queue.png)
![Applications Tracker](screenshots/applications-tracker.png)
![Tailored Resume](screenshots/resume-sample.png)
-->

## Design decisions worth knowing before you touch this

- **No LinkedIn login automation, ever.** LinkedIn coverage comes from (a) Gmail parsing of LinkedIn's own job-alert emails, and (b) JobSpy's *unauthenticated* public search (no account, so no ban risk — just IP-level rate limiting, capped conservatively).
- **No autonomous submission in this pipeline.** Every application is staged for manual review/approval in the dashboard. Full auto-apply across arbitrary company ATSs isn't reliably buildable and isn't the goal here — quality of application matters more than volume for these roles.
- **CV tailoring never fabricates a skill.** `services/tailoring.py` can only reorder/select from `skill_profile_items` — see `backend/tests/test_tailoring.py`.
- **No plaintext credentials, anywhere.** Gmail access is OAuth-only (`gmail.readonly` scope). Anything unavoidable is Fernet-encrypted with a key that lives outside the database.
- **The API is never unauthenticated in a deployed environment.** A single shared credential (`DASHBOARD_USERNAME`/`DASHBOARD_PASSWORD`) gates every route except `/health`, checked with a timing-safe comparison — see `backend/app/core/auth.py`.
- **GitHub Actions and Databricks are decoupled.** Whether Databricks Free Edition supports external job-triggering is unconfirmed, so ingestion lands in Postgres on its own schedule and Databricks pulls from Postgres on its own native schedule — neither depends on calling the other.

## Tech stack

| Layer | Choice |
|---|---|
| Backend | FastAPI, SQLAlchemy, Postgres (Neon, with pgvector) |
| Frontend | React, Vite, TypeScript |
| Pipeline | Python connectors + GitHub Actions cron |
| LLM | Groq (primary), Gemini (fallback) — both free-tier |
| PDF generation | WeasyPrint |
| Deployment | Render (backend, Docker), Vercel (frontend) |

## Repo layout

- `backend/` — FastAPI + SQLAlchemy, serves the dashboard from Postgres
- `frontend/` — React + Vite + TS dashboard
- `pipeline/` — ingestion connectors + GitHub Actions entrypoints + Databricks notebooks
- `docs/SETUP.md` — one-time account/key setup (Neon, Google Cloud, Render, Vercel, etc.)

## Running this yourself

See [`docs/SETUP.md`](docs/SETUP.md) for the full walkthrough. The short version: create a free Neon Postgres project, run `backend/db/schema.sql` then `backend/db/seed_profile.sql` (the fictional sample data above) against it, set the env vars in `.env.example`, and run the backend/frontend locally or in a Codespace.

## About

Built by **Megha Kanojia** — [LinkedIn](https://www.linkedin.com/in/megha-kanojia-bb3662192) · [GitHub](https://github.com/MeghaKanojia)
