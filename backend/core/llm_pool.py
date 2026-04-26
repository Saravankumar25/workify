"""Multi-provider LLM key pool with round-robin rotation and provider fallback.

Round-robin is implemented with itertools.cycle at module level — safe for
single-process uvicorn (--workers 1). Each worker process gets its own
independent pool state, which is acceptable for load distribution.

Provider fallback chains per task type (configured in llm_service.py):
  resume_generation / cover_letter:  groq → gemini
  qa_generation / pdf_parsing:       mistral → groq
  browser_agent:                     gemini → groq

Design rules:
- API key values are never logged; only provider names appear in log output.
- Providers with no configured keys are skipped silently in the fallback chain.
- Module works with only GROQ_API_KEYS set (graceful degradation).
"""
from __future__ import annotations

import asyncio
import itertools
import logging
from typing import Awaitable, Callable, Iterator, Optional, Sequence

logger = logging.getLogger(__name__)


class KeyPool:
    """Round-robin key rotator for one LLM provider.

    itertools.cycle never raises StopIteration so next() is safe to call
    indefinitely. An empty pool returns None from next_key().
    """

    def __init__(self, keys: Sequence[str], provider: str) -> None:
        self._keys: list[str] = list(keys)
        self._provider = provider
        self._cycle: Iterator[str] = (
            itertools.cycle(self._keys) if self._keys else iter([])
        )

    @property
    def provider(self) -> str:
        return self._provider

    def has_keys(self) -> bool:
        return bool(self._keys)

    def next_key(self) -> Optional[str]:
        """Return the next key in rotation, or None if the pool is empty."""
        return next(self._cycle, None)

    def count(self) -> int:
        return len(self._keys)


# ---------------------------------------------------------------------------
# Module-level pools — lazily initialised on first use to avoid circular
# imports at settings-load time (config.py imports nothing from core/).
# ---------------------------------------------------------------------------

_groq_pool: Optional[KeyPool] = None
_gemini_pool: Optional[KeyPool] = None
_mistral_pool: Optional[KeyPool] = None


def _get_groq() -> KeyPool:
    global _groq_pool
    if _groq_pool is None:
        from core.config import settings
        _groq_pool = KeyPool(settings.groq_keys_list, "groq")
        logger.info("Groq key pool ready: %d key(s)", _groq_pool.count())
    return _groq_pool


def _get_gemini() -> KeyPool:
    global _gemini_pool
    if _gemini_pool is None:
        from core.config import settings
        _gemini_pool = KeyPool(settings.gemini_keys_list, "gemini")
        logger.info("Gemini key pool ready: %d key(s)", _gemini_pool.count())
    return _gemini_pool


def _get_mistral() -> KeyPool:
    global _mistral_pool
    if _mistral_pool is None:
        from core.config import settings
        _mistral_pool = KeyPool(settings.mistral_keys_list, "mistral")
        logger.info("Mistral key pool ready: %d key(s)", _mistral_pool.count())
    return _mistral_pool


def get_pool(provider: str) -> KeyPool:
    """Return the KeyPool for the named provider."""
    if provider == "groq":
        return _get_groq()
    if provider == "gemini":
        return _get_gemini()
    if provider == "mistral":
        return _get_mistral()
    raise ValueError(f"Unknown LLM provider: {provider!r}")


# ---------------------------------------------------------------------------
# Convenience accessors used by llm_service.py and apply_service.py
# ---------------------------------------------------------------------------

def next_groq_key() -> Optional[str]:
    """Next Groq API key in round-robin rotation. None if pool is empty."""
    return _get_groq().next_key()


def next_gemini_key() -> Optional[str]:
    """Next Gemini API key in round-robin rotation. None if pool is empty."""
    return _get_gemini().next_key()


def next_mistral_key() -> Optional[str]:
    """Next Mistral API key in round-robin rotation. None if pool is empty."""
    return _get_mistral().next_key()


# ---------------------------------------------------------------------------
# Provider fallback orchestrator
# ---------------------------------------------------------------------------

async def call_with_fallback(
    providers: Sequence[str],
    make_call: Callable[[str, str], Awaitable[str]],
    task_name: str = "",
) -> str:
    """Attempt each provider in order using round-robin key rotation.

    Providers with no configured keys are skipped silently.
    Raises the last exception if every configured provider fails.
    Raises RuntimeError if no provider has any keys.

    Args:
        providers:  Ordered provider names, e.g. ["groq", "gemini"].
        make_call:  Async callable (provider_name, api_key) → raw text.
        task_name:  Used only in log messages; never contains key material.
    """
    last_exc: BaseException | None = None
    tried_any = False

    for provider in providers:
        pool = get_pool(provider)
        if not pool.has_keys():
            logger.debug(
                "Skipping provider=%s for task=%r — no keys configured",
                provider, task_name,
            )
            continue

        key = pool.next_key()
        if key is None:
            continue

        tried_any = True
        try:
            logger.debug("Calling provider=%s for task=%r", provider, task_name)
            return await make_call(provider, key)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning(
                "Provider=%s failed for task=%r: %s",
                provider, task_name, type(exc).__name__,
            )
            last_exc = exc

    if not tried_any:
        raise RuntimeError(
            f"No LLM provider has keys configured for task {task_name!r}. "
            "Set GROQ_API_KEYS, GEMINI_API_KEYS, or MISTRAL_API_KEYS."
        )
    assert last_exc is not None
    raise last_exc


__all__ = [
    "KeyPool",
    "get_pool",
    "next_groq_key",
    "next_gemini_key",
    "next_mistral_key",
    "call_with_fallback",
]
