"""Same circuit-breaker/rate-limiting base as pipeline/llm/base.py, duplicated
because the backend is a separately-deployed process. See that module's
docstring for the reasoning: a long retry-after means a daily quota, not a
per-minute window, so it must not be slept through.
"""

import logging
import threading
import time

logger = logging.getLogger(__name__)


class RateLimitedProvider:
    name: str = "base"
    min_interval_seconds: float = 5.0
    long_backoff_threshold_seconds: float = 60.0

    def __init__(self):
        self._lock = threading.Lock()
        self._last_call_time = 0.0
        self._unavailable_until = 0.0

    def is_configured(self) -> bool:
        raise NotImplementedError

    def _request(self, system_prompt: str, user_prompt: str) -> tuple[int, float | None, str | None]:
        raise NotImplementedError

    def _throttle(self) -> None:
        with self._lock:
            wait = self.min_interval_seconds - (time.monotonic() - self._last_call_time)
            if wait > 0:
                time.sleep(wait)
            self._last_call_time = time.monotonic()

    def _breaker_tripped(self) -> bool:
        return time.monotonic() < self._unavailable_until

    def chat(self, system_prompt: str, user_prompt: str) -> str | None:
        if not self.is_configured():
            return None
        if self._breaker_tripped():
            return None

        for attempt in range(2):
            self._throttle()
            try:
                status, retry_after, text = self._request(system_prompt, user_prompt)
            except Exception as exc:  # noqa: BLE001
                logger.warning("%s chat call raised, caller should fall back: %s", self.name, exc)
                return None

            if status == 429:
                if retry_after and retry_after > self.long_backoff_threshold_seconds:
                    self._unavailable_until = time.monotonic() + retry_after
                    logger.warning(
                        "%s rate-limited (429) with a %.0fs retry-after -- likely a daily quota. "
                        "Skipping %s for the rest of this process's life.",
                        self.name,
                        retry_after,
                        self.name,
                    )
                    return None
                if attempt == 0:
                    wait = retry_after or self.min_interval_seconds * 2
                    logger.warning("%s rate-limited (429), retrying once after %.1fs", self.name, wait)
                    time.sleep(wait)
                    continue
                return None

            if status >= 400 or text is None:
                logger.warning("%s chat call failed (status=%s), caller should fall back", self.name, status)
                return None

            return text

        logger.warning("%s chat call still rate-limited after one retry, caller should fall back", self.name)
        return None
