import datetime as dt
from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.application import Application
from app.models.job_posting import JobPosting
from app.schemas.job_posting import JobPostingOut

router = APIRouter(prefix="/api/matches", tags=["matches"])


@router.get("", response_model=list[JobPostingOut])
def list_matches(
    min_score: float = 0.0,
    limit: int = 50,
    sort: Literal["score", "posted_at"] = "score",
    posted_within_days: int | None = None,
    db: Session = Depends(get_db),
):
    """Shows every role-matched posting regardless of scoring status -- score is a
    ranking signal, not a visibility gate. The pipeline computes a score at landing
    time (defaulting to 0.0 until you've configured a skill profile), so score should
    always be populated for new rows; nullslast() just guards against any legacy
    row from before that landing-time scoring existed.

    sort="posted_at" surfaces the newest postings first -- freshly posted roles have
    fewer competing applicants, so this is the default a user chasing that edge wants
    even though it isn't the ranking-quality default. posted_within_days filters out
    stale postings entirely rather than just reordering them.

    Excludes any posting that already has an Application row (staged, approved,
    applied, whatever) -- once you've staged it for review it belongs to that flow,
    not this list. Reverting it (Review Queue's "back to New Matches" action) deletes
    the Application row, which is exactly what makes it reappear here.
    """
    stmt = select(JobPosting).where(
        (JobPosting.keyword_match_score >= min_score) | (JobPosting.keyword_match_score.is_(None))
    ).where(~select(Application.id).where(Application.job_posting_id == JobPosting.id).exists())

    if posted_within_days is not None:
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=posted_within_days)
        stmt = stmt.where(JobPosting.posted_at >= cutoff)

    if sort == "posted_at":
        stmt = stmt.order_by(JobPosting.posted_at.desc().nullslast(), JobPosting.ingested_at.desc())
    else:
        stmt = stmt.order_by(JobPosting.keyword_match_score.desc().nullslast(), JobPosting.ingested_at.desc())

    stmt = stmt.limit(limit)
    return db.execute(stmt).scalars().all()
