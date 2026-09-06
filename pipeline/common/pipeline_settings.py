"""Per-source enable/disable state, set via the dashboard's Settings page
(backend/app/api/routes/settings.py) -- the "instant kill switch" promised in
irish_boards_connector.py's docstring, actually wired into run_ingest.py here
rather than existing only as a rate-limit cap. Same pipeline_settings table
rate_limiter.py already uses for run-frequency state, keyed separately
("source_enabled:<name>" vs "rate_limit:<name>") so the two never collide.
"""

from sqlalchemy import text
from sqlalchemy.engine import Engine


def is_source_enabled(engine: Engine, source: str) -> bool:
    """Defaults to True (running) for a source that's never been explicitly
    toggled off -- matches the Settings API's own default, so an untouched
    source behaves exactly as it always has.
    """
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT value FROM pipeline_settings WHERE key = :key"),
            {"key": f"source_enabled:{source}"},
        ).fetchone()
    if row is None:
        return True
    return bool(row[0].get("enabled", True))
