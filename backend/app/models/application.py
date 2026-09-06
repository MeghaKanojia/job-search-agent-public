import datetime as dt
import enum

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ApplicationStatus(str, enum.Enum):
    NEW = "new"
    STAGED_FOR_REVIEW = "staged_for_review"
    APPROVED_READY_TO_SUBMIT = "approved_ready_to_submit"
    APPLIED = "applied"
    VIEWED = "viewed"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_posting_id: Mapped[int] = mapped_column(ForeignKey("job_postings.id"))
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_portal: Mapped[str | None] = mapped_column(String(50), nullable=True)
    jd_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_skills_matched: Mapped[list | None] = mapped_column(JSON, nullable=True)
    status: Mapped[ApplicationStatus] = mapped_column(
        # values_callable is required here -- SQLAlchemy's Enum column type stores
        # the Python enum's NAME ("STAGED_FOR_REVIEW") by default, not its value
        # ("staged_for_review"), even though this class mixes in str. The Postgres
        # enum type in schema.sql only accepts the lowercase values, so without
        # this every insert/update was rejected with "invalid input value for
        # enum application_status" -- which is why Stage for review did nothing.
        Enum(ApplicationStatus, values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        default=ApplicationStatus.NEW,
    )
    applied_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    last_status_change_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=dt.datetime.utcnow
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)