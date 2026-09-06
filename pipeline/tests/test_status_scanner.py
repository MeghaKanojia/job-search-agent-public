from pipeline.gmail_status_sync import status_scanner


def test_llm_classification_used_when_available(monkeypatch):
    monkeypatch.setattr(status_scanner.llm, "chat", lambda *a, **k: "rejected")

    status, confidence = status_scanner._classify("Unfortunately we have decided not to proceed.")

    assert status == "rejected"
    assert confidence == 0.8


def test_llm_none_means_no_status_without_falling_back_to_keywords(monkeypatch):
    # A clean "none" from the LLM is a real answer, not a failure -- it must not
    # trigger the keyword fallback (which could produce a false positive the LLM
    # correctly avoided).
    monkeypatch.setattr(status_scanner.llm, "chat", lambda *a, **k: "none")

    status, confidence = status_scanner._classify("Thanks for your email, will get back to you.")

    assert status is None
    assert confidence == 0.0


def test_falls_back_to_keywords_when_llm_unconfigured(monkeypatch):
    monkeypatch.setattr(status_scanner.llm, "chat", lambda *a, **k: None)

    status, confidence = status_scanner._classify("Unfortunately we will not be moving forward.")

    assert status == "rejected"
    assert confidence == 0.6


def test_falls_back_to_keywords_when_llm_returns_unparseable_output(monkeypatch):
    monkeypatch.setattr(status_scanner.llm, "chat", lambda *a, **k: "I'm not sure, maybe rejected?")

    status, confidence = status_scanner._classify("We would like to schedule a call with you.")

    assert status == "interview"
    assert confidence == 0.6


def test_no_match_at_all_returns_none(monkeypatch):
    monkeypatch.setattr(status_scanner.llm, "chat", lambda *a, **k: None)

    status, confidence = status_scanner._classify("Your Amazon order has shipped.")

    assert status is None
    assert confidence == 0.0
