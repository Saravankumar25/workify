from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from core.dependencies import get_current_user
from core.security import encrypt, decrypt
from models.linkedin_credentials import LinkedInCredentials
from models.user import User

router = APIRouter(prefix="/credentials", tags=["Credentials"])


class LinkedInCredentialsSave(BaseModel):
    email: str
    # Omit password to keep the existing saved password unchanged.
    password: Optional[str] = None


@router.post("/linkedin")
async def save_linkedin_credentials(
    body: LinkedInCredentialsSave,
    user: User = Depends(get_current_user),
):
    """Save encrypted LinkedIn credentials. Omit password to keep existing."""
    user_id = str(user.id)

    existing = await LinkedInCredentials.find_one(
        LinkedInCredentials.user_id == user_id
    )

    if existing:
        existing.encrypted_email = encrypt(body.email)
        if body.password:
            existing.encrypted_password = encrypt(body.password)
        existing.updated_at = datetime.now(timezone.utc)
        await existing.save()
    else:
        if not body.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password is required when saving credentials for the first time.",
            )
        creds = LinkedInCredentials(
            user_id=user_id,
            encrypted_email=encrypt(body.email),
            encrypted_password=encrypt(body.password),
        )
        await creds.insert()

    return {"saved": True}


@router.get("/linkedin/status")
async def linkedin_credentials_status(
    user: User = Depends(get_current_user),
):
    """Check if LinkedIn credentials are stored. Returns email but never password."""
    creds = await LinkedInCredentials.find_one(
        LinkedInCredentials.user_id == str(user.id)
    )

    if not creds:
        return {"has_creds": False, "cookies_valid": False}

    cookies_valid = False
    if creds.cookies_valid_until:
        cookies_valid = creds.cookies_valid_until > datetime.now(timezone.utc)

    return {
        "has_creds": True,
        "cookies_valid": cookies_valid,
        "email": decrypt(creds.encrypted_email),
        "password_saved": True,
        "created_at": creds.created_at.isoformat(),
        "updated_at": creds.updated_at.isoformat(),
    }


@router.delete("/linkedin")
async def delete_linkedin_credentials(
    user: User = Depends(get_current_user),
):
    """Delete stored LinkedIn credentials."""
    creds = await LinkedInCredentials.find_one(
        LinkedInCredentials.user_id == str(user.id)
    )
    if not creds:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No LinkedIn credentials found",
        )
    await creds.delete()
    return {"deleted": True}
