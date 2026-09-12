import datetime as dt
from collections import Counter

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.application import Application
from app.models.job_posting import JobPosting
from app.models.status_proposal import StatusHistory

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

_FUNNEL_STATUSES = ["applied", "viewed", "interview", "offer", "rejected", "withdrawn"]
_SCORE_BUCKETS = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0001]
_SCORE_BUCKET_LABELS = ["0.0-0.2", "0.2-0.4", "0.4-0.6", "0.6-0.8", "0.8-1.0"]


@router.get("")
def get_analytics(
    start_date: dt.datetime | None = Query(None),
    end_date: dt.datetime | None = Query(None),
    db: Session = Depends(get_db),
):
    """One consolidated payload backing the Analytics page, aggregated
    server-side since it reads across job_postings/applications/status_history --
    not something the frontend should stitch together from three separate
    fetches. Both dates are optional; omitting both means all-time.

    Every count below is EVENT-based, not entity-lifetime-based: a "staged"
    count reflects Application.created_at falling in range, and every later
    transition (applied/interview/offer/...) reflects the StatusHistory row's
    own created_at, not when the application was originally staged. That's
    the standard way a date-filtered funnel behaves -- filtering to "last 30
    days" should show interviews that happened in that window, regardless of
    when the underlying application was first staged.
    """
    end = end_date or dt.datetime.utcnow()

    postings_stmt = select(JobPosting).where(JobPosting.ingested_at <= end)
    if start_date:
        postings_stmt = postings_stmt.where(JobPosting.ingested_at >= start_date)
    postings = db.execute(postings_stmt).scalars().all()

    apps_stmt = select(Application).where(Application.created_at <= end)
    if start_date:
        apps_stmt = apps_stmt.where(Application.created_at >= start_date)
    staged_apps = db.execute(apps_stmt).scalars().all()

    history_stmt = select(StatusHistory).where(StatusHistory.created_at <= end)
    if start_date:
        history_stmt = history_stmt.where(StatusHistory.created_at >= start_date)
    history_rows = db.execute(history_stmt).scalars().all()

    # Source doesn't change over an application's lifetime, so this lookup is
    # built from every application regardless of the date filter -- a status
    # transition that falls inside the range can belong to an application
    # that was staged outside it.
    source_by_app_id = {
        a.id: (a.source_portal or "unknown") for a in db.execute(select(Application)).scalars().all()
    }

    funnel = {"new_matches": len(postings), "staged": len(staged_apps)}
    funnel.update({status: 0 for status in _FUNNEL_STATUSES})
    for h in history_rows:
        if h.new_status in funnel:
            funnel[h.new_status] += 1

    def _rate(numerator: int, denominator: int) -> float | None:
        return round(numerator / denominator, 4) if denominator else None

    conversion_rates = {
        "staged_to_applied": _rate(funnel["applied"], funnel["staged"]),
        "applied_to_interview": _rate(funnel["interview"], funnel["applied"]),
        "interview_to_offer": _rate(funnel["offer"], funnel["interview"]),
    }

    daily: dict[str, dict[str, int]] = {}

    def _day_bucket(when: dt.datetime) -> dict[str, int]:
        key = when.date().isoformat()
        return daily.setdefault(key, {"new_matches": 0, "staged": 0, "applied": 0})

    for p in postings:
        _day_bucket(p.ingested_at)["new_matches"] += 1
    for a in staged_apps:
        _day_bucket(a.created_at)["staged"] += 1
    for h in history_rows:
        if h.new_status == "applied":
            _day_bucket(h.created_at)["applied"] += 1

    activity_over_time = [{"date": day, **counts} for day, counts in sorted(daily.items())]

    source_matches: Counter = Counter(p.source for p in postings)
    source_staged: Counter = Counter(source_by_app_id.get(a.id, "unknown") for a in staged_apps)
    source_status: dict[str, Counter] = {}
    for h in history_rows:
        src = source_by_app_id.get(h.application_id, "unknown")
        source_status.setdefault(src, Counter())[h.new_status] += 1

    all_sources = sorted(set(source_matches) | set(source_staged) | set(source_status))
    source_effectiveness = [
        {
            "source": s,
            "matches": source_matches.get(s, 0),
            "staged": source_staged.get(s, 0),
            "applied": source_status.get(s, Counter()).get("applied", 0),
            "interview": source_status.get(s, Counter()).get("interview", 0),
            "offer": source_status.get(s, Counter()).get("offer", 0),
        }
        for s in all_sources
    ]

    bucket_counts = [0] * len(_SCORE_BUCKET_LABELS)
    for p in postings:
        if p.keyword_match_score is None:
            continue
        for i, label in enumerate(_SCORE_BUCKET_LABELS):
            if _SCORE_BUCKETS[i] <= p.keyword_match_score < _SCORE_BUCKETS[i + 1]:
                bucket_counts[i] += 1
                break
    match_score_distribution = [
        {"bucket": label, "count": count} for label, count in zip(_SCORE_BUCKET_LABELS, bucket_counts)
    ]

    keyword_counter: Counter = Counter()
    for p in postings:
        if p.matched_keywords:
            keyword_counter.update(p.matched_keywords)
    top_keywords = [{"keyword": k, "count": c} for k, c in keyword_counter.most_common(15)]

    return {
        "range": {"start": start_date.isoformat() if start_date else None, "end": end.isoformat()},
        "funnel": funnel,
        "conversion_rates": conversion_rates,
        "activity_over_time": activity_over_time,
        "source_effectiveness": source_effectiveness,
        "match_score_distribution": match_score_distribution,
        "top_keywords": top_keywords,
    }
