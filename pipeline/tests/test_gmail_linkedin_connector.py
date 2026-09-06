import json

from pipeline.connectors import gmail_linkedin_connector as connector


def test_extract_companies_maps_titles_to_companies(monkeypatch):
    monkeypatch.setattr(
        connector,
        "llm_chat",
        lambda *a, **k: json.dumps({"companies": {"Data Engineer": "Acme Corp", "Data Analyst": "Widget Co"}}),
    )

    result = connector._extract_companies("some email text", ["Data Engineer", "Data Analyst"])

    assert result == {"Data Engineer": "Acme Corp", "Data Analyst": "Widget Co"}


def test_extract_companies_ignores_hallucinated_titles(monkeypatch):
    # The LLM should only ever answer for the titles it was given -- if it
    # invents an extra entry for a title that was never asked about, that
    # entry must never surface (the caller only reads keys from `titles`).
    monkeypatch.setattr(
        connector,
        "llm_chat",
        lambda *a, **k: json.dumps({"companies": {"Data Engineer": "Acme Corp", "Invented Title": "Fake Co"}}),
    )

    result = connector._extract_companies("some email text", ["Data Engineer"])

    assert result == {"Data Engineer": "Acme Corp"}
    assert "Invented Title" not in result


def test_extract_companies_returns_empty_on_malformed_json(monkeypatch):
    monkeypatch.setattr(connector, "llm_chat", lambda *a, **k: "not valid json")

    result = connector._extract_companies("some email text", ["Data Engineer"])

    assert result == {}


def test_extract_companies_returns_empty_when_llm_unavailable(monkeypatch):
    monkeypatch.setattr(connector, "llm_chat", lambda *a, **k: None)

    result = connector._extract_companies("some email text", ["Data Engineer"])

    assert result == {}


def test_extract_companies_returns_empty_for_no_titles():
    result = connector._extract_companies("some email text", [])

    assert result == {}
