"""Groq / Gemini / Mistral LLM client with key pool rotation and provider fallback.

Hardening rules:
- Every call has a hard asyncio timeout (GROQ_REQUEST_TIMEOUT_SECONDS).
- Retries ONLY on 429 / 5xx / network errors (see is_groq_retryable).
- NEVER retried: malformed JSON, prompt/validation errors, auth failures.
- Within Groq: primary model → fallback model (same key, same pool slot).
- Across providers: call_with_fallback() tries each provider in chain order.
- If all providers fail, raises HTTP 503 — never propagates raw exception.
- API key values are never logged; only provider names appear in log output.

Provider chains per task:
  resume_generation / cover_letter:  ["groq", "gemini"]
  qa_generation / pdf_parsing:       ["mistral", "groq"]
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from fastapi import HTTPException, status as http_status
from groq import AsyncGroq

from core.config import settings
from core.llm_pool import call_with_fallback
from utils.retry import async_retry, is_groq_retryable

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


class LLMJSONError(ValueError):
    """Raised when the model returns content that cannot be parsed as JSON.
    Never retried — a malformed response is a prompt/model bug, not transient."""


def load_prompt(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.md"
    return path.read_text(encoding="utf-8")


def _get_retry_after_seconds(exc: BaseException) -> float | None:
    """Extract Retry-After wait from a Groq 429 exception's response headers."""
    resp = getattr(exc, "response", None)
    if resp is None:
        return None
    headers = getattr(resp, "headers", None) or {}
    for key in ("retry-after", "x-ratelimit-reset-requests"):
        raw = headers.get(key)
        if raw is not None:
            try:
                return float(raw)
            except (ValueError, TypeError):
                continue
    return None


# ---------------------------------------------------------------------------
# Provider-specific chat helpers
# ---------------------------------------------------------------------------

@async_retry(
    max_attempts=3,
    delay=2.0,
    backoff=2.0,
    max_delay=20.0,
    should_retry=is_groq_retryable,
)
async def _chat_groq(system: str, user: str, *, model: str, api_key: str) -> str:
    client = AsyncGroq(
        api_key=api_key,
        timeout=settings.GROQ_REQUEST_TIMEOUT_SECONDS,
        max_retries=0,
    )
    resp = await asyncio.wait_for(
        client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.4,
            max_tokens=4096,
        ),
        timeout=settings.GROQ_REQUEST_TIMEOUT_SECONDS,
    )
    return resp.choices[0].message.content or ""


async def _chat_gemini(system: str, user: str, *, api_key: str, model: str | None = None) -> str:
    """Call Gemini via langchain-google-genai. Lazy import — only needed when keys are set."""
    from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore[import]
    from langchain_core.messages import HumanMessage, SystemMessage  # type: ignore[import]

    _model = model or settings.GEMINI_MODEL_AGENT
    llm = ChatGoogleGenerativeAI(
        model=_model,
        google_api_key=api_key,
        temperature=0.4,
    )
    messages = [SystemMessage(content=system), HumanMessage(content=user)]
    resp = await asyncio.wait_for(
        llm.ainvoke(messages),
        timeout=settings.GROQ_REQUEST_TIMEOUT_SECONDS,
    )
    return resp.content or ""


async def _chat_mistral(system: str, user: str, *, api_key: str, model: str | None = None) -> str:
    """Call Mistral AI. Lazy import — only needed when keys are set."""
    from mistralai import Mistral  # type: ignore[import]

    _model = model or settings.MISTRAL_MODEL_QA
    client = Mistral(api_key=api_key)
    resp = await asyncio.wait_for(
        client.chat.complete_async(
            model=_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        ),
        timeout=settings.GROQ_REQUEST_TIMEOUT_SECONDS,
    )
    return resp.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# Unified chat dispatcher
# ---------------------------------------------------------------------------

async def _chat(
    system: str,
    user: str,
    *,
    model: str | None = None,
    providers: list[str] | None = None,
    task_name: str = "chat",
) -> str:
    """Route an LLM call through the provider pool with fallback.

    providers: ordered list such as ["groq", "gemini"]. Defaults to ["groq"].
    Raises HTTP 503 if all providers fail.
    """
    primary_model = model or settings.GROQ_MODEL
    _providers = providers or ["groq"]

    async def _try_provider(provider: str, api_key: str) -> str:
        if provider == "groq":
            primary_exc: Exception | None = None
            try:
                return await _chat_groq(system, user, model=primary_model, api_key=api_key)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                if not is_groq_retryable(exc):
                    raise
                primary_exc = exc
                retry_after = _get_retry_after_seconds(exc)
                if retry_after is not None and retry_after <= 5.0:
                    await asyncio.sleep(retry_after)

            logger.warning(
                "Groq primary model %s failed for task=%s (%s) — trying fallback %s",
                primary_model, task_name, primary_exc, settings.GROQ_MODEL_FALLBACK,
            )
            return await _chat_groq(
                system, user, model=settings.GROQ_MODEL_FALLBACK, api_key=api_key
            )

        if provider == "gemini":
            return await _chat_gemini(system, user, api_key=api_key)

        if provider == "mistral":
            return await _chat_mistral(system, user, api_key=api_key)

        raise ValueError(f"Unknown LLM provider: {provider!r}")

    try:
        return await call_with_fallback(_providers, _try_provider, task_name=task_name)
    except asyncio.CancelledError:
        raise
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("All LLM providers failed for task=%s: %s", task_name, exc)
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Document generation is temporarily unavailable — the AI service is "
                "rate-limited. Please wait a moment and try again."
            ),
        ) from exc


# ---------------------------------------------------------------------------
# JSON extraction helper
# ---------------------------------------------------------------------------

def _extract_json(raw: str, open_c: str, close_c: str) -> str | None:
    start = raw.find(open_c)
    end = raw.rfind(close_c) + 1
    if start != -1 and end > start:
        return raw[start:end]
    return None


# ---------------------------------------------------------------------------
# Public API — callers must not need changes
# ---------------------------------------------------------------------------

async def generate_resume_and_cl(job: dict, profile: dict) -> dict:
    style_guide = load_prompt("style_guides")
    resume_system = load_prompt("resume_system") + "\n\n" + style_guide
    cl_system = load_prompt("cover_letter_system") + "\n\n" + style_guide

    user_input = (
        f"PROFILE_JSON:\n```json\n{json.dumps(profile, indent=2)}\n```\n\n"
        f"JOB_DESCRIPTION:\n{job.get('description', '')}\n\n"
        f"Job Title: {job.get('title', '')}\n"
        f"Company: {job.get('company', '')}"
    )

    resume_md = await _chat(
        resume_system, user_input,
        model=settings.GROQ_MODEL_RESUME,
        providers=["groq", "gemini"],
        task_name="resume_generation",
    )
    cl_md = await _chat(
        cl_system, user_input,
        model=settings.GROQ_MODEL_COVER_LETTER,
        providers=["groq", "gemini"],
        task_name="cover_letter",
    )

    return {
        "resume_md": resume_md,
        "cover_letter_md": cl_md,
        "job_title": job.get("title", ""),
        "company": job.get("company", ""),
    }


async def generate_qa(job: dict, profile: dict) -> list:
    system = load_prompt("qa_system")
    user_input = (
        f"PROFILE_JSON:\n```json\n{json.dumps(profile, indent=2)}\n```\n\n"
        f"JOB_DESCRIPTION:\n{job.get('description', '')}"
    )

    raw = await _chat(
        system, user_input,
        model=settings.GROQ_MODEL_QA,
        providers=["mistral", "groq"],
        task_name="qa_generation",
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        snippet = _extract_json(raw, "[", "]")
        if snippet is not None:
            try:
                return json.loads(snippet)
            except json.JSONDecodeError:
                pass
        logger.error("Q&A generation returned non-JSON payload; surfacing empty list")
        return []


async def parse_resume_pdf(pdf_text: str) -> dict:
    system = load_prompt("pdf_import_system")
    user_input = f"RESUME_TEXT:\n{pdf_text}"

    raw = await _chat(
        system, user_input,
        model=settings.GROQ_MODEL_PDF_PARSE,
        providers=["mistral", "groq"],
        task_name="pdf_parsing",
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        snippet = _extract_json(raw, "{", "}")
        if snippet is not None:
            try:
                return json.loads(snippet)
            except json.JSONDecodeError:
                pass
        raise LLMJSONError("Model returned non-JSON resume parse output")
