"""Entrypoint for .github/workflows/gmail-status-sync.yml.

Scans recent Gmail for replies that look like rejection/interview/acknowledgement
language matching a tracked application's company name, and writes a
`status_update_proposals` row. Never writes directly to `applications.status` --
you always confirm or correct these in the dashboard first.
"""

import logging
import sys

from sqlalchemy import create_engine, text

from pipeline import llm
from pipeline.common.config import config
from pipeline.gmail_status_sync.gmail_client import get_gmail_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("status_scanner")

# Fallback for when the LLM is unavailable/unconfigured/fails -- deliberately
# simple/explainable keyword heuristics. A real rejection email that doesn't
# happen to contain one of these exact phrases gets missed entirely, which is
# exactly the gap the LLM classifier below is meant to close.
_SIGNALS = {
    "rejected": ["unfortunately", "not moving forward", "other candidates", "regret to inform"],
    "interview": ["interview", "schedule a call", "next steps", "would like to speak"],
    "viewed": ["thank you for applying", "received your application", "application received"],
}

_CLASSIFY_SYSTEM_PROMPT = """You classify a short email snippet related to a job application.
Respond with EXACTLY ONE WORD from this list, nothing else: rejected, interview, viewed, none.
- rejected: the email says the candidate was not selected / application unsuccessful.
- interview: the email invites the candidate to an interview, call, or next round.
- viewed: the email is just an acknowledgement that the application was received (no decision yet).
- none: the email doesn't clearly indicate any of the above, or isn't about a job application status.
If genuinely ambiguous, respond none rather than guessing."""


def main() -> int:
    if not config.database_url:
        logger.error("DATABASE_URL is not set")
        return 1

    engine = create_engine(config.database_url, pool_pre_ping=True)

    try:
        service = get_gmail_service(engine)
    except RuntimeError as exc:
        logger.error(str(exc))
        return 1

    with engine.connect() as conn:
        applications = conn.execute(
            text(
                "SELECT id, company FROM applications "
                "WHERE status NOT IN ('rejected', 'withdrawn', 'offer') AND company IS NOT NULL"
            )
        ).fetchall()

    proposals_written = 0
    for app in applications:
        query = f'"{app.company}" newer_than:14d'
        try:
            messages = (
                service.users()
                .messages()
                .list(userId="me", q=query, maxResults=10)
                .execute()
                .get("messages", [])
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("gmail search failed for company=%s: %s", app.company, exc)
            continue

        for m in messages:
            full = service.users().messages().get(userId="me", id=m["id"], format="full").execute()
            snippet = full.get("snippet", "")
            proposed_status, confidence = _classify(snippet)
            if proposed_status is None:
                continue

            with engine.begin() as conn:
                already_proposed = conn.execute(
                    text(
                        "SELECT 1 FROM status_update_proposals "
                        "WHERE application_id = :app_id AND gmail_message_id = :msg_id"
                    ),
                    {"app_id": app.id, "msg_id": m["id"]},
                ).fetchone()
                if already_proposed:
                    continue

                conn.execute(
                    text(
                        """
                        INSERT INTO status_update_proposals
                            (application_id, proposed_status, evidence_snippet, gmail_message_id, confidence)
                        VALUES (:app_id, :status, :snippet, :msg_id, :confidence)
                        """
                    ),
                    {
                        "app_id": app.id,
                        "status": proposed_status,
                        "snippet": full.get("snippet", ""),
                        "msg_id": m["id"],
                        "confidence": confidence,
                    },
                )
                proposals_written += 1

    logger.info("status scan complete, proposals_written=%d", proposals_written)
    return 0


def _classify(snippet: str) -> tuple[str | None, float]:
    """Tries the LLM first (handles phrasing the keyword list never anticipated),
    falls back to keyword matching if the LLM is unconfigured or fails, or if it
    returns something unparseable. Confidence reflects which path produced the
    answer, not a calibrated probability.
    """
    llm_result = llm.chat(_CLASSIFY_SYSTEM_PROMPT, snippet)
    if llm_result is not None:
        answer = llm_result.strip().lower()
        if answer in ("rejected", "interview", "viewed"):
            return answer, 0.8
        if answer == "none":
            return None, 0.0
        logger.warning("llm classifier returned unparseable output %r, falling back to keywords", llm_result)

    snippet_lower = snippet.lower()
    for status, signals in _SIGNALS.items():
        if any(s in snippet_lower for s in signals):
            return status, 0.6
    return None, 0.0


if __name__ == "__main__":
    sys.exit(main())
