"""Retrieval-Augmented Generation for skill matching: embeds your skill
profile once (stored in Postgres via pgvector) and retrieves only the top-K
most semantically relevant skills for a given job description, instead of
sending your entire ~76-item profile to the LLM on every call.

This does double duty: it's a genuine RAG pipeline (embed -> store -> vector
similarity retrieve -> augment the LLM prompt with just the retrieved
context), and it directly reduces per-call token usage, which is the actual
fix for the rate-limit incidents this project hit -- sending 15 retrieved
skills instead of 76 roughly quarters the skill-list portion of every prompt.

Uses fastembed (ONNX runtime) rather than sentence-transformers/torch --
same quality of dense embeddings for this purpose, without pulling a
multi-hundred-MB deep learning framework into a GitHub Actions runner that
reinstalls dependencies from scratch on every run, or into Render's build.
"""

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIM = 384

_model = None


def _get_model():
    global _model
    if _model is None:
        from fastembed import TextEmbedding

        _model = TextEmbedding(model_name=EMBEDDING_MODEL_NAME)
    return _model


def embed_text(text_to_embed: str) -> list[float]:
    """Embeds a single string. fastembed's embed() is a generator over a batch
    even for one input -- list()[0] pulls out the one vector.
    """
    vector = list(_get_model().embed([text_to_embed]))[0]
    return vector.tolist()


def backfill_skill_embeddings(engine: Engine) -> int:
    """Computes and stores an embedding for every active skill_profile_items
    row missing one. Run this once after seeding/editing your skill profile
    (see docs/SETUP.md) -- not run automatically on every ingestion, since
    your skill profile changes rarely compared to how often ingestion runs.
    """
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT id, skill_name, evidence_bullet FROM skill_profile_items "
                "WHERE is_active = TRUE AND embedding IS NULL"
            )
        ).fetchall()

    updated = 0
    with engine.begin() as conn:
        for row in rows:
            text_to_embed = row.skill_name if not row.evidence_bullet else f"{row.skill_name}: {row.evidence_bullet}"
            vector = embed_text(text_to_embed)
            # SQLAlchemy's text() treats ':name' as a bind parameter and gets
            # confused when it's immediately followed by Postgres's '::' cast
            # operator -- it silently drops the parameter from the compiled
            # SQL entirely (confirmed in practice: a real run hit "syntax
            # error at or near ':'" because :embedding never got substituted).
            # Escaping each colon in '::' as '\:\:' is SQLAlchemy's documented
            # fix for a literal colon that isn't a bind parameter.
            conn.execute(
                text(r"UPDATE skill_profile_items SET embedding = :embedding\:\:vector WHERE id = :id"),
                {"embedding": _vector_literal(vector), "id": row.id},
            )
            updated += 1
    return updated


def retrieve_relevant_skills(engine: Engine, jd_text: str, k: int = 15) -> list[str]:
    """Embeds the JD text and returns the top-K most similar skill names via
    pgvector cosine-distance search. Falls back to returning ALL active skill
    names (the old behavior) if embeddings aren't backfilled yet or the
    embedding call fails -- retrieval quality degrading to "everything" is
    safe, just less token-efficient, so this must never raise.
    """
    try:
        query_vector = embed_text(jd_text[:2000])
    except Exception as exc:  # noqa: BLE001 -- embedding failure must degrade, not crash ingestion
        logger.warning("RAG embedding failed, falling back to full skill list: %s", exc)
        return _all_active_skill_names(engine)

    with engine.connect() as conn:
        # Same '\:\:' escape as backfill_skill_embeddings() -- see comment there.
        rows = conn.execute(
            text(
                r"SELECT skill_name FROM skill_profile_items "
                r"WHERE is_active = TRUE AND embedding IS NOT NULL "
                r"ORDER BY embedding <=> :query_vector\:\:vector LIMIT :k"
            ),
            {"query_vector": _vector_literal(query_vector), "k": k},
        ).fetchall()

    if not rows:
        # No embeddings backfilled yet -- fall back rather than retrieve nothing.
        return _all_active_skill_names(engine)

    return [r.skill_name for r in rows]


def _vector_literal(vector: list[float]) -> str:
    """pgvector's text input format: '[0.1,0.2,0.3]', no spaces -- Python's
    default str(list) includes spaces after commas, which some pgvector
    versions are stricter about than others, so build it explicitly.
    """
    return "[" + ",".join(repr(v) for v in vector) + "]"


def _all_active_skill_names(engine: Engine) -> list[str]:
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT skill_name FROM skill_profile_items WHERE is_active = TRUE")
        ).fetchall()
    return [r.skill_name for r in rows]
