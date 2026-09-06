import datetime as dt

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class KeywordFilter(Base):
    """Your editable role/skill filter list: controls what the pipeline ingests at all."""

    __tablename__ = "keyword_filters"

    id: Mapped[int] = mapped_column(primary_key=True)
    pipeline: Mapped[str] = mapped_column(String(50), default="professional")
    keyword: Mapped[str] = mapped_column(String(255))
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)  # "role" | "skill"
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)


class PipelineSetting(Base):
    """Schedule config, per-source enable flags, rate-limit state. Persists across
    ephemeral GitHub Actions runners since each run reads/writes this table.
    """

    __tablename__ = "pipeline_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(255), unique=True)
    value: Mapped[dict] = mapped_column(JSON)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow
    )
