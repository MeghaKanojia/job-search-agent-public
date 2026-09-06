"""Multi-provider LLM abstraction for the backend -- same design as
pipeline/llm/, duplicated because this is a separately-deployed process.
Lets the dashboard's cover-letter drafting pick a provider per request
(the "options for using LLMs in my final UI" requirement), while defaulting
to the configured default_llm_provider when the caller doesn't specify one.

Claude/Anthropic was evaluated and deliberately excluded (2026-09-04): no
ongoing free tier, only a one-time trial credit -- doesn't meet this
project's free-only requirement. See pipeline/llm/__init__.py for the full
note; don't re-add without confirming that's changed.
"""

from app.core.config import settings
from app.services.llm.gemini_provider import GeminiProvider
from app.services.llm.groq_provider import GroqProvider

_PROVIDERS = {
    "groq": GroqProvider(),
    "gemini": GeminiProvider(),
}


def get_provider(name: str | None = None):
    candidate = _PROVIDERS.get(name) if name else None
    if candidate is not None and candidate.is_configured():
        return candidate
    return _PROVIDERS.get(settings.default_llm_provider, _PROVIDERS["groq"])


def chat(system_prompt: str, user_prompt: str, provider: str | None = None) -> str | None:
    return get_provider(provider).chat(system_prompt, user_prompt)


def available_providers() -> list[str]:
    """Providers that are actually configured right now -- for the Settings
    page / cover-letter provider dropdown.
    """
    return [name for name, p in _PROVIDERS.items() if p.is_configured()]
