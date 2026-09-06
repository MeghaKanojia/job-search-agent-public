"""LinkedIn ingestion via Gmail, not LinkedIn's site -- this is the zero-risk half
of LinkedIn coverage (paired with the rate-capped JobSpy unauthenticated search).
Requires the user to have subscribed to LinkedIn job-alert emails for their target
searches (see docs/SETUP.md); parses those digest emails for job title/company/link.
"""

import base64
import json
import logging
import re

from bs4 import BeautifulSoup
from sqlalchemy.engine import Engine

from pipeline.connectors.base import Connector, ConnectorResult, JobPosting
from pipeline.gmail_status_sync.gmail_client import get_gmail_service
from pipeline.llm import chat as llm_chat

logger = logging.getLogger(__name__)

LINKEDIN_ALERT_QUERY = 'from:(jobs-noreply@linkedin.com OR jobalerts-noreply@linkedin.com) newer_than:2d'

# LinkedIn alert emails wrap each job link in a linkedin.com/comm/jobs/view/... redirect;
# titles sit in the anchor text immediately preceding it. This is best-effort HTML
# parsing of an email template LinkedIn controls and can change without notice.
_JOB_LINK_RE = re.compile(
    r'<a[^>]+href="(https://www\.linkedin\.com/comm/jobs/view/[^"]+)"[^>]*>([^<]{5,150})</a>',
    re.IGNORECASE,
)

# The regex above only reliably finds title + link -- the company name sits in
# a sibling element whose exact tag/class LinkedIn doesn't document and can
# change without notice, so a second regex for it would be just as brittle and
# would silently start returning wrong matches the moment the template shifts.
# An LLM reading the email's plain text is far more robust to that kind of
# layout drift. This is a SELECTION/extraction task, not generation: the model
# may only report a company name that is literally present in the email text,
# never infer one from the job title -- same no-fabrication discipline as
# backend/app/services/tailoring.py, just applied to reading instead of writing.
_COMPANY_EXTRACTION_SYSTEM_PROMPT = """You extract company names from a LinkedIn job-alert email's
plain text, for a list of job titles already found in that same email.

Hard rules, non-negotiable:
- Only report a company name if it is literally written in the text near that job's
  title. Never guess, infer, or invent a company from the job title, industry, or
  general knowledge -- if the text doesn't clearly show a company name for a given
  title, report null for it.
- Match each entry to one of the exact job titles given below -- don't rename or
  paraphrase the titles.
- Respond with ONLY a single JSON object, no prose, no markdown fences, in exactly
  this shape: {"companies": {"<exact job title>": "<company name or null>", ...}}"""


def _extract_companies(email_text: str, titles: list[str]) -> dict[str, str | None]:
    """Asks the LLM which company goes with each already-extracted job title, using
    only text present in this one email. Returns {} (meaning "unknown for all of
    them", same as before this existed) if the LLM is unconfigured, the call
    fails, or the response isn't valid JSON -- never raises, never blocks landing
    the postings themselves.
    """
    if not titles:
        return {}
    user_prompt = (
        "Job titles to find companies for (one per line):\n"
        + "\n".join(f"- {t}" for t in titles)
        + "\n\nEmail text:\n"
        + email_text[:6000]
    )
    result = llm_chat(_COMPANY_EXTRACTION_SYSTEM_PROMPT, user_prompt)
    if result is None:
        return {}
    cleaned = result.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.split("\n", 1)[-1] if "\n" in cleaned else cleaned
    try:
        parsed = json.loads(cleaned)
        companies = parsed.get("companies", {})
        return {t: (companies.get(t) or None) for t in titles}
    except (json.JSONDecodeError, AttributeError, TypeError):
        logger.warning("gmail_linkedin: company extraction response wasn't valid JSON")
        return {}


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
                matches = _JOB_LINK_RE.findall(html)
                if not matches:
                    continue

                # One LLM call per email covering every posting in it, not one per
                # posting -- Groq's free tier caps at 1,000 calls/day shared across
                # every LLM feature in this app, and this connector alone can see
                # up to 20 emails per run.
                titles = [title.strip() for _url, title in matches]
                email_text = BeautifulSoup(html, "html.parser").get_text(separator="\n", strip=True)
                companies = _extract_companies(email_text, titles)

                for url, raw_title in matches:
                    title = raw_title.strip()
                    result.postings.append(
                        JobPosting(
                            source="gmail_linkedin_alert",
                            source_job_id=m["id"],
                            title=title,
                            company=companies.get(title),
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
