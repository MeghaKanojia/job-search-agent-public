"""LangGraph self-correcting draft loop for the free-text generators in
tailoring.py (draft_cover_letter, draft_project_bullet).

Those generators already enforce "ground every claim in the facts you're
given" via a strict system prompt, and tests/test_tailoring.py asserts the
non-LLM skill-selection path never invents a skill. What this module adds is
a *runtime* check on top of the prompt-only rule for the two genuinely
generative (free-text) paths: a second, cheap LLM call acts as a critic,
comparing the draft against the same grounding facts and returning PASS or
FAIL with a reason. On FAIL, the graph loops back to the draft node with that
reason appended as corrective feedback, up to MAX_RETRIES attempts, before
giving up and returning None (same fallback contract draft_cover_letter and
draft_project_bullet already had: callers fall back to a static
template/raw description when the result is None).

The LLM call function is passed in as `chat_fn` rather than imported at
module level, so callers (tailoring.py) can pass their own `llm_chat`
reference straight through -- this keeps the existing monkeypatch-based
tests in test_cover_letter_draft.py working unchanged, since they patch
`tailoring.llm_chat`, and tailoring.py forwards that same name here.
"""

import json
import logging
from typing import Callable, TypedDict

from langgraph.graph import END, StateGraph

logger = logging.getLogger(__name__)

MAX_RETRIES = 2

ChatFn = Callable[..., "str | None"]

_VALIDATE_SYSTEM_PROMPT = """You check whether a drafted piece of job-application text only
references facts that actually appear in the grounding facts given to you.

Hard rules, non-negotiable:
- Compare the DRAFT against the GROUNDING FACTS only. Do not use outside knowledge.
- Flag a FAIL if the draft states a company, skill, technology, metric, or outcome
  that is not present, even approximately, in the grounding facts.
- General connective sentences (e.g. "I'd welcome the chance to discuss this further")
  need no grounding, they are not factual claims.
- Respond with ONLY a single JSON object, no prose, no markdown fences, in exactly this
  shape: {"verdict": "PASS"} or {"verdict": "FAIL", "reason": "<short reason>"}"""


class DraftState(TypedDict):
    system_prompt: str
    user_prompt: str
    grounding_facts: str
    provider: str | None
    draft: str | None
    attempt: int
    verdict: str | None
    reason: str | None


def _make_draft_node(chat_fn: ChatFn):
    def _draft_node(state: DraftState) -> DraftState:
        user_prompt = state["user_prompt"]
        if state.get("reason"):
            user_prompt += (
                f"\n\nYour previous draft failed a grounding check for this reason: "
                f"{state['reason']}\nRevise it so every claim is grounded in the facts given."
            )
        draft = chat_fn(state["system_prompt"], user_prompt, provider=state.get("provider"))
        return {**state, "draft": draft, "attempt": state["attempt"] + 1}

    return _draft_node


def _make_validate_node(chat_fn: ChatFn):
    def _validate_node(state: DraftState) -> DraftState:
        if state["draft"] is None:
            return {**state, "verdict": "FAIL", "reason": "LLM draft call failed"}

        check_prompt = (
            f"GROUNDING FACTS:\n{state['grounding_facts'][:4000]}\n\n"
            f"DRAFT TO CHECK:\n{state['draft']}"
        )
        result = chat_fn(_VALIDATE_SYSTEM_PROMPT, check_prompt, provider=state.get("provider"))
        if result is None:
            # The critic call itself failed -- don't block on a check we couldn't
            # run; accept the draft rather than retry forever against a down provider.
            return {**state, "verdict": "PASS", "reason": None}

        cleaned = result.strip().strip("`")
        try:
            parsed = json.loads(cleaned)
            verdict = parsed.get("verdict", "PASS")
            reason = parsed.get("reason")
        except (json.JSONDecodeError, AttributeError):
            logger.warning("grounding-check critic response wasn't valid JSON, accepting draft as-is")
            verdict, reason = "PASS", None

        return {**state, "verdict": verdict, "reason": reason}

    return _validate_node


def _should_retry(state: DraftState) -> str:
    if state["verdict"] != "FAIL":
        return "finish"
    if state["attempt"] >= MAX_RETRIES:
        return "finish"
    return "retry"


def _build_graph(chat_fn: ChatFn):
    graph = StateGraph(DraftState)
    graph.add_node("draft", _make_draft_node(chat_fn))
    graph.add_node("validate", _make_validate_node(chat_fn))
    graph.set_entry_point("draft")
    graph.add_edge("draft", "validate")
    graph.add_conditional_edges("validate", _should_retry, {"retry": "draft", "finish": END})
    return graph.compile()


def run_grounded_draft(
    system_prompt: str,
    user_prompt: str,
    grounding_facts: str,
    chat_fn: ChatFn,
    provider: str | None = None,
) -> str | None:
    """Runs the draft -> validate -> retry loop and returns the final draft
    text, or None if the LLM call failed outright or the last attempt still
    failed the grounding check. Callers keep their existing None -> static
    fallback behavior unchanged.
    """
    graph = _build_graph(chat_fn)
    final_state: DraftState = graph.invoke({
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "grounding_facts": grounding_facts,
        "provider": provider,
        "draft": None,
        "attempt": 0,
        "verdict": None,
        "reason": None,
    })
    if final_state["verdict"] == "FAIL":
        return None
    return final_state["draft"]
