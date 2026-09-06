"""One-time local/Codespaces script: run this once after creating your Google
Cloud OAuth client to mint a refresh token and store it (encrypted) in
`oauth_tokens`. After this, the pipeline refreshes automatically -- your Gmail
account password is never seen or stored anywhere.

Usage:
    python -m pipeline.gmail_status_sync.authorize
"""

from google_auth_oauthlib.flow import InstalledAppFlow
from sqlalchemy import create_engine

from pipeline.common.config import config
from pipeline.gmail_status_sync.gmail_client import SCOPES, save_credentials

CLIENT_CONFIG = {
    "installed": {
        "client_id": config.google_oauth_client_id,
        "client_secret": config.google_oauth_client_secret,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost"],
    }
}


def main() -> None:
    if not config.google_oauth_client_id or not config.google_oauth_client_secret:
        raise SystemExit(
            "Set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET before running this."
        )
    if not config.database_url:
        raise SystemExit("Set DATABASE_URL before running this.")

    flow = InstalledAppFlow.from_client_config(CLIENT_CONFIG, SCOPES)
    creds = flow.run_local_server(port=0)

    engine = create_engine(config.database_url)
    save_credentials(engine, creds)
    print("Gmail OAuth token stored (encrypted) in oauth_tokens. You're set.")


if __name__ == "__main__":
    main()
