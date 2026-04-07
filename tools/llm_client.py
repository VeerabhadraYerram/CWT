"""Minimal OpenRouter LLM client — wraps OpenAI SDK."""

from __future__ import annotations

import time

import structlog
from openai import OpenAI

from config.settings import settings

logger = structlog.get_logger(__name__)


class LLMClient:
    """Thin wrapper around OpenRouter's OpenAI-compatible API.

    Usage:
        client = LLMClient()
        reply = client.chat([{"role": "user", "content": "Hello"}])
    """

    FALLBACK_MODELS = [
        "google/gemma-3-4b-it:free",
        "meta-llama/llama-3.3-70b-instruct:free",
    ]

    MAX_RETRIES = 2
    RETRY_DELAY = 3  # seconds between retries on 429

    def __init__(self, model: str | None = None):
        if not settings.OPENROUTER_API_KEY:
            raise ValueError("Missing OPENROUTER_API_KEY in environment")
        self.model = model or settings.OPENROUTER_MODEL
        self._client = OpenAI(
            base_url=settings.OPENROUTER_BASE_URL,
            api_key=settings.OPENROUTER_API_KEY,
        )

    def _call(self, messages, temperature):
        """Call LLM with retry on 429 and model fallback chain."""

        # Use ONLY these models in order
        models = [
            "google/gemma-3-4b-it:free",
            "meta-llama/llama-3.3-70b-instruct:free"
        ]

        for model in models:
            for attempt in range(1, self.MAX_RETRIES + 1):
                try:
                    return self._client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=500,
                    )
                except Exception as e:
                    error_str = str(e)
                    is_rate_limit = "429" in error_str
                    is_not_found = "404" in error_str

                    if is_not_found:
                        logger.warning("model_not_found", model=model)
                        break  # skip to next model

                    if is_rate_limit and attempt < self.MAX_RETRIES:
                        wait = self.RETRY_DELAY * attempt
                        logger.info("rate_limited_retry", model=model, attempt=attempt, wait=wait)
                        time.sleep(wait)
                        continue

                    logger.warning("llm_call_failed", model=model, attempt=attempt, error=error_str[:100])
                    break  # skip to next model

        raise Exception("All LLM models failed.")

    def chat(self, messages: list[dict], temperature: float = 0.7) -> str:
        """Send messages and return the assistant's text response.

        Args:
            messages: OpenAI-format message list (role + content dicts).
            temperature: Sampling temperature (0.0 = deterministic).

        Returns:
            The assistant reply as a plain string.
        """
        logger.debug("llm_request", model=self.model, msg_count=len(messages))

        response = self._call(messages, temperature)

        reply = response.choices[0].message.content or ""
        logger.debug("llm_response", chars=len(reply))
        return reply
