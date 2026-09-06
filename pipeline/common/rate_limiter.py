"""Persistent rate-limit/backoff state for sources we deliberately under-hit
(IrishJobs.ie/Jobs.ie, LinkedIn via JobSpy). State lives in Postgres
`pipeline_settings` because GitHub Actions runners are ephemeral -- an in-memory
counter would reset every run and defeat the whole point of capping frequency.
"""

import datetime as dt

from sqlalchemy import text
from sqlalchemy.engine import Engine


def _get_setting(engine: Engine, key: str) -> dict | None:
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT value FROM pipeline_settings WHERE key = :key"), {"key": key}
        ).fetchone()
        return row[0] if row else None


def _set_setting(engine: Engine, key: str, value: dict) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO pipeline_settings (key, value, updated_at)
                VALUES (:key, :value, NOW())
                ON CONFLICT (key) DO UPDATE SET value = :value, updated_at = NOW()
                """
            ),
            {"key": key, "value": value},
        )


def allowed_to_run(engine: Engine, source: str, min_interval_hours: float, max_per_day: int) -> bool:
    """Enforces both a minimum gap between runs and a hard daily cap, independent
    of how often the GitHub Actions cron itself fires.
    """
    state_key = f"rate_limit:{source}"
    state = _get_setting(engine, state_key) or {"last_run": None, "runs_today": 0, "day": None}

    now = dt.datetime.utcnow()
    today = now.date().isoformat()

    if state.get("day") != today:
        state = {"last_run": state.get("last_run"), "runs_today": 0, "day": today}

    if state["runs_today"] >= max_per_day:
        return False

    if state["last_run"]:
        last_run = dt.datetime.fromisoformat(state["last_run"])
        if (now - last_run).total_seconds() < min_interval_hours * 3600:
            return False

    return True


def record_run(engine: Engine, source: str) -> None:
    state_key = f"rate_limit:{source}"
    now = dt.datetime.utcnow()
    today = now.date().isoformat()
    state = _get_setting(engine, state_key) or {"runs_today": 0, "day": today}
    if state.get("day") != today:
        state = {"runs_today": 0, "day": today}
    state["runs_today"] += 1
    state["last_run"] = now.isoformat()
    state["day"] = today
    _set_setting(engine, state_key, state)
