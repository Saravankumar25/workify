"""Narrow async retry helper.

Production rule: only retry transient failures. Retrying on a programming
error, a malformed JSON body from Groq, an auth failure, or a permanent
Cloudinary rejection compounds cost and hides bugs. Callers pass
`should_retry(exc) -> bool` to opt into retryable exceptions explicitly.
"""
from __future__ import annotations

import asyncio
import functools
import logging
import random
from typing import Callable, Type

logger = logging.getLogger(__name__)


def _default_predicate(_exc: BaseException) -> bool:
    return False


def async_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    max_delay: float = 20.0,
    jitter: float = 0.25,
    exceptions: tuple[Type[BaseException], ...] = (Exception,),
    should_retry: Callable[[BaseException], bool] | None = None,
):
    """Retry decorator for async functions.

    - Only exceptions in ``exceptions`` are candidates for retry.
    - If ``should_retry`` is provided, it must also return True; this is
      where 4xx (non-429) and validation errors get filtered OUT.
    - asyncio.CancelledError is NEVER retried (propagates immediately so
      timeouts and shutdown remain prompt).
    """
    predicate = should_retry or _default_predicate

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            current_delay = delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except asyncio.CancelledError:
                    raise
                except exceptions as exc:
                    # Classifier gate — default predicate returns False so
                    # callers must explicitly opt into retry semantics.
                    if not predicate(exc):
                        raise
                    if attempt == max_attempts:
                        logger.error(
                            "%s failed after %d attempts: %s",
                            func.__name__,
                            max_attempts,
                            exc,
                        )
                        raise
                    sleep_for = min(current_delay, max_delay)
                    sleep_for *= 1 + random.uniform(-jitter, jitter)
                    sleep_for = max(0.05, sleep_for)
                    logger.warning(
                        "%s attempt %d/%d failed: %s — retrying in %.2fs",
                        func.__name__,
                        attempt,
                        max_attempts,
                        exc,
                        sleep_for,
                    )
                    await asyncio.sleep(sleep_for)
                    current_delay *= backoff
            # Unreachable — loop either returns or raises.
            raise RuntimeError("async_retry: exhausted without raise")

        return wrapper

    return decorator


def is_groq_retryable(exc: BaseException) -> bool:
    """Retry only on Groq 429 / 5xx / network timeouts / read errors."""
    import httpx

    if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError)):
        return True
    # groq SDK wraps HTTP errors with a .status_code on the exception.
    status = getattr(exc, "status_code", None)
    if status is None:
        resp = getattr(exc, "response", None)
        status = getattr(resp, "status_code", None)
    if isinstance(status, int):
        return status == 429 or 500 <= status < 600
    cls_name = exc.__class__.__name__.lower()
    return "ratelimit" in cls_name or "timeout" in cls_name


def is_cloudinary_retryable(exc: BaseException) -> bool:
    """Retry only on transient network/5xx Cloudinary failures."""
    import httpx

    if isinstance(
        exc, (httpx.TimeoutException, httpx.NetworkError, TimeoutError, ConnectionError)
    ):
        return True
    # cloudinary.exceptions.Error subclasses — inspect http_code.
    code = getattr(exc, "http_code", None)
    if isinstance(code, int) and (code == 429 or 500 <= code < 600):
        return True
    msg = str(exc).lower()
    if any(tok in msg for tok in ("timed out", "timeout", "temporarily", "connection")):
        return True
    return False
