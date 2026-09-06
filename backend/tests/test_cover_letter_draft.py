from app.services import tailoring


def test_draft_cover_letter_returns_llm_output_when_available(monkeypatch):
    monkeypatch.setattr(tailoring, "llm_chat", lambda *a, **k: "Dear hiring team, I am writing to apply...")

    result = tailoring.draft_cover_letter(
        candidate_name="Megha Kanojia",
        company="Acme Corp",
        role_title="Data Engineer",
        jd_text="We need a data engineer with Python and SQL.",
        grounding_facts="- Python: built ETL pipelines at a previous role\n- SQL: wrote analytical queries",
    )

    assert result == "Dear hiring team, I am writing to apply..."


def test_draft_cover_letter_returns_none_when_llm_unavailable(monkeypatch):
    # Caller (the API route) must fall back to a static placeholder when this is
    # None -- confirming the contract, not just the happy path.
    monkeypatch.setattr(tailoring, "llm_chat", lambda *a, **k: None)

    result = tailoring.draft_cover_letter(
        candidate_name="Megha Kanojia",
        company="Acme Corp",
        role_title="Data Engineer",
        jd_text="We need a data engineer.",
        grounding_facts="- Python: built ETL pipelines",
    )

    assert result is None
