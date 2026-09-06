from pipeline.connectors.base import JobPosting
from pipeline.landing import land_to_postgres


def test_llm_call_count_is_capped_regardless_of_posting_count(monkeypatch):
    # A real run with 200+ matched postings spent 2+ hours in 429-retry loops
    # because every single one got an LLM call. This asserts the fix directly:
    # no matter how many postings come in, at most MAX_LLM_JUDGMENTS_PER_RUN
    # ever reach the LLM.
    call_count = {"n": 0}

    def fake_llm_relevance_judgment(engine, title, description):
        call_count["n"] += 1
        return (0.5, "mock reason")

    monkeypatch.setattr(land_to_postgres, "llm_relevance_judgment", fake_llm_relevance_judgment)
    monkeypatch.setattr(land_to_postgres, "load_active_skill_names", lambda engine: ["Python"])
    monkeypatch.setattr(land_to_postgres, "score_description", lambda desc, skills: (0.1, []))

    postings = [
        JobPosting(source="jobspy_indeed", title=f"Data Engineer {i}", url=f"https://example.com/{i}")
        for i in range(200)
    ]

    # land_postings normally opens a real DB transaction -- stub engine.begin()
    # to a no-op context manager since this test only cares about how many
    # times the LLM was called, not the DB writes.
    class _FakeConn:
        def execute(self, *a, **k):
            class _Result:
                def fetchone(self_inner):
                    return None
            return _Result()

    class _FakeEngineCtx:
        def __enter__(self):
            return _FakeConn()

        def __exit__(self, *a):
            return False

    class _FakeConnectCtx:
        def __enter__(self):
            return _FakeConn()

        def __exit__(self, *a):
            return False

    class _FakeEngine:
        def begin(self):
            return _FakeEngineCtx()

        def connect(self):
            return _FakeConnectCtx()

    land_to_postgres.land_postings(_FakeEngine(), "jobspy", "batch-1", postings)

    assert call_count["n"] == land_to_postgres.MAX_LLM_JUDGMENTS_PER_RUN
