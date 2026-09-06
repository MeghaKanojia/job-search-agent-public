"""Gates every dashboard API route behind one shared username/password.

This is a single-user tool with no per-account system. Locally/in the Codespace
that was never a problem -- nothing outside your own GitHub-authenticated
Codespace could reach it. Once deployed, the backend is a public URL with no
other access control in front of it, so this is the only thing standing between
the open internet and: your generated resume PDFs (phone number, email, full
work history), your application tracker, your profile data, and the ability to
burn your LLM quota or delete your data via the write endpoints.

DASHBOARD_USERNAME/DASHBOARD_PASSWORD live only as a Render environment
variable, entered once per browser session via the dashboard's own login
screen (frontend/src/components/Login.tsx) -- never hardcoded, never shipped
in the frontend bundle (VITE_-prefixed env vars get bundled into public JS,
so a real secret can never go through that path).
"""

import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.core.config import settings

_security = HTTPBasic()


def require_auth(credentials: HTTPBasicCredentials = Depends(_security)) -> None:
    if not settings.dashboard_username or not settings.dashboard_password:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DASHBOARD_USERNAME/DASHBOARD_PASSWORD are not configured on the server.",
        )
    # compare_digest avoids a timing side-channel on the comparison -- a naive
    # `==` leaks how many leading characters matched via response time.
    valid_username = secrets.compare_digest(credentials.username, settings.dashboard_username)
    valid_password = secrets.compare_digest(credentials.password, settings.dashboard_password)
    if not (valid_username and valid_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
