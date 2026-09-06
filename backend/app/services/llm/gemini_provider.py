"""See pipeline/llm/gemini_provider.py -- same provider, duplicated for this
separately-deployed process. Enabling billing on the Google Cloud project
removes the free tier entirely -- never do that if this should stay free.
"""

import requests

from app.core.config import settings
from app.services.llm.base import RateLimitedProvider

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
GEMINI_MODEL = "gemini-3.8-flash"


class GeminiProvider(RateLimitedProvider):
    name = "gemini"
    min_interval_seconds = 6.0

    def is_configured(self) -> bool:
        return bool(settings.gemini_api_key)

    def _request(self, system_prompt: str, user_prompt: str) -> tuple[int, float | None, str | None]:
        resp = requests.post(
            GEMINI_URL,
            headers={"x-goog-api-key": settings.gemini_api_key, "Content-Type": "application/json"},
            json={
                "model": GEMINI_MODEL,
                "system_instruction": system_prompt,
                "input": user_prompt,
            },
            timeout=30,
        )
        if resp.status_code == 429:
            return 429, _parse_retry_after(resp.headers.get("Retry-After")), None
        if resp.status_code >= 400:
            return resp.status_code, None, None

        data = resp.json()
        text = data.get("output_text")
        if not text:
            for step in data.get("steps", []):
                for block in step.get("content", []):
                    if block.get("type") == "text" and block.get("text"):
                        text = block["text"]
                        break
        if not text:
            raise ValueError(f"no text found in Gemini response: {data}")
        return 200, None, text.strip()


def _parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None
