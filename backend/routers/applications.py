from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from typing import Optional

from core.dependencies import get_current_user
from models.application import ApplicationStatus
from models.user import User
from services.tracker_service import (
    list_applications,
    get_application,
    update_application_status,
    delete_application,
)

router = APIRouter(prefix="/applications", tags=["Applications"])


class ApplicationUpdate(BaseModel):
    status: Optional[ApplicationStatus] = None
    notes: Optional[str] = None


def _app_to_dict(app) -> dict:
    return {
        "id": str(app.id),
        "user_id": app.user_id,
        "job_id": app.job_id,
        "status": app.status.value,
        "submitted_at": app.submitted_at.isoformat() if app.submitted_at else None,
        "notes": app.notes,
        "run_id": app.run_id,
        "created_at": app.created_at.isoformat(),
        "updated_at": app.updated_at.isoformat(),
    }


@router.get("")
async def list_user_applications(
    user: User = Depends(get_current_user),
    status_filter: Optional[ApplicationStatus] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """List applications with optional status filter and pagination."""
    result = await list_applications(
        user_id=str(user.id),
        status=status_filter,
        skip=skip,
        limit=limit,
    )
    return {
        "applications": [_app_to_dict(a) for a in result["items"]],
        "total": result["total"],
        "skip": result["skip"],
        "limit": result["limit"],
    }


@router.get("/{application_id}")
async def get_single_application(
    application_id: str,
    user: User = Depends(get_current_user),
):
    """Get a single application."""
    app = await get_application(application_id, str(user.id))
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Application not found"
        )
    return _app_to_dict(app)


@router.patch("/{application_id}")
async def update_application(
    application_id: str,
    body: ApplicationUpdate,
    user: User = Depends(get_current_user),
):
    """Update an application's status and/or notes."""
    app = await update_application_status(
        application_id=application_id,
        user_id=str(user.id),
        status=body.status,
        notes=body.notes,
    )
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Application not found"
        )
    return _app_to_dict(app)


@router.delete("/{application_id}")
async def delete_user_application(
    application_id: str,
    user: User = Depends(get_current_user),
):
    """Delete an application."""
    deleted = await delete_application(application_id, str(user.id))
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Application not found"
        )
    return {"deleted": True}
