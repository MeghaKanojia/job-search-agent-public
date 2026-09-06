"""Writes filtered postings into `job_postings` (upsert on dedup_hash) and
appends the raw payload to `raw_ingest_events` for lineage -- Databricks reads
the latter's unprocessed rows to run bronze/silver/gold independently.
"""

import datetime as dt
import json
import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from pipeline.connectors.base import JobPosting
from pipeline.scoring import llm_relevance_judgment, load_active_skill_names, score_description

logger = logging.getLogger(__name__)

# Groq's confirmed free-tier limits for openai/gpt-oss-120b: 30 req/min,
# 8,000 tokens/min, and a tight 1,000 requests/DAY (see pipeline/llm/groq_provider.py).
# That daily cap is the real constraint to design around. Ingestion runs every
# 4h (6x/day) across up to ~2 connectors that typically produce matches
# (JobSpy, Gmail-LinkedIn) -- at 40/connector that's already 480 requests/day
# from ingestion alone, leaving little room for status-email classification
# and cover-letter drafting sharing the same daily quota. 20 keeps ingestion's
# worst-case daily usage around 240, leaving real headroom. Postings beyond
# this cap per connector call just keep their rule-based score, ranked by that
# same score first so the ones most likely to be worth the richer judgment get
# it.
MAX_LLM_JUDGMENTS_PER_RUN = 20


def land_postings(engine: Engine, source: str, batch_id: str, postings: list[JobPosting]) -> int:
    landed = 0
    skill_names = load_active_skill_names(engine)

    # Score every posting BEFORE opening the DB transaction below -- these involve
    # a network call to Groq per posting, and holding a DB transaction open across
    # potentially slow/rate-limited network calls risks long-held locks/timeouts.
    rule_scored = [
        (posting, *score_description(posting.description, skill_names)) for posting in postings
    ]
    rule_scored.sort(key=lambda row: row[1], reverse=True)

    scored = []
    for i, (posting, rule_score, matched_keywords) in enumerate(rule_scored):
        if i < MAX_LLM_JUDGMENTS_PER_RUN:
            judgment = llm_relevance_judgment(engine, posting.title, posting.description)
        else:
            judgment = None
        if judgment is not None:
            score, reasoning = judgment
        else:
            score, reasoning = rule_score, None
        scored.append((posting, score, matched_keywords, reasoning))

    with engine.begin() as conn:
        for posting, score, matched_keywords, reasoning in scored:
            # The Gmail-LinkedIn-alert parser and the Irish-boards scraper have no
            # real "date posted" field to read (see their connectors) and leave posted_at
            # None. Falling back to ingestion time here -- rather than leaving it NULL --
            # means date-based sort/filter in the API (e.g. "posted within 24h") doesn't
            # silently exclude these sources just because the true posting date is unknown;
            # discovery time is the best available freshness signal for them.
            posted_at = posting.posted_at or dt.datetime.now(dt.timezone.utc)

            conn.execute(
                text(
                    "INSERT INTO raw_ingest_events (source, payload, batch_id) "
                    "VALUES (:source, :payload, :batch_id)"
                ),
                {
                    "source": source,
                    "payload": json.dumps(_posting_to_dict(posting)),
                    "batch_id": batch_id,
                },
            )

            result = conn.execute(
                text(
                    """
                    INSERT INTO job_postings
                        (source, source_job_id, title, company, location, url,
                         description_raw, salary_text, posted_at, dedup_hash,
                         keyword_match_score, matched_keywords, relevance_reasoning)
                    VALUES
                        (:source, :source_job_id, :title, :company, :location, :url,
                         :description_raw, :salary_text, :posted_at, :dedup_hash,
                         :keyword_match_score, :matched_keywords, :relevance_reasoning)
                    ON CONFLICT (dedup_hash) DO NOTHING
                    RETURNING id
                    """
                ),
                {
                    "source": posting.source,
                    "source_job_id": posting.source_job_id,
                    "title": posting.title,
                    "company": posting.company,
                    "location": posting.location,
                    "url": posting.url,
                    "description_raw": posting.description,
                    "salary_text": posting.salary_text,
                    "posted_at": posted_at,
                    "dedup_hash": posting.dedup_hash(),
                    "keyword_match_score": score,
                    "matched_keywords": json.dumps(matched_keywords),
                    "relevance_reasoning": reasoning,
                },
            )
            if result.fetchone() is not None:
                landed += 1

    return landed


def _posting_to_dict(posting: JobPosting) -> dict:
    return {
        "source": posting.source,
        "title": posting.title,
        "company": posting.company,
        "location": posting.location,
        "url": posting.url,
        "description": posting.description,
        "salary_text": posting.salary_text,
        "source_job_id": posting.source_job_id,
        "posted_at": posting.posted_at.isoformat() if posting.posted_at else None,
    }
