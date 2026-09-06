import time

from app.services.llm.base import RateLimitedProvider


class _FakeProvider(RateLimitedProvider):
    name = "fake"
    min_interval_seconds = 0.0
    long_backoff_threshold_seconds = 60.0

    def __init__(self, responses):
        super().__init__()
        self._responses = list(responses)
        self.request_count = 0

    def is_configured(self) -> bool:
        return True

    def _request(self, system_prompt, user_prompt):
        self.request_count += 1
        return self._responses.pop(0)


def test_successful_call_returns_text():
    provider = _FakeProvider([(200, None, "hello")])
    assert provider.chat("sys", "user") == "hello"


def test_long_retry_after_trips_breaker_without_waiting_it_out():
    # Same fix as pipeline/llm/base.py, duplicated here since this is a
    # separately-deployed process with its own copy of the same bug class.
    provider = _FakeProvider([(429, 300.0, None)])

    start = time.monotonic()
    result = provider.chat("sys", "user")
    elapsed = time.monotonic() - start

    assert result is None
    assert elapsed < 2.0, f"took {elapsed}s -- should have skipped waiting out a 300s retry-after"
    assert provider.request_count == 1


def test_breaker_stays_tripped_for_subsequent_calls():
    provider = _FakeProvider([(429, 300.0, None), (200, None, "should not be reached")])

    first = provider.chat("sys", "user")
    second = provider.chat("sys", "user2")

    assert first is None
    assert second is None
    assert provider.request_count == 1


def test_unconfigured_provider_returns_none_without_calling():
    class _Unconfigured(_FakeProvider):
        def is_configured(self):
            return False

    provider = _Unconfigured([(200, None, "should never be reached")])
    assert provider.chat("sys", "user") is None
    assert provider.request_count == 0
