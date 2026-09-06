import datetime as dt

from sqlalchemy import JSON, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class JobPosting(Base):
    __tablename__ = "job_postings"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(50))  # e.g. "jobspy_indeed", "gmail_linkedin"
    source_job_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str] = mapped_column(String(500))
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url: Mapped[str] = mapped_column(Text)
    description_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_clean: Mapped[str | None] = mapped_column(Text, nullable=True)
    salary_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    posted_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    ingested_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    keyword_match_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    matched_keywords: Mapped[list | None] = mapped_column(JSON, nullable=True)
    relevance_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    dedup_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)