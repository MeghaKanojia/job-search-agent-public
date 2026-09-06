"""IrishJobs.ie / Jobs.ie -- both Disallow their RSS path in robots.txt, so this
is deliberately NOT treated as clean official access. Per your decision: proceed
at low volume (max 3x/day, enforced by rate_limiter against Postgres state, not
just the GH Actions cron frequency), respectful identifying User-Agent, back off
hard on any 429/403, and an instant kill switch via pipeline_settings.

Requires a manually-obtained saved-search URL (see docs/SETUP.md) -- there is no
sanctioned API, so this connector is best-effort and expected to need occasional
maintenance if the page structure changes.
"""

import logging

import requests
from bs4 import BeautifulSoup
from sqlalchemy.engine import Engine

from pipeline.common.rate_limiter import allowed_to_run, record_run
from pipeline.connectors.base import Connector, ConnectorResult, JobPosting

logger = logging.getLogger(__name__)

USER_AGENT = "job-search-agent-personal-use/1.0 (+low-volume, non-commercial, 3x/day cap)"
MAX_RUNS_PER_DAY = 3
MIN_INTERVAL_HOURS = 6  # ~3x/day spaced out, not three requests back-to-back


class IrishBoardsConnector(Connector):
    name = "irish_boards"

    def __init__(self, search_url: str, engine: Engine):
        self.search_url = search_url
        self.engine = engine

    def fetch(self) -> ConnectorResult:
        result = ConnectorResult()

        if not self.search_url:
            result.errors.append("irish_boards: no search URL configured, skipping")
            return result

        if not allowed_to_run(self.engine, self.name, MIN_INTERVAL_HOURS, MAX_RUNS_PER_DAY):
            logger.info("irish_boards: skipping run, rate cap already hit for today")
            return result

        try:
            resp = requests.get(
                self.search_url, headers={"User-Agent": USER_AGENT}, timeout=15
            )
            if resp.status_code == 429:
                logger.warning("irish_boards: got 429, backing off -- not retrying this run")
                result.errors.append("irish_boards: rate limited (429)")
                return result
            resp.raise_for_status()
        except requests.RequestException as exc:
            msg = f"irish_boards fetch failed: {exc}"
            logger.warning(msg)
            result.errors.append(msg)
            return result

        record_run(self.engine, self.name)

        # Structure is best-effort and will need adjusting to the real saved-search
        # page markup -- these selectors are placeholders, not verified against the
        # live site, since the URL itself is user-supplied and not publicly documented.
        soup = BeautifulSoup(resp.text, "html.parser")
        for card in soup.select("[data-job-card], .job-result, article"):
            title_el = card.select_one("h2, h3, .job-title, a")
            if not title_el:
                continue
            link_el = card.select_one("a[href]")
            result.postings.append(
                JobPosting(
                    source="irish_boards",
                    title=title_el.get_text(strip=True),
                    company=_text_or_none(card.select_one(".company, .job-company")),
                    location=_text_or_none(card.select_one(".location, .job-location")),
                    url=link_el["href"] if link_el else self.search_url,
                    description=_text_or_none(card.select_one(".summary, .job-summary")),
                )
            )
        return result


def _text_or_none(el) -> str | None:
    return el.get_text(strip=True) if el else None
