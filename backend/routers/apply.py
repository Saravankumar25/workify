import asyncio
import json
import logging

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core.config import settings
from core.dependencies import get_current_user, get_current_user_sse
from core.rate_limit import (
    is_linkedin_circuit_open,
    release_daily_apply,
    reserve_daily_apply,
)
from models.application import Application
from models.artifact import Artifact, ArtifactType
from models.job import Job
from models.run import Run, RunKind
from models.user import User
from services.apply_service import (
    get_run_queue,
    run_apply_job,
    schedule_run,
    TERMINAL_PREFIXES,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/apply", tags=["Apply"])


class ApplyRunRequest(BaseModel):
    application_id: str


class ResumeRunRequest(BaseModel):
    run_id: str


@router.post("/run")
async def start_apply_run(
    body: ApplyRunRequest, user: User = Depends(get_current_user)
):
    # Circuit-breaker gate BEFORE reservation so we don't spend a cap on
    # an immediately-rejected request.
    open_until = await is_linkedin_circuit_open(user)
    if open_until is not None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Repeated LinkedIn failures detected for your account. "
                f"Automated applies paused until {open_until.isoformat()}Z."
            ),
        )

    # Atomic reservation — competing parallel requests cannot over-count.
    await reserve_daily_apply(user)

    try:
        # Fail fast on server busy — semaphore is in apply_service. We return
        # 503 here without acquiring, by comparing in-flight apply runs.
        # (The semaphore itself enforces the real cap inside run_apply.)
        if len(_inflight_run_ids()) >= settings.MAX_CONCURRENT_APPLY_RUNS:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Server busy, try again in a moment.",
            )

        try:
            app_oid = PydanticObjectId(body.application_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid application_id")

        app = await Application.get(app_oid)
        if not app or app.user_id != str(user.id):
            raise HTTPException(status_code=404, detail="Application not found")

        try:
            job_oid = PydanticObjectId(app.job_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid job reference")
        job = await Job.get(job_oid)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
    except HTTPException:
        # Roll back the reservation so the user isn't penalized for a
        # pre-run validation failure.
        await release_daily_apply(user.id)
        raise

    run = Run(user_id=str(user.id), application_id=str(app.id), kind=RunKind.apply)
    await run.insert()

    app.run_id = str(run.id)
    await app.save()

    # Pull the md/json artifact bodies from artifact.content (hardened schema).
    artifacts = await Artifact.find(
        Artifact.application_id == str(app.id)
    ).to_list()
    resume_md = ""
    cl_md = ""
    qa_pairs: list = []
    for art in artifacts:
        if art.type == ArtifactType.resume_md:
            resume_md = art.content or ""
        elif art.type == ArtifactType.cover_letter_md:
            cl_md = art.content or ""
        elif art.type == ArtifactType.qa_json:
            try:
                qa_pairs = json.loads(art.content or "[]")
            except json.JSONDecodeError:
                logger.warning("Malformed qa_json artifact for app %s", app.id)
                qa_pairs = []

    schedule_run(
        application=app,
        run_id=str(run.id),
        job_url=job.url,
        resume_md=resume_md,
        cover_letter_md=cl_md,
        qa_pairs=qa_pairs,
    )

    return {
        "run_id": str(run.id),
        "status": "started",
        "stream_url": f"/apply/stream/{run.id}",
    }


def _inflight_run_ids() -> list[str]:
    # Lazy import avoids circular ref. _run_tasks tracks only live background
    # tasks; queues may linger past completion during the grace period.
    from services.apply_service import _run_tasks  # type: ignore
    return [rid for rid, t in _run_tasks.items() if not t.done()]


@router.get("/stream/{run_id}")
async def stream_run_logs(
    run_id: str,
    user: User = Depends(get_current_user_sse),
):
    """SSE stream of apply-run logs. Accepts ?token= query param for EventSource."""
    try:
        run_oid = PydanticObjectId(run_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Run not found")

    run = await Run.get(run_oid)
    if not run or run.user_id != str(user.id):
        raise HTTPException(status_code=404, detail="Run not found")

    queue = get_run_queue(run_id)
    if queue is None:
        # No queue AND run has ended → replay persisted log_lines once, then close.
        if run.ended_at is not None:
            return StreamingResponse(
                _replay_completed_run(run),
                media_type="text/event-stream",
                headers=_SSE_HEADERS,
            )
        raise HTTPException(
            status_code=404,
            detail="Run not found or already completed",
        )

    async def event_generator():
        # Keepalive on 25s of silence; terminal events always break.
        while True:
            try:
                line = await asyncio.wait_for(queue.get(), timeout=25.0)
            except asyncio.TimeoutError:
                yield "data: __PING__\n\n"
                continue
            except asyncio.CancelledError:
                break
            yield f"data: {line}\n\n"
            if any(line.startswith(p) for p in TERMINAL_PREFIXES):
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


async def _replay_completed_run(run: Run):
    for line in run.log_lines or []:
        yield f"data: {line}\n\n"
    if run.success:
        yield "data: __DONE__\n\n"
    else:
        yield "data: __ERROR__ run already completed\n\n"


_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


@router.get("/test-worker")
async def test_worker(user: User = Depends(get_current_user)):
    """Sanity check that the apply_worker subprocess can launch and communicate."""
    logs: list[str] = []
    result = await run_apply_job(
        job_url="https://example.com",
        resume_md="Test resume",
        cover_letter_md="Test cover letter",
        qa_pairs=[],
        linkedin_email="test@test.com",
        linkedin_password="testpass",
        session_cookies=None,
        log_fn=logs.append,
    )
    return {"logs": logs, "result": result}


@router.post("/resume")
async def resume_after_captcha(
    body: ResumeRunRequest, user: User = Depends(get_current_user)
):
    try:
        prev_oid = PydanticObjectId(body.run_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Run not found")
    prev = await Run.get(prev_oid)
    if not prev or prev.user_id != str(user.id):
        raise HTTPException(status_code=404, detail="Run not found")
    if not prev.application_id:
        raise HTTPException(status_code=400, detail="Run has no associated application")

    open_until = await is_linkedin_circuit_open(user)
    if open_until is not None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Repeated LinkedIn failures detected for your account. "
                f"Automated applies paused until {open_until.isoformat()}Z."
            ),
        )

    await reserve_daily_apply(user)
    try:
        app = await Application.get(PydanticObjectId(prev.application_id))
        if not app:
            raise HTTPException(status_code=404, detail="Application not found")
        job = await Job.get(PydanticObjectId(app.job_id))
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
    except HTTPException:
        await release_daily_apply(user.id)
        raise

    new_run = Run(
        user_id=str(user.id),
        application_id=str(app.id),
        kind=RunKind.apply,
        metadata={"resumed_from": str(prev.id)},
    )
    await new_run.insert()

    schedule_run(
        application=app,
        run_id=str(new_run.id),
        job_url=job.url,
    )

    return {
        "run_id": str(new_run.id),
        "status": "resumed",
        "stream_url": f"/apply/stream/{new_run.id}",
    }
