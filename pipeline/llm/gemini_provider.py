"""Gemini free tier. Google's own rate-limits docs (ai.google.dev/gemini-api/docs/rate-limits)
don't publish a fixed table -- limits are personalized per Google AI Studio
account and shown at aistudio.google.com/rate-limit. Pacing here is a
conservative default; if you see frequent 429s, check your actual limits
there and adjust min_interval_seconds.

IMPORTANT: enabling billing on the Google Cloud project removes the free tier
entirely (confirmed via Google's own docs) -- never do that if this should
stay free-only.

Request shape verified directly against ai.google.dev/gemini-api/docs/text-generation
(2026-09-04) rather than assumed from memory, given how much churn other
providers' APIs have had recently in this project.
"""

import requests

from pipeline.common.config import config
from pipeline.llm.base import RateLimitedProvider

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
GEMINI_MODEL = "gemini-3.8-flash"


class GeminiProvider(RateLimitedProvider):
    name = "gemini"
    # No published fixed TPM/RPM table for this account tier -- 6s is a
    # conservative starting point matching the same order of magnitude as
    # Groq's confirmed limits. Tighten or loosen based on real 429 behavior.
    min_interval_seconds = 6.0

    def is_configured(self) -> bool:
        return bool(config.gemini_api_key)

    def _request(self, system_prompt: str, user_prompt: str) -> tuple[int, float | None, str | None]:
        resp = requests.post(
            GEMINI_URL,
            headers={"x-goog-api-key": config.gemini_api_key, "Content-Type": "application/json"},
            json={
                "model": GEMINI_MODEL,
                "system_instruction": system_prompt,
                "input": user_prompt,
            },
            timeout=30,
        )
        if resp.status_code == 429:
            retry_after = _parse_retry_after(resp.headers.get("Retry-After"))
            return 429, retry_after, None
        if resp.status_code >= 400:
            return resp.status_code, None, None

        data = resp.json()
        text = data.get("output_text")
        if not text:
            # Best-effort fallback if output_text isn't present -- the verified
            # shape as of this writing includes it, but dig through steps as a
            # backstop in case that changes.
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
