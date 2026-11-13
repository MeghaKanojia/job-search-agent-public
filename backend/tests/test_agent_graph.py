from app.services.agent_graph import run_grounded_draft


def test_passes_through_on_first_pass_verdict():
    calls = []

    def fake_chat(system_prompt, user_prompt, provider=None):
        calls.append(system_prompt)
        if "You check whether" in system_prompt:
            return '{"verdict": "PASS"}'
        return "Dear hiring team, I built ETL pipelines in Python at Optum."

    result = run_grounded_draft(
        system_prompt="draft system prompt",
        user_prompt="draft this",
        grounding_facts="- Python: built ETL pipelines at Optum",
        chat_fn=fake_chat,
    )

    assert result == "Dear hiring team, I built ETL pipelines in Python at Optum."
    assert len(calls) == 2  # one draft call, one validate call


def test_retries_once_then_succeeds_on_fail_then_pass():
    attempts = {"draft": 0, "validate": 0}

    def fake_chat(system_prompt, user_prompt, provider=None):
        if "You check whether" in system_prompt:
            attempts["validate"] += 1
            if attempts["validate"] == 1:
                return '{"verdict": "FAIL", "reason": "mentions Rust, not in the facts"}'
            return '{"verdict": "PASS"}'
        attempts["draft"] += 1
        if attempts["draft"] == 1:
            return "I am a Rust expert who also knows Python."
        return "I built ETL pipelines in Python."

    result = run_grounded_draft(
        system_prompt="draft system prompt",
        user_prompt="draft this",
        grounding_facts="- Python: built ETL pipelines",
        chat_fn=fake_chat,
    )

    assert result == "I built ETL pipelines in Python."
    assert attempts["draft"] == 2
    assert attempts["validate"] == 2


def test_gives_up_after_max_retries_and_returns_none():
    def always_fail_validate(system_prompt, user_prompt, provider=None):
        if "You check whether" in system_prompt:
            return '{"verdict": "FAIL", "reason": "still wrong"}'
        return "a draft that never satisfies the critic"

    result = run_grounded_draft(
        system_prompt="draft system prompt",
        user_prompt="draft this",
        grounding_facts="- Python: built ETL pipelines",
        chat_fn=always_fail_validate,
    )

    assert result is None


def test_returns_none_immediately_when_llm_draft_call_fails():
    def chat_fn_unconfigured(system_prompt, user_prompt, provider=None):
        return None

    result = run_grounded_draft(
        system_prompt="draft system prompt",
        user_prompt="draft this",
        grounding_facts="- Python: built ETL pipelines",
        chat_fn=chat_fn_unconfigured,
    )

    assert result is None
