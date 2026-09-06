"""Same RAG retrieval as pipeline/rag.py, duplicated for this separately-
deployed process, using the ORM's pgvector integration instead of raw SQL
since the backend already has SkillProfileItem as a model. See pipeline/rag.py
for the full design rationale (fastembed over sentence-transformers/torch to
keep the install light; falls back to the full skill list on any failure).
"""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.skill_profile import SkillProfileItem

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    global _model
    if _model is None:
        from fastembed import TextEmbedding

        _model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    return _model


def embed_text(text_to_embed: str) -> list[float]:
    vector = list(_get_model().embed([text_to_embed]))[0]
    return vector.tolist()


def retrieve_relevant_skills(db: Session, jd_text: str, k: int = 15) -> list[SkillProfileItem]:
    """Returns the top-K most semantically relevant active skill_profile_items
    for the given JD text, via pgvector cosine-distance search. Falls back to
    ALL active items if embedding fails or none are backfilled yet -- must
    never raise or return nothing when items exist.
    """
    items, _degraded = retrieve_relevant_skills_with_status(db, jd_text, k)
    return items


def retrieve_relevant_skills_with_status(db: Session, jd_text: str, k: int = 15) -> tuple[list[SkillProfileItem], bool]:
    """Same as retrieve_relevant_skills, but also reports whether it had to
    degrade to the full active list (embedding failure, or nothing backfilled
    yet) instead of a genuine semantic top-K. Most callers don't care and use
    retrieve_relevant_skills; the resume generator's tailoring-transparency
    warnings use this directly so it can tell the user semantic matching
    didn't actually run this time, rather than looking silently normal.
    """
    try:
        query_vector = embed_text(jd_text[:2000])
    except Exception as exc:  # noqa: BLE001 -- embedding failure must degrade, not crash the request
        logger.warning("RAG embedding failed, falling back to full skill list: %s", exc)
        return _all_active(db), True

    stmt = (
        select(SkillProfileItem)
        .where(SkillProfileItem.is_active.is_(True))
        .where(SkillProfileItem.embedding.is_not(None))
        .order_by(SkillProfileItem.embedding.cosine_distance(query_vector))
        .limit(k)
    )
    results = db.execute(stmt).scalars().all()
    if results:
        return list(results), False
    return _all_active(db), True


def _all_active(db: Session) -> list[SkillProfileItem]:
    stmt = select(SkillProfileItem).where(SkillProfileItem.is_active.is_(True))
    return list(db.execute(stmt).scalars().all())
