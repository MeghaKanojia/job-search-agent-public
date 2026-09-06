import datetime as dt

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

# Must match pipeline/rag.py's EMBEDDING_DIM (fastembed's BAAI/bge-small-en-v1.5).
EMBEDDING_DIM = 384


class SkillProfileItem(Base):
    """Your truthful, self-reported skills: the ONLY source CV tailoring may draw
    from. tailoring.py must never emit a skill absent from this table.
    """

    __tablename__ = "skill_profile_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    skill_name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    proficiency_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    years_experience: Mapped[float | None] = mapped_column(nullable=True)
    evidence_bullet: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow
    )
    # NULL until pipeline/rag.py's backfill_skill_embeddings() runs.
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
