"""Provider-agnostic OpenAI-compatible generation."""

from __future__ import annotations

import time
from typing import Any

from openai import OpenAI

from .config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_RATE_DELAY

SYSTEM_PROMPT = """You are YojanaMitra, a cautious government-scheme assistant.
Answer ONLY from the retrieved context. If context does not contain the answer,
say that it is not available. Never invent schemes, amounts, dates, or eligibility.
Always cite scheme names and source links when links are present. Use "you may be
eligible", not certainty. Always end by reminding the user to verify details on
the official portal (myscheme.gov.in)."""


def generate(prompt: str, system: str = SYSTEM_PROMPT, client: Any = None) -> str:
    if not LLM_MODEL:
        raise RuntimeError("LLM_MODEL is required; set it in the environment.")
    client = client or OpenAI(
        api_key=LLM_API_KEY or "ollama",
        base_url=LLM_BASE_URL,
        timeout=30.0,
        max_retries=0,
    )
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
                temperature=0.1,
            )
            time.sleep(LLM_RATE_DELAY)
            return response.choices[0].message.content or ""
        except Exception as exc:
            last_error = exc
            status = getattr(exc, "status_code", None)
            if status not in {429, 500, 502, 503, 504} or attempt == 3:
                raise
            time.sleep(2**attempt)
    raise RuntimeError("LLM generation failed") from last_error
