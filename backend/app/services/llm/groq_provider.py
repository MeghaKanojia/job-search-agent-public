"""See pipeline/llm/groq_provider.py -- same provider, duplicated for this
separately-deployed process. Confirmed limits for openai/gpt-oss-120b: 30
req/min, 8,000 tokens/min, 1,000 req/DAY.
"""

import requests

from app.core.config import settings
from app.services.llm.base import RateLimitedProvider

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "openai/gpt-oss-120b"


class GroqProvider(RateLimitedProvider):
    name = "groq"
    min_interval_seconds = 13.0

    def is_configured(self) -> bool:
        return bool(settings.groq_api_key)

    def _request(self, system_prompt: str, user_prompt: str) -> tuple[int, float | None, str | None]:
        resp = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {settings.groq_api_key}"},
            json={
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.4,
                "max_tokens": 600,
            },
            timeout=30,
        )
        if resp.status_code == 429:
            return 429, _parse_retry_after(resp.headers.get("Retry-After")), None
        if resp.status_code >= 400:
            return resp.status_code, None, None
        text = resp.json()["choices"][0]["message"]["content"].strip()
        return 200, None, text


def _parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None
