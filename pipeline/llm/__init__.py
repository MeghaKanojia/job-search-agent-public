"""Multi-provider LLM abstraction: Groq and Gemini, selectable per call, both
behind the same chat(system_prompt, user_prompt) -> str | None interface.
Every provider degrades to None on any failure (unconfigured, rate-limited,
network error, unparseable response) -- callers must always have a
deterministic fallback, same rule as the original single-provider client
this replaced.

Provider notes (see docs/SETUP.md for the full one-time setup):
- groq: ongoing free tier, no billing risk. Default provider.
- gemini: free tier exists but limits aren't published as a fixed table;
  paced conservatively. Enabling billing on the project removes the free
  tier entirely -- never do that if this should stay free.

Claude/Anthropic was evaluated and deliberately excluded (2026-09-04):
confirmed via research that the Claude API has no ongoing free tier, only a
one-time ~$5 trial credit -- doesn't meet this project's free-only
requirement. Cerebras was also checked and ruled out for the same reason.
Don't re-add either without first confirming they've introduced a genuine
ongoing free tier, not just a bigger trial credit.
"""

from pipeline.common.config import config
from pipeline.llm.gemini_provider import GeminiProvider
from pipeline.llm.groq_provider import GroqProvider

_PROVIDERS = {
    "groq": GroqProvider(),
    "gemini": GeminiProvider(),
}


def get_provider(name: str | None = None):
    """Returns the named provider if configured, else falls back to the
    configured default provider (also returned even if unconfigured -- the
    caller's chat() call will then correctly return None).
    """
    candidate = _PROVIDERS.get(name) if name else None
    if candidate is not None and candidate.is_configured():
        return candidate
    return _PROVIDERS.get(config.default_llm_provider, _PROVIDERS["groq"])


def chat(system_prompt: str, user_prompt: str, provider: str | None = None) -> str | None:
    return get_provider(provider).chat(system_prompt, user_prompt)


def available_providers() -> list[str]:
    """Providers that are actually configured right now -- for a UI dropdown."""
    return [name for name, p in _PROVIDERS.items() if p.is_configured()]
