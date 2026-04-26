import json
import logging
from datetime import datetime, timezone

from models.profile import Profile
from services.llm_service import parse_resume_pdf
from utils.pdf import extract_text_from_pdf

logger = logging.getLogger(__name__)


async def get_or_create_profile(user_id: str) -> Profile:
    """Return the user's profile, creating a blank one if it doesn't exist."""
    profile = await Profile.find_one(Profile.user_id == user_id)
    if not profile:
        profile = Profile(user_id=user_id)
        await profile.insert()
    return profile


async def update_profile(user_id: str, data: dict) -> Profile:
    """Update profile fields from a dict of changes."""
    profile = await get_or_create_profile(user_id)

    allowed_fields = {
        "full_name", "location", "phone", "email",
        "linkedin_url", "portfolio_url", "summary",
        "skills", "experience_json", "education_json",
        "projects_json", "certifications_json", "languages",
        "linkedin_email", "linkedin_password",
    }

    set_data = {k: v for k, v in data.items() if k in allowed_fields}
    set_data["updated_at"] = datetime.now(timezone.utc)

    # Use motor directly — bypasses all Beanie abstraction and writes exactly
    # what we specify.
    await Profile.get_motor_collection().update_one(
        {"user_id": user_id},
        {"$set": set_data},
    )

    return await Profile.find_one(Profile.user_id == user_id)


async def import_pdf(file_bytes: bytes, user_id: str) -> dict:
    """Extract text from a PDF resume and parse it with the LLM.

    Returns a draft parsed profile (not yet saved).
    """
    text = extract_text_from_pdf(file_bytes)
    if not text.strip():
        raise ValueError("Could not extract text from the uploaded PDF")

    parsed = await parse_resume_pdf(text)
    return parsed


async def confirm_import(user_id: str, parsed_data: dict) -> Profile:
    """Confirm and save the LLM-parsed resume data into the user's profile."""
    profile = await get_or_create_profile(user_id)

    field_map = {
        "full_name": "full_name",
        "email": "email",
        "phone": "phone",
        "location": "location",
        "linkedin_url": "linkedin_url",
        "portfolio_url": "portfolio_url",
        "summary": "summary",
        "skills": "skills",
        "languages": "languages",
    }

    for source_key, profile_key in field_map.items():
        val = parsed_data.get(source_key)
        if val:
            setattr(profile, profile_key, val)

    json_fields = {
        "experience": "experience_json",
        "education": "education_json",
        "projects": "projects_json",
        "certifications": "certifications_json",
    }

    for source_key, profile_key in json_fields.items():
        val = parsed_data.get(source_key)
        if val and isinstance(val, list):
            setattr(profile, profile_key, json.dumps(val))

    profile.updated_at = datetime.now(timezone.utc)
    await profile.save()
    return profile
