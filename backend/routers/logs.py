from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional

from beanie import PydanticObjectId

from core.dependencies import get_current_user
from models.run import Run, RunKind
from models.user import User

router = APIRouter(prefix="/logs", tags=["Logs"])


def _run_to_dict(run: Run) -> dict:
    return {
        "id": str(run.id),
        "user_id": run.user_id,
        "application_id": run.application_id,
        "kind": run.kind.value,
        "started_at": run.started_at.isoformat(),
        "ended_at": run.ended_at.isoformat() if run.ended_at else None,
        "success": run.success,
        "log_lines": run.log_lines,
        "metadata": run.metadata,
    }


@router.get("/runs")
async def list_runs(
    user: User = Depends(get_current_user),
    kind: Optional[RunKind] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """List runs with optional kind filter and pagination."""
    query = Run.find(Run.user_id == str(user.id))
    if kind:
        query = query.find(Run.kind == kind)

    total = await query.count()
    items = await query.sort(-Run.started_at).skip(skip).limit(limit).to_list()

    return {
        "runs": [_run_to_dict(r) for r in items],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/runs/{run_id}")
async def get_run(
    run_id: str,
    user: User = Depends(get_current_user),
):
    """Get a single run with its log lines."""
    run = await Run.get(PydanticObjectId(run_id))
    if not run or run.user_id != str(user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Run not found"
        )
    return _run_to_dict(run)
