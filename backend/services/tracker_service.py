from datetime import datetime, timezone
from typing import Optional

from beanie import PydanticObjectId

from models.application import Application, ApplicationStatus


async def list_applications(
    user_id: str,
    status: Optional[ApplicationStatus] = None,
    skip: int = 0,
    limit: int = 20,
) -> dict:
    """List applications for a user with optional status filter and pagination."""
    query = Application.find(Application.user_id == user_id)
    if status:
        query = query.find(Application.status == status)

    total = await query.count()
    items = (
        await query.sort(-Application.created_at).skip(skip).limit(limit).to_list()
    )

    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit,
    }


async def get_application(application_id: str, user_id: str) -> Application | None:
    """Get a single application by ID, scoped to the user."""
    app = await Application.get(PydanticObjectId(application_id))
    if app and app.user_id == user_id:
        return app
    return None


async def update_application_status(
    application_id: str,
    user_id: str,
    status: Optional[ApplicationStatus] = None,
    notes: Optional[str] = None,
) -> Application | None:
    """Update an application's status and/or notes."""
    app = await get_application(application_id, user_id)
    if not app:
        return None

    if status is not None:
        app.status = status
    if notes is not None:
        app.notes = notes
    app.updated_at = datetime.now(timezone.utc)
    await app.save()
    return app


async def delete_application(application_id: str, user_id: str) -> bool:
    """Delete an application. Returns True if deleted."""
    app = await get_application(application_id, user_id)
    if not app:
        return False
    await app.delete()
    return True
