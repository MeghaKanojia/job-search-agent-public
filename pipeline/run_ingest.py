"""Entrypoint for .github/workflows/ingest-professional.yml.

Calls every source connector with per-source isolation (one failing must never
block the others), applies the keyword filter, and lands results in Postgres.
Databricks scoring/cleanup runs independently on its own native schedule -- this
script never calls Databricks.
"""

import logging
import sys
import uuid

from sqlalchemy import create_engine

from pipeline.common.config import config
from pipeline.common.pipeline_settings import is_source_enabled
from pipeline.connectors.base import ConnectorResult
from pipeline.connectors.gmail_linkedin_connector import GmailLinkedInConnector
from pipeline.connectors.irish_boards_connector import IrishBoardsConnector
from pipeline.connectors.jobspy_connector import JobSpyConnector
from pipeline.keyword_filter import filter_postings, load_active_keywords
from pipeline.landing.land_to_postgres import land_postings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("run_ingest")


def main() -> int:
    if not config.database_url:
        logger.error("DATABASE_URL is not set")
        return 1

    engine = create_engine(config.database_url, pool_pre_ping=True)
    batch_id = str(uuid.uuid4())
    # Skill keywords from keyword_filters are unused here on purpose -- skill relevance
    # is now reflected in keyword_match_score (computed from skill_profile_items at
    # landing time, see pipeline/scoring.py) rather than as a hard pre-landing filter.
    role_keywords, _skill_keywords = load_active_keywords(engine, pipeline="professional")

    connectors = [
        JobSpyConnector(search_terms=config.search_terms, location=config.search_location),
        GmailLinkedInConnector(engine=engine),
        IrishBoardsConnector(search_url=config.irish_boards_search_url, engine=engine),
    ]

    total_landed = 0
    for connector in connectors:
        if not is_source_enabled(engine, connector.name):
            logger.info("skipping connector %s: disabled via Settings", connector.name)
            continue

        logger.info("running connector: %s", connector.name)
        try:
            result: ConnectorResult = connector.fetch()
        except Exception:  # noqa: BLE001 -- a connector crashing must not stop the batch
            logger.exception("connector %s raised unexpectedly, skipping", connector.name)
            continue

        for err in result.errors:
            logger.warning("[%s] %s", connector.name, err)

        filtered = filter_postings(result.postings, role_keywords)
        landed = land_postings(engine, connector.name, batch_id, filtered)
        total_landed += landed
        logger.info(
            "%s: fetched=%d matched_filters=%d newly_landed=%d",
            connector.name,
            len(result.postings),
            len(filtered),
            landed,
        )

    logger.info("run complete, batch_id=%s total_newly_landed=%d", batch_id, total_landed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
