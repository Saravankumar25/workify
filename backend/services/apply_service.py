"""Apply-run orchestration.

The browser-use Agent runs in a dedicated OS thread that owns its own asyncio
event loop (via asyncio.run()). This avoids two Windows-specific failures:

  1. asyncio.create_subprocess_exec → NotImplementedError on Windows
     (ProactorEventLoop does not support subprocess in all FastAPI configurations)

  2. asyncio.run()-inside-running-loop
     (browser-use internally calls asyncio.run(); nesting it inside FastAPI's
      already-running loop raises RuntimeError)

The thread receives progress via a thread-safe log callback that posts messages
back onto the FastAPI event loop with loop.call_soon_threadsafe().
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
import traceback
from datetime import datetime
from typing import Callable, Dict, Optional

from beanie import PydanticObjectId

from core.config import settings
from core.rate_limit import (
    is_linkedin_circuit_open,
    record_linkedin_failure,
    record_linkedin_success,
    release_daily_apply,
)
from models.application import Application, ApplicationStatus
from models.profile import Profile
from models.run import Run

logger = logging.getLogger(__name__)

_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_APPLY_RUNS)
_run_queues: Dict[str, asyncio.Queue] = {}
_run_tasks: Dict[str, asyncio.Task] = {}
_QUEUE_GRACE_SECONDS = 30.0

TERMINAL_PREFIXES = ("__DONE__", "__ERROR__", "__CAPTCHA_DETECTED__", "__TIMEOUT__")


# ---------- queue helpers ----------

def register_run(run_id: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _run_queues[run_id] = q
    return q


def get_run_queue(run_id: str) -> Optional[asyncio.Queue]:
    return _run_queues.get(run_id)


def _emit(run_id: str, message: str) -> None:
    q = _run_queues.get(run_id)
    if q is not None:
        q.put_nowait(message)


async def _drop_queue_after_grace(run_id: str) -> None:
    await asyncio.sleep(_QUEUE_GRACE_SECONDS)
    _run_queues.pop(run_id, None)
    _run_tasks.pop(run_id, None)


# ---------- orphan cleanup ----------

def kill_orphan_chromium() -> None:
    """Kill leftover Chromium processes owned by this FastAPI process."""
    try:
        import psutil
    except Exception:
        psutil = None

    if psutil is not None:
        try:
            me = psutil.Process(os.getpid())
            for child in me.children(recursive=True):
                try:
                    name = (child.name() or "").lower()
                except Exception:
                    continue
                if any(tok in name for tok in ("chrome", "chromium", "headless_shell")):
                    try:
                        child.kill()
                    except Exception:
                        pass
            return
        except Exception as exc:
            logger.debug("psutil-based orphan kill failed: %s", exc)

    if sys.platform.startswith("linux") or sys.platform == "darwin":
        try:
            import signal
            os.killpg(os.getpgrp(), signal.SIGKILL)
        except Exception:
            pass


# ---------- in-process apply job ----------

async def run_apply_job(
    job_url: str,
    resume_md: str,
    cover_letter_md: str,
    qa_pairs: list,
    linkedin_email: str,
    linkedin_password: str,
    session_cookies: Optional[list],
    log_fn: Callable[[str], None],
) -> dict:
    """
    Run apply_worker.run_apply() in a dedicated thread with its own event loop.

    Progress messages are forwarded thread-safely back to the FastAPI event loop
    via loop.call_soon_threadsafe so the SSE stream stays live during the run.
    Returns the worker's result dict.
    """
    from core.llm_pool import next_gemini_key, next_groq_key
    from workers.apply_worker import run_apply as worker_run_apply

    config = {
        "job_url": job_url,
        "resume_md": resume_md,
        "cover_letter_md": cover_letter_md,
        "qa_pairs": qa_pairs,
        "linkedin_email": linkedin_email,
        "linkedin_password": linkedin_password,
        "session_cookies": session_cookies,
        "groq_api_key": next_groq_key() or "",
        "groq_model": settings.GROQ_MODEL_APPLY,
        "gemini_api_key": next_gemini_key() or "",
        "gemini_model": settings.GEMINI_MODEL_AGENT,
        "max_steps": settings.BROWSER_USE_MAX_STEPS,
        "headless": settings.PLAYWRIGHT_HEADLESS,
        "slowmo_ms": settings.PLAYWRIGHT_SLOWMO_MS,
    }

    log_fn("Starting browser automation worker (in-process)...")

    loop = asyncio.get_event_loop()

    def thread_safe_log(msg: str) -> None:
        loop.call_soon_threadsafe(log_fn, msg)

    result_holder: dict = {"result": {"status": "unknown", "message": "Worker produced no result"}}

    def run_in_thread() -> None:
        # Give the worker thread its own ProactorEventLoop on Windows so that
        # Playwright's internal subprocess spawning works correctly.
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        try:
            result_holder["result"] = asyncio.run(worker_run_apply(config, thread_safe_log))
        except Exception as exc:
            tb = traceback.format_exc()
            thread_safe_log(f"Thread-level exception: {type(exc).__name__}: {exc}")
            thread_safe_log(f"Traceback:\n{tb}")
            result_holder["result"] = {"status": "error", "message": str(exc), "tb": tb}

    await asyncio.to_thread(run_in_thread)

    result = result_holder["result"]

    if result.get("tb"):
        log_fn(f"Worker traceback:\n{result['tb']}")
        logger.error("[run] Worker traceback:\n%s", result["tb"])

    return result


# ---------- top-level run orchestrator ----------

async def run_apply(
    application: Application,
    run_id: str,
    job_url: str,
    resume_md: str = "",
    cover_letter_md: str = "",
    qa_pairs: list | None = None,
) -> None:
    """Execute the apply run in-process. Always updates application + run status,
    always emits a terminal sentinel, always releases the semaphore."""
    log_lines: list[str] = []

    def log(msg: str) -> None:
        log_lines.append(msg)
        _emit(run_id, msg)
        logger.info("[run %s] %s", run_id, msg)

    terminal_sentinel: str = "__ERROR__ unknown"
    try:
        async with _semaphore:
            log("Acquired semaphore slot — starting apply run")

            profile = await Profile.find_one(Profile.user_id == application.user_id)
            li_email: Optional[str] = profile.linkedin_email if profile else None
            li_password: Optional[str] = profile.linkedin_password if profile else None

            if not li_email or not li_password:
                log("ERROR: No LinkedIn credentials found in profile — add them on the Profile page")
                application.status = ApplicationStatus.failed
                terminal_sentinel = "__ERROR__ No LinkedIn credentials"
            else:
                session_cookies: Optional[list] = None

                try:
                    result = await asyncio.wait_for(
                        run_apply_job(
                            job_url=job_url,
                            resume_md=resume_md,
                            cover_letter_md=cover_letter_md,
                            qa_pairs=qa_pairs or [],
                            linkedin_email=li_email,
                            linkedin_password=li_password,
                            session_cookies=session_cookies,
                            log_fn=log,
                        ),
                        timeout=settings.APPLY_RUN_TIMEOUT_SECONDS,
                    )
                except asyncio.TimeoutError:
                    application.status = ApplicationStatus.failed
                    log(f"Total apply-run timeout ({settings.APPLY_RUN_TIMEOUT_SECONDS}s) exceeded")
                    terminal_sentinel = "__TIMEOUT__ total apply-run deadline"
                else:
                    status_val = result.get("status", "unknown")
                    if status_val == "success":
                        application.status = ApplicationStatus.submitted
                        application.submitted_at = datetime.utcnow()
                        log("Application submitted successfully")
                        terminal_sentinel = "__DONE__"
                    elif status_val == "captcha":
                        application.status = ApplicationStatus.needs_action
                        log("CAPTCHA detected — manual action required")
                        terminal_sentinel = "__CAPTCHA_DETECTED__"
                    else:
                        application.status = ApplicationStatus.failed
                        log(f"Apply run failed: {result.get('message', '')}")
                        terminal_sentinel = f"__ERROR__ {result.get('message', 'unknown error')}"

    except asyncio.CancelledError:
        application.status = ApplicationStatus.failed
        terminal_sentinel = "__ERROR__ cancelled"
        raise
    except Exception as exc:
        application.status = ApplicationStatus.failed
        tb = traceback.format_exc()
        log(f"Apply run crashed: {type(exc).__name__}: {exc}")
        log(f"Traceback:\n{tb}")
        logger.exception("Apply run crashed for run_id=%s", run_id)
        terminal_sentinel = f"__ERROR__ {type(exc).__name__}: {exc}"
    finally:
        application.updated_at = datetime.utcnow()
        try:
            await application.save()
        except Exception:
            logger.exception("Failed to persist application status")

        try:
            run = await Run.get(PydanticObjectId(run_id))
            if run is not None:
                run.ended_at = datetime.utcnow()
                run.success = application.status == ApplicationStatus.submitted
                run.log_lines = log_lines
                await run.save()
        except Exception:
            logger.exception("Failed to persist run")

        try:
            if application.status == ApplicationStatus.submitted:
                await record_linkedin_success(application.user_id)
            elif application.status == ApplicationStatus.failed:
                await record_linkedin_failure(application.user_id)
        except Exception:
            logger.exception("Circuit breaker update failed")

        _emit(run_id, terminal_sentinel)
        asyncio.create_task(_drop_queue_after_grace(run_id))


def schedule_run(
    application: Application,
    run_id: str,
    job_url: str,
    resume_md: str = "",
    cover_letter_md: str = "",
    qa_pairs: list | None = None,
) -> asyncio.Task:
    register_run(run_id)
    task = asyncio.create_task(
        run_apply(
            application=application,
            run_id=run_id,
            job_url=job_url,
            resume_md=resume_md,
            cover_letter_md=cover_letter_md,
            qa_pairs=qa_pairs,
        ),
        name=f"apply-run-{run_id}",
    )
    _run_tasks[run_id] = task
    return task


__all__ = [
    "register_run",
    "get_run_queue",
    "run_apply",
    "run_apply_job",
    "schedule_run",
    "kill_orphan_chromium",
    "TERMINAL_PREFIXES",
    "is_linkedin_circuit_open",
    "release_daily_apply",
]
