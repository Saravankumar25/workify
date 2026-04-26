from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel
from typing import List, Optional

from core.dependencies import get_current_user
from models.user import User
from services.profile_service import (
    get_or_create_profile,
    update_profile,
    import_pdf,
    confirm_import,
)

router = APIRouter(prefix="/profile", tags=["Profile"])


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    location: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    linkedin_email: Optional[str] = None
    linkedin_password: Optional[str] = None
    summary: Optional[str] = None
    skills: Optional[List[str]] = None
    experience_json: Optional[str] = None
    education_json: Optional[str] = None
    projects_json: Optional[str] = None
    certifications_json: Optional[str] = None
    languages: Optional[List[str]] = None


class ConfirmImportRequest(BaseModel):
    parsed_data: dict


def _profile_to_dict(profile) -> dict:
    return {
        "id": str(profile.id),
        "user_id": profile.user_id,
        "full_name": profile.full_name,
        "location": profile.location,
        "phone": profile.phone,
        "email": profile.email,
        "linkedin_url": profile.linkedin_url,
        "portfolio_url": profile.portfolio_url,
        "linkedin_email": profile.linkedin_email,
        "linkedin_password": profile.linkedin_password,
        "summary": profile.summary,
        "skills": profile.skills,
        "experience_json": profile.experience_json,
        "education_json": profile.education_json,
        "projects_json": profile.projects_json,
        "certifications_json": profile.certifications_json,
        "languages": profile.languages,
        "updated_at": profile.updated_at.isoformat(),
    }


@router.get("")
async def get_profile(user: User = Depends(get_current_user)):
    """Get the current user's profile."""
    profile = await get_or_create_profile(str(user.id))
    return _profile_to_dict(profile)


@router.put("")
async def update_user_profile(
    body: ProfileUpdate,
    user: User = Depends(get_current_user),
):
    """Update the current user's profile."""
    data = body.model_dump(exclude_none=True)
    profile = await update_profile(str(user.id), data)
    return _profile_to_dict(profile)


@router.post("/import-pdf")
async def import_pdf_resume(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    """Upload a PDF resume, parse with LLM, and return a draft."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are accepted",
        )

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large (max 10 MB)",
        )

    try:
        parsed = await import_pdf(contents, str(user.id))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    return {"parsed": parsed, "message": "Review and confirm to save to your profile"}


@router.put("/confirm-import")
async def confirm_pdf_import(
    body: ConfirmImportRequest,
    user: User = Depends(get_current_user),
):
    """Confirm the LLM-parsed resume data and save to profile."""
    profile = await confirm_import(str(user.id), body.parsed_data)
    return _profile_to_dict(profile)
