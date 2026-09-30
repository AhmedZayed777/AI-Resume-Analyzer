import time
from functools import lru_cache

from langchain.chat_models import init_chat_model

from .. import config


@lru_cache(maxsize=1)
def get_llm():
    if not config.LLM_API_KEY:
        raise RuntimeError("LLM_API_KEY is not set. Add it to .env (see .env.example).")
    return init_chat_model(
        config.LLM_MODEL,
        model_provider="openai",
        base_url=config.LLM_BASE_URL,
        api_key=config.LLM_API_KEY,
        temperature=0,
        max_tokens=4096,
        timeout=60,
        max_retries=5,
    )


def _is_daily_quota_error(exc: Exception) -> bool:
    return "free-models-per-day" in str(exc)


def describe_ai_error(exc: Exception, fallback: str) -> str:
    """Turn provider failures into an accurate, actionable user-facing message."""
    if _is_daily_quota_error(exc):
        return (
            "The free LLM daily quota is exhausted (OpenRouter allows 50 free requests "
            "per day). It resets automatically at 00:00 UTC. You can wait, add credits "
            "at openrouter.ai, or put a different provider key in .env."
        )
    status = getattr(exc, "status_code", None)
    if status == 429 or "429" in str(exc)[:80]:
        return (
            "The LLM provider is rate-limiting requests right now. "
            "Please try again in a minute."
        )
    return fallback


def call_with_retry(fn, attempts: int = 3, delay: float = 2.0):
    """Run fn() with retries for free-tier 429/503 and malformed-structured-output errors.

    Daily-quota 429s are not retried: every attempt would fail until the reset.
    """
    last = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - provider errors vary by class
            if _is_daily_quota_error(exc):
                raise
            last = exc
            if i < attempts - 1:
                time.sleep(delay * (i + 1))
    raise last
