import json

from app.services import tailoring


def test_select_relevant_projects_drops_hallucinated_titles(monkeypatch):
    # The LLM should only ever choose from the titles it's given -- if it invents
    # one anyway (here "Unrelated Project", never selected), the caller must not
    # let anything outside the known set through.
    monkeypatch.setattr(
        tailoring,
        "llm_chat",
        lambda *a, **k: json.dumps({"projects": ["Credit Risk Scorecard", "Nonexistent Project"]}),
    )

    projects = tailoring.select_relevant_projects(
        jd_text="We need a Python developer with fintech risk modeling experience.",
        project_titles=["Credit Risk Scorecard", "Unrelated Project"],
    )

    assert projects == ["Credit Risk Scorecard"]


def test_select_relevant_projects_returns_none_on_malformed_json(monkeypatch):
    # Caller (generate_resume) must fall back to keeping every project unfiltered
    # when this returns None, same contract as every other LLM call.
    monkeypatch.setattr(tailoring, "llm_chat", lambda *a, **k: "not valid json")

    projects = tailoring.select_relevant_projects(
        jd_text="We need a Python developer.",
        project_titles=["Credit Risk Scorecard"],
    )

    assert projects is None


def test_select_relevant_projects_returns_none_when_llm_unavailable(monkeypatch):
    monkeypatch.setattr(tailoring, "llm_chat", lambda *a, **k: None)

    projects = tailoring.select_relevant_projects(
        jd_text="We need a Python developer.",
        project_titles=["Credit Risk Scorecard"],
    )

    assert projects is None
