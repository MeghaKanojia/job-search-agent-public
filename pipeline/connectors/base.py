import datetime as dt
import hashlib
from dataclasses import dataclass, field


@dataclass
class JobPosting:
    """Common shape every connector normalizes into before landing in Postgres."""

    source: str  # "jobspy_indeed", "jobspy_linkedin", "gmail_linkedin_alert", "irish_boards"
    title: str
    url: str
    company: str | None = None
    location: str | None = None
    description: str | None = None
    salary_text: str | None = None
    source_job_id: str | None = None
    posted_at: dt.datetime | None = None

    def dedup_hash(self) -> str:
        """Same posting from two sources (or re-scraped twice) collapses to one row.

        Keyed on company+title+location rather than URL, since the same posting
        is often re-published under different tracking URLs across boards/refreshes.
        """
        key = f"{(self.company or '').strip().lower()}|{self.title.strip().lower()}|{(self.location or '').strip().lower()}"
        return hashlib.sha256(key.encode()).hexdigest()


@dataclass
class ConnectorResult:
    postings: list[JobPosting] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class Connector:
    """Base interface every source connector implements. Each connector's fetch()
    is wrapped in try/except by run_ingest.py so one source failing never blocks
    the others.
    """

    name: str = "base"

    def fetch(self) -> ConnectorResult:
        raise NotImplementedError
