from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from core.config import settings as app_settings
from core.dependencies import get_current_user
from models.user import User

router = APIRouter(prefix="/settings", tags=["Settings"])


class SettingsUpdate(BaseModel):
    daily_apply_cap: Optional[int] = None


class AdminCapUpdate(BaseModel):
    user_id: str
    daily_apply_cap: int


@router.get("")
async def get_settings(user: User = Depends(get_current_user)):
    """Get the current user's settings."""
    return {
        "daily_apply_cap": user.daily_apply_cap,
        "max_allowed": app_settings.RATE_LIMIT_APPLIES_PER_DAY_MAX,
        "is_admin": user.is_admin,
    }


@router.patch("")
async def update_settings(
    body: SettingsUpdate,
    user: User = Depends(get_current_user),
):
    """Update user settings (e.g., daily cap)."""
    if body.daily_apply_cap is not None:
        capped = min(body.daily_apply_cap, app_settings.RATE_LIMIT_APPLIES_PER_DAY_MAX)
        capped = max(capped, 1)
        user.daily_apply_cap = capped
        await user.save()

    return {
        "daily_apply_cap": user.daily_apply_cap,
        "max_allowed": app_settings.RATE_LIMIT_APPLIES_PER_DAY_MAX,
    }


@router.get("/admin")
async def admin_stats(user: User = Depends(get_current_user)):
    """Admin-only: get aggregate stats."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )

    total_users = await User.count()
    active_users = await User.find(User.is_active == True).count()

    return {
        "total_users": total_users,
        "active_users": active_users,
        "max_cap": app_settings.RATE_LIMIT_APPLIES_PER_DAY_MAX,
        "default_cap": app_settings.RATE_LIMIT_APPLIES_PER_DAY_DEFAULT,
    }


@router.patch("/admin/caps")
async def admin_set_user_cap(
    body: AdminCapUpdate,
    user: User = Depends(get_current_user),
):
    """Admin-only: set a specific user's daily apply cap."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )

    from beanie import PydanticObjectId

    target = await User.get(PydanticObjectId(body.user_id))
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found"
        )

    capped = min(body.daily_apply_cap, app_settings.RATE_LIMIT_APPLIES_PER_DAY_MAX)
    capped = max(capped, 1)
    target.daily_apply_cap = capped
    await target.save()

    return {
        "user_id": str(target.id),
        "daily_apply_cap": target.daily_apply_cap,
    }
