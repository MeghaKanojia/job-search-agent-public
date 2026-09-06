import datetime as dt

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class StatusUpdateProposal(Base):
    """A Gmail-derived guess at a status change. Always surfaced for the user to
    confirm/correct in the dashboard — never silently applied to `applications.status`.
    """

    __tablename__ = "status_update_proposals"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"))
    proposed_status: Mapped[str] = mapped_column(String(50))
    evidence_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    gmail_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_status: Mapped[str | None] = mapped_column(String(50), nullable=True)


class StatusHistory(Base):
    __tablename__ = "status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"))
    old_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    new_status: Mapped[str] = mapped_column(String(50))
    changed_by: Mapped[str] = mapped_column(String(20))  # "user" | "auto_gmail"
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
