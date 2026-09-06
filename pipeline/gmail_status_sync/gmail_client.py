"""Shared Gmail OAuth client, used by both the LinkedIn-alert ingestion connector
and the application status-sync scanner. No email account password is ever
stored or used -- only an OAuth refresh token, encrypted at rest in `oauth_tokens`.

One-time setup (see docs/SETUP.md): create a Google Cloud project, enable the
Gmail API, create an OAuth client, and run `python -m pipeline.gmail_status_sync.authorize`
once locally/in Codespaces to mint and store the refresh token.
"""

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from sqlalchemy import text
from sqlalchemy.engine import Engine

from pipeline.common.config import config
from pipeline.common.secrets import decrypt, encrypt

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def load_credentials(engine: Engine) -> Credentials | None:
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT encrypted_access_token, encrypted_refresh_token, scope, expires_at "
                "FROM oauth_tokens WHERE provider = 'gmail'"
            )
        ).fetchone()
    if row is None:
        return None

    creds = Credentials(
        token=decrypt(row.encrypted_access_token),
        refresh_token=decrypt(row.encrypted_refresh_token),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=config.google_oauth_client_id,
        client_secret=config.google_oauth_client_secret,
        scopes=SCOPES,
    )
    if creds.expired:
        creds.refresh(Request())
        save_credentials(engine, creds)
    return creds


def save_credentials(engine: Engine, creds: Credentials) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO oauth_tokens (provider, encrypted_access_token, encrypted_refresh_token, scope, updated_at)
                VALUES ('gmail', :access, :refresh, :scope, NOW())
                ON CONFLICT (provider) DO UPDATE SET
                    encrypted_access_token = :access,
                    encrypted_refresh_token = :refresh,
                    updated_at = NOW()
                """
            ),
            {
                "access": encrypt(creds.token),
                "refresh": encrypt(creds.refresh_token),
                "scope": " ".join(SCOPES),
            },
        )


def get_gmail_service(engine: Engine):
    creds = load_credentials(engine)
    if creds is None:
        raise RuntimeError(
            "No Gmail OAuth token stored. Run `python -m pipeline.gmail_status_sync.authorize` "
            "once to authorize and store a refresh token."
        )
    return build("gmail", "v1", credentials=creds)
