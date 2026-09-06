import datetime as dt
import enum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, LargeBinary, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class DocumentType(str, enum.Enum):
    RESUME = "resume"
    COVER_LETTER = "cover_letter"


class Document(Base):
    """A generated resume/cover-letter file, one row per version, tied to one application.

    Stored as raw bytes in Postgres rather than an object store — Render's free
    web-service filesystem is ephemeral (wiped on redeploy), and volume here is
    a handful of small PDFs, not worth adding S3/R2 credentials for.
    """

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"))
    # values_callable required -- see the identical fix + explanation on
    # Application.status in app/models/application.py.
    doc_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType, values_callable=lambda enum_cls: [e.value for e in enum_cls])
    )
    file_bytes: Mapped[bytes] = mapped_column(LargeBinary)
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    generated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
