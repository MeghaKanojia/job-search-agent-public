import datetime as dt

from sqlalchemy import Boolean, Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Certification(Base):
    """Covers both certifications and notable awards -- the source CV groups
    them under one "Certifications & Awards" section, and splitting them into
    two tables wasn't worth it for what's otherwise identical shape (a name,
    an issuer, a date).
    """

    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    issuing_organization: Mapped[str | None] = mapped_column(String(255), nullable=True)
    issue_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    credential_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow
    )
