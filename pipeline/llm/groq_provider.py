"""Groq: ongoing free tier, no billing risk. Confirmed via a direct API test
against this project's real key (2026-09-04): openai/gpt-oss-120b's free-tier
limits are 30 req/min, 8,000 tokens/min, 1,000 req/DAY. llama-3.3-70b-versatile
returned "model_not_found" on this account despite appearing in Groq's own
docs examples -- gpt-oss-120b is what actually works.
"""

import requests

from pipeline.common.config import config
from pipeline.llm.base import RateLimitedProvider

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "openai/gpt-oss-120b"


class GroqProvider(RateLimitedProvider):
    name = "groq"
    # ~1,000-1,100 tokens/call after RAG-based prompt trimming -- 13s keeps
    # ~4.6 calls/min, safely under the 8,000 TPM budget with margin.
    min_interval_seconds = 13.0

    def is_configured(self) -> bool:
        return bool(config.groq_api_key)

    def _request(self, system_prompt: str, user_prompt: str) -> tuple[int, float | None, str | None]:
        resp = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {config.groq_api_key}"},
            json={
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.2,
                "max_tokens": 500,
            },
            timeout=30,
        )
        if resp.status_code == 429:
            retry_after = _parse_retry_after(resp.headers.get("Retry-After"))
            return 429, retry_after, None
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
