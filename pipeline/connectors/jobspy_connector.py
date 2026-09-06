"""Automated Indeed/Glassdoor/ZipRecruiter/Google-for-Jobs/LinkedIn ingestion via
JobSpy (https://github.com/speedyapply/JobSpy) — MIT-licensed, no API key, no login.

Indeed has no meaningful rate limiting for this per current reviews, so it runs
at the normal 4h GH Actions cadence. LinkedIn's unauthenticated search rate-limits
a single IP around page 10 of results, so it's capped much more conservatively
here and backs off rather than pushing through -- LinkedIn login/Easy-Apply
automation remains explicitly out of scope regardless (that's a different, much
higher-risk category: this connector never logs in).
"""

import datetime as dt
import logging

import pandas as pd
from jobspy import scrape_jobs

from pipeline.connectors.base import Connector, ConnectorResult, JobPosting

logger = logging.getLogger(__name__)

# Sites carrying the same "unauthenticated, no account to ban" risk profile as Indeed.
LOW_RISK_SITES = ["indeed", "glassdoor", "zip_recruiter", "google"]

# LinkedIn is unauthenticated too (no login = no account-ban risk) but rate-limits
# hard, so it's requested separately with a much smaller results_wanted.
LINKEDIN_SITE = "linkedin"
LINKEDIN_MAX_RESULTS = 40  # stays well under the ~page-10 limit that triggers 429s


class JobSpyConnector(Connector):
    name = "jobspy"

    def __init__(self, search_terms: list[str], location: str = "Ireland", results_wanted: int = 40):
        self.search_terms = search_terms
        self.location = location
        self.results_wanted = results_wanted

    def fetch(self) -> ConnectorResult:
        result = ConnectorResult()

        for term in self.search_terms:
            result = self._fetch_one(term, LOW_RISK_SITES, self.results_wanted, result)
            result = self._fetch_one(term, [LINKEDIN_SITE], LINKEDIN_MAX_RESULTS, result)

        return result

    def _fetch_one(
        self, term: str, sites: list[str], results_wanted: int, result: ConnectorResult
    ) -> ConnectorResult:
        try:
            df = scrape_jobs(
                site_name=sites,
                search_term=term,
                location=self.location,
                results_wanted=results_wanted,
                # 7 days, not 2 -- Ireland's DE/DA/DS/AI-ML market is small enough that a
                # 48h window was cutting out plenty of postings that are a few days old
                # but still open. Dedup on landing means re-seeing the same postings
                # across runs is harmless; it just means newly_landed reflects genuinely
                # new ones while still catching postings missed by a skipped run.
                hours_old=168,
                country_indeed="Ireland",
            )
        except Exception as exc:  # noqa: BLE001 -- one bad term/site must not kill the whole run
            msg = f"jobspy fetch failed for term={term!r} sites={sites}: {exc}"
            logger.warning(msg)
            result.errors.append(msg)
            return result

        # Column names below match python-jobspy 1.1.x's scrape_jobs() output as of
        # this writing -- verify against `df.columns` if JobSpy is upgraded, since
        # it queries each site's unofficial internal API and its own schema can shift.
        for _, row in df.iterrows():
            posted_at = None
            raw_date = _clean(row.get("date_posted"))
            if raw_date is not None:
                try:
                    posted_at = dt.datetime.combine(raw_date, dt.time.min)
                except (TypeError, ValueError):
                    pass

            result.postings.append(
                JobPosting(
                    source=f"jobspy_{_clean(row.get('site')) or 'unknown'}",
                    source_job_id=_clean(row.get("id")),
                    title=_clean(row.get("title")) or "",
                    company=_clean(row.get("company")),
                    location=_clean(row.get("location")),
                    url=_clean(row.get("job_url")) or "",
                    description=_clean(row.get("description")),
                    salary_text=_clean(row.get("salary_source")),
                    posted_at=posted_at,
                )
            )
        return result


def _clean(value):
    """Pandas represents a missing cell (e.g. a job with no listed company) as
    NaN -- a Python float, not None. That NaN flows straight through into
    JobPosting and, when JSON-serialized for raw_ingest_events.payload, becomes
    the literal token `NaN`, which is invalid JSON per spec and gets rejected by
    Postgres's strict JSON parser (observed in practice: a real ingestion run
    crashed on exactly this for a posting with no company listed). Every value
    pulled from a DataFrame row must go through this before use.
    """
    if pd.isna(value):
        return None
    return str(value) if not isinstance(value, (dt.date, dt.datetime)) else value
