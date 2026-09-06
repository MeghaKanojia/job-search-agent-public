import datetime as dt

from sqlalchemy import DateTime, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Credential(Base):
    """Encrypted-at-rest secrets only. Never store plaintext passwords.

    The encryption key lives in the ENCRYPTION_KEY env var (see app/core/security.py),
    never in this table and never in source control. LinkedIn login credentials must
    never be stored here, LinkedIn is not automated via login, only via unauthenticated
    search (JobSpy) and Gmail alert parsing.
    """

    __tablename__ = "credentials"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(100))
    encrypted_blob: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow
    )
    expires_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)


class OAuthToken(Base):
    """OAuth tokens (Gmail, etc.), encrypted at rest, refreshed via the provider's
    OAuth flow rather than ever storing an account password.
    """

    __tablename__ = "oauth_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(100), unique=True)
    encrypted_access_token: Mapped[bytes] = mapped_column(LargeBinary)
    encrypted_refresh_token: Mapped[bytes] = mapped_column(LargeBinary)
    scope: Mapped[str | None] = mapped_column(String(500), nullable=True)
    expires_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow
    )
