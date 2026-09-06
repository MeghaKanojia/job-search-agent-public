from pipeline import scoring


def test_llm_relevance_judgment_returns_none_with_no_relevant_skills(monkeypatch):
    monkeypatch.setattr(scoring, "retrieve_relevant_skills", lambda engine, text, k=15: [])

    assert scoring.llm_relevance_judgment(None, "Data Engineer", "some JD") is None


def test_llm_relevance_judgment_parses_valid_json(monkeypatch):
    monkeypatch.setattr(scoring, "retrieve_relevant_skills", lambda engine, text, k=15: ["Python", "SQL"])
    monkeypatch.setattr(
        scoring.llm, "chat", lambda *a, **k: '{"score": 0.85, "reason": "Strong Python/SQL overlap."}'
    )

    result = scoring.llm_relevance_judgment(None, "Data Engineer", "Needs Python and SQL")

    assert result == (0.85, "Strong Python/SQL overlap.")


def test_llm_relevance_judgment_falls_back_to_none_on_malformed_json(monkeypatch):
    # Caller (land_to_postgres.py) must fall back to the rule-based score_description
    # when this returns None -- confirming the contract, not just the happy path.
    monkeypatch.setattr(scoring, "retrieve_relevant_skills", lambda engine, text, k=15: ["Python"])
    monkeypatch.setattr(scoring.llm, "chat", lambda *a, **k: "not valid json at all")

    assert scoring.llm_relevance_judgment(None, "Data Engineer", "some JD") is None


def test_llm_relevance_judgment_falls_back_to_none_when_llm_unconfigured(monkeypatch):
    monkeypatch.setattr(scoring, "retrieve_relevant_skills", lambda engine, text, k=15: ["Python"])
    monkeypatch.setattr(scoring.llm, "chat", lambda *a, **k: None)

    assert scoring.llm_relevance_judgment(None, "Data Engineer", "some JD") is None


def test_llm_relevance_judgment_clamps_out_of_range_score(monkeypatch):
    monkeypatch.setattr(scoring, "retrieve_relevant_skills", lambda engine, text, k=15: ["Python"])
    monkeypatch.setattr(scoring.llm, "chat", lambda *a, **k: '{"score": 1.7, "reason": "test"}')

    score, _ = scoring.llm_relevance_judgment(None, "Data Engineer", "some JD")

    assert score == 1.0


def test_score_description_still_works_unaffected_by_rag_changes():
    # score_description is the cheap rule-based fallback, unrelated to RAG/LLM --
    # confirms the refactor didn't accidentally change its independent behavior.
    score, matched = scoring.score_description("We need Python and SQL", ["Python", "SQL", "Java"])
    assert matched == ["Python", "SQL"]
    assert score == round(2 / scoring.STRONG_MATCH_SKILL_COUNT, 4)
