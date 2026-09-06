"""Filters raw ingested postings down to ones actually worth landing, using your
editable `keyword_filters` table (role titles + required skills). Keeps this
pipeline's data volume small and relevant instead of hoovering up every posting.
"""

import re

from sqlalchemy import text
from sqlalchemy.engine import Engine

from pipeline.connectors.base import JobPosting

_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9+.#-]{1,}")

# Catches roles under a different title than the exact keyword_filters phrases --
# e.g. "Data Platform Engineer", "BI Analyst", "Machine Learning Scientist" -- per
# the original spec ("Data Engineer, Data Analyst... and similar roles even if they
# have different titles"). A plain substring match against 8 fixed phrases missed
# this entirely (observed in practice: 325 fetched, only 4 matched two runs in a row).
_ROLE_NOUNS = ("engineer", "analyst", "scientist", "developer")
_DOMAIN_QUALIFIERS = (
    "data", "analytics", "ai", "ml", "machine learning", "artificial intelligence",
    "business intelligence", "bi", "big data",
)


def load_active_keywords(engine: Engine, pipeline: str = "professional") -> tuple[list[str], list[str]]:
    """Returns (role_keywords, skill_keywords) from the keyword_filters table."""
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT keyword, category FROM keyword_filters "
                "WHERE pipeline = :pipeline AND is_active = TRUE"
            ),
            {"pipeline": pipeline},
        ).fetchall()

    roles = [r.keyword for r in rows if r.category == "role"]
    skills = [r.keyword for r in rows if r.category == "skill"]
    return roles, skills


def matches_filters(posting: JobPosting, role_keywords: list[str]) -> bool:
    """A posting passes if EITHER:
      - its title contains one of your exact configured role phrases, OR
      - its title contains a role noun (engineer/analyst/scientist/developer)
        together with a data/AI/ML/BI domain qualifier -- this is what catches
        differently-titled-but-equivalent roles.

    This deliberately favors recall over precision: an occasional loosely-related
    match (e.g. "Data Entry Analyst") is cheap to dismiss when you review it, but
    silently never landing a real match (e.g. "Analytics Consultant") isn't
    recoverable -- you'd never know it existed.

    Skill keywords are NOT a hard gate here at all: JobSpy search results often
    carry a thin or missing description, so requiring an exact skill match before
    landing a posting discards real matches just because the description text was
    incomplete. Skill relevance is instead reflected in keyword_match_score
    (computed at landing time, see pipeline/scoring.py).
    """
    title_lower = posting.title.lower()

    if role_keywords and any(role.lower() in title_lower for role in role_keywords):
        return True

    # Word-boundary matching matters here -- short qualifiers like "ai"/"bi"/"ml"
    # would otherwise false-positive as substrings inside unrelated words (e.g.
    # "ai" inside "Maintenance Engineer").
    has_role_noun = any(re.search(rf"\b{noun}\b", title_lower) for noun in _ROLE_NOUNS)
    has_domain_qualifier = any(
        re.search(rf"\b{re.escape(q)}\b", title_lower) for q in _DOMAIN_QUALIFIERS
    )
    return has_role_noun and has_domain_qualifier


def filter_postings(postings: list[JobPosting], role_keywords: list[str]) -> list[JobPosting]:
    return [p for p in postings if matches_filters(p, role_keywords)]
