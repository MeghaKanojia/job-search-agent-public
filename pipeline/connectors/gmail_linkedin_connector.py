"""LinkedIn ingestion via Gmail, not LinkedIn's site -- this is the zero-risk half
of LinkedIn coverage (paired with the rate-capped JobSpy unauthenticated search).
Requires the user to have subscribed to LinkedIn job-alert emails for their target
searches (see docs/SETUP.md); parses those digest emails for job title/company/link.
"""

import base64
import logging
import re

from sqlalchemy.engine import Engine

from pipeline.connectors.base import Connector, ConnectorResult, JobPosting
from pipeline.gmail_status_sync.gmail_client import get_gmail_service

logger = logging.getLogger(__name__)

LINKEDIN_ALERT_QUERY = 'from:(jobs-noreply@linkedin.com OR jobalerts-noreply@linkedin.com) newer_than:2d'

# LinkedIn alert emails wrap each job link in a linkedin.com/comm/jobs/view/... redirect;
# titles sit in the anchor text immediately preceding it. This is best-effort HTML
# parsing of an email template LinkedIn controls and can change without notice.
_JOB_LINK_RE = re.compile(
    r'<a[^>]+href="(https://www\.linkedin\.com/comm/jobs/view/[^"]+)"[^>]*>([^<]{5,150})</a>',
    re.IGNORECASE,
)


class GmailLinkedInConnector(Connector):
    name = "gmail_linkedin"

    def __init__(self, engine: Engine):
        self.engine = engine

    def fetch(self) -> ConnectorResult:
        result = ConnectorResult()
        try:
            service = get_gmail_service(self.engine)
        except RuntimeError as exc:
            result.errors.append(str(exc))
            return result

        try:
            messages = (
                service.users()
                .messages()
                .list(userId="me", q=LINKEDIN_ALERT_QUERY, maxResults=20)
                .execute()
                .get("messages", [])
            )
        except Exception as exc:  # noqa: BLE001
            msg = f"gmail_linkedin: failed to list messages: {exc}"
            logger.warning(msg)
            result.errors.append(msg)
            return result

        for m in messages:
            try:
                full = service.users().messages().get(userId="me", id=m["id"], format="full").execute()
                html = _extract_html(full)
                if not html:
                    continue
                for url, title in _JOB_LINK_RE.findall(html):
                    result.postings.append(
                        JobPosting(
                            source="gmail_linkedin_alert",
                            source_job_id=m["id"],
                            title=title.strip(),
                            url=url,
                        )
                    )
            except Exception as exc:  # noqa: BLE001 -- one malformed email must not kill the run
                logger.warning("gmail_linkedin: failed to parse message %s: %s", m["id"], exc)

        return result


def _extract_html(message: dict) -> str | None:
    payload = message.get("payload", {})
    parts = payload.get("parts") or [payload]
    for part in parts:
        if part.get("mimeType") == "text/html":
            data = part.get("body", {}).get("data")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
    return None
