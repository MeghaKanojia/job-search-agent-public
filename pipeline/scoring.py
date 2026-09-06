"""Same rule-based keyword-overlap scoring as backend/app/services/matching.py,
duplicated here because the pipeline is a separately-deployed process. Computes
keyword_match_score immediately at landing time, so the dashboard works before
Databricks is even set up -- Databricks's 03_gold_scored_matches.py can later
overwrite this column with a more refined score once labeled outcomes exist.

Also offers an LLM-based relevance judgment (score + a one-sentence reason) as
a richer alternative to raw keyword overlap -- e.g. it can recognize "led ETL
pipeline development" as evidence of PySpark/Databricks-adjacent experience
even if those exact words aren't in the posting. Falls back to the rule-based
score if the LLM is unconfigured or fails; land_to_postgres.py decides which
result to use.

The LLM prompt is built from RAG-retrieved skills (pipeline/rag.py), not the
full skill profile -- retrieving only the ~15 most relevant skills for a given
JD keeps token usage well within free-tier budgets regardless of how large
your overall skill profile grows.
"""

import json
import logging
import re

from sqlalchemy import text
from sqlalchemy.engine import Engine

from pipeline import llm
from pipeline.rag import retrieve_relevant_skills

logger = logging.getLogger(__name__)

_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9+.#-]{1,}")

_RELEVANCE_SYSTEM_PROMPT = """You judge how well a job posting matches a candidate's real skill profile.
Respond with ONLY a JSON object, no other text, in exactly this shape:
{"score": <float 0.0-1.0>, "reason": "<one short sentence>"}
score: 1.0 = excellent match, 0.0 = no relevant overlap at all.
Base the score only on the candidate's listed skills below -- do not assume skills not listed.
The reason must be a single factual sentence about why it does or doesn't fit, no more than 25 words."""

# Keep in sync with backend/app/services/matching.py's STRONG_MATCH_SKILL_COUNT --
# scoring against the full skill-profile size made even a strong match (5-6
# overlapping skills) score near zero, since no single posting mentions most of a
# 70-item profile. This many matches (or more) now counts as a full/strong score.
STRONG_MATCH_SKILL_COUNT = 5


def load_active_skill_names(engine: Engine) -> list[str]:
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT skill_name FROM skill_profile_items WHERE is_active = TRUE")
        ).fetchall()
    return [r.skill_name for r in rows]


def score_description(description: str | None, skill_names: list[str]) -> tuple[float, list[str]]:
    if not skill_names:
        return 0.0, []
    # See backend/app/services/matching.py's extract_keywords for why the rstrip
    # matters -- otherwise a skill at the end of a sentence ("...in Python.") would
    # extract as "python." and silently fail to match "python".
    words = {w.lower().rstrip(".") for w in _WORD_RE.findall(description or "")}
    matched = [s for s in skill_names if s.lower() in words]
    return round(min(len(matched) / STRONG_MATCH_SKILL_COUNT, 1.0), 4), matched


def llm_relevance_judgment(
    engine: Engine, title: str, description: str | None, provider: str | None = None
) -> tuple[float, str] | None:
    """Returns (score, one-sentence reason), or None if the LLM is unconfigured,
    the call failed, or it returned something unparseable -- callers must fall
    back to score_description() in that case.

    Retrieves only the RAG top-K relevant skills for this JD (not your full
    profile) to build the prompt -- see pipeline/rag.py.
    """
    relevant_skills = retrieve_relevant_skills(engine, f"{title}\n{description or ''}", k=15)
    if not relevant_skills:
        return None

    user_prompt = (
        f"Job title: {title}\n"
        f"Job description: {(description or '(no description available)')[:1500]}\n\n"
        f"Candidate's most relevant skills: {', '.join(relevant_skills)}"
    )
    result = llm.chat(_RELEVANCE_SYSTEM_PROMPT, user_prompt, provider=provider)
    if result is None:
        return None

    try:
        parsed = json.loads(result)
        score = float(parsed["score"])
        reason = str(parsed["reason"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        logger.warning("llm relevance judgment returned unparseable output %r: %s", result, exc)
        return None

    return round(min(max(score, 0.0), 1.0), 4), reason
