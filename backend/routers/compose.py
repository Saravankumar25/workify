import json

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from beanie import PydanticObjectId

from core.dependencies import get_current_user
from core.rate_limit import reserve_artifact_export
from models.application import Application, ApplicationStatus
from models.artifact import Artifact, ArtifactType
from models.job import Job
from models.user import User
from services.llm_service import generate_resume_and_cl, generate_qa
from services.docs_service import export_resume_pdf, export_cover_letter_pdf
from services.profile_service import get_or_create_profile

router = APIRouter(prefix="/compose", tags=["Compose"])


class GenerateRequest(BaseModel):
    job_id: str
    application_id: Optional[str] = None


class ExportRequest(BaseModel):
    application_id: str
    resume_md: str
    cover_letter_md: str


@router.post("/generate")
async def generate_documents(
    body: GenerateRequest,
    user: User = Depends(get_current_user),
):
    """Generate tailored resume, cover letter, and Q&A for a job."""
    job = await Job.get(PydanticObjectId(body.job_id))
    if not job or job.user_id != str(user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    profile = await get_or_create_profile(str(user.id))
    profile_dict = {
        "full_name": profile.full_name,
        "email": profile.email,
        "phone": profile.phone,
        "location": profile.location,
        "linkedin_url": profile.linkedin_url,
        "portfolio_url": profile.portfolio_url,
        "summary": profile.summary,
        "skills": profile.skills,
        "experience": json.loads(profile.experience_json),
        "education": json.loads(profile.education_json),
        "projects": json.loads(profile.projects_json),
        "certifications": json.loads(profile.certifications_json),
        "languages": profile.languages,
    }

    job_dict = {
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "description": job.description,
        "skills": job.skills,
    }

    result = await generate_resume_and_cl(job_dict, profile_dict)
    qa = await generate_qa(job_dict, profile_dict)

    app = None
    if body.application_id:
        try:
            app = await Application.get(PydanticObjectId(body.application_id))
        except Exception:
            app = None
        if app and app.user_id != str(user.id):
            raise HTTPException(status_code=404, detail="Application not found")
    if not app:
        # Reuse existing (user_id, job_id) application to respect the unique
        # compound index instead of crashing on duplicate-key.
        app = await Application.find_one(
            Application.user_id == str(user.id),
            Application.job_id == str(job.id),
        )
    if not app:
        app = Application(
            user_id=str(user.id),
            job_id=str(job.id),
            status=ApplicationStatus.drafted,
        )
        await app.insert()
    else:
        app.status = ApplicationStatus.drafted
        await app.save()

    for art_type, content in [
        (ArtifactType.resume_md, result["resume_md"]),
        (ArtifactType.cover_letter_md, result["cover_letter_md"]),
        (ArtifactType.qa_json, json.dumps(qa)),
    ]:
        # Overwrite prior inline artifact of the same type so regenerating
        # on the same application doesn't accumulate duplicates.
        existing = await Artifact.find_one(
            Artifact.application_id == str(app.id),
            Artifact.type == art_type,
        )
        if existing:
            existing.content = content
            await existing.save()
        else:
            await Artifact(
                application_id=str(app.id),
                type=art_type,
                content=content,
            ).insert()

    return {
        "application_id": str(app.id),
        "resume_md": result["resume_md"],
        "cover_letter_md": result["cover_letter_md"],
        "qa": qa,
    }


@router.post("/export")
async def export_documents(
    body: ExportRequest,
    user: User = Depends(get_current_user),
):
    """Export resume and cover letter to PDF, upload to Cloudinary."""
    app = await Application.get(PydanticObjectId(body.application_id))
    if not app or app.user_id != str(user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Application not found"
        )

    # Cloudinary free-tier abuse protection: two uploads per export call,
    # so reserve twice. Either reservation failing aborts the call.
    await reserve_artifact_export(user)
    await reserve_artifact_export(user)

    profile = await get_or_create_profile(str(user.id))
    profile_dict = {"full_name": profile.full_name}

    resume_result = await export_resume_pdf(
        body.resume_md, profile_dict, str(app.id)
    )
    cl_result = await export_cover_letter_pdf(
        body.cover_letter_md, profile_dict, str(app.id)
    )

    resume_artifact = Artifact(
        application_id=str(app.id),
        type=ArtifactType.resume_pdf,
        cloudinary_url=resume_result["url"],
        cloudinary_public_id=resume_result["public_id"],
    )
    await resume_artifact.insert()

    cl_artifact = Artifact(
        application_id=str(app.id),
        type=ArtifactType.cover_letter_pdf,
        cloudinary_url=cl_result["url"],
        cloudinary_public_id=cl_result["public_id"],
    )
    await cl_artifact.insert()

    return {
        "resume_pdf_url": resume_result["url"],
        "cover_letter_pdf_url": cl_result["url"],
    }


@router.get("/artifacts/{application_id}")
async def list_artifacts(
    application_id: str,
    user: User = Depends(get_current_user),
):
    """List all artifacts for an application."""
    app = await Application.get(PydanticObjectId(application_id))
    if not app or app.user_id != str(user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Application not found"
        )

    artifacts = await Artifact.find(
        Artifact.application_id == application_id
    ).to_list()

    return {
        "artifacts": [
            {
                "id": str(a.id),
                "type": a.type.value,
                "cloudinary_url": a.cloudinary_url,
                "cloudinary_public_id": a.cloudinary_public_id,
                "content": a.content,
                "created_at": a.created_at.isoformat(),
            }
            for a in artifacts
        ]
    }
