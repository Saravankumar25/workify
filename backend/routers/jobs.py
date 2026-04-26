import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from pymongo.errors import DuplicateKeyError
from typing import Optional

from beanie import PydanticObjectId

from core.dependencies import get_current_user
from models.job import Job
from models.user import User
from services.scraper_service import ScraperError, scrape_linkedin_jobs

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/jobs", tags=["Jobs"])


class JobSearchRequest(BaseModel):
    query: str
    location: str = ""
    limit: int = 10


@router.post("/search")
async def search_jobs(
    body: JobSearchRequest,
    user: User = Depends(get_current_user),
):
    """Scrape LinkedIn for jobs matching the query.

    Failure modes — important for UX:
    - 400 if the query is empty.
    - 502 if the scraper itself fails (network / LinkedIn block / timeout).
      We explicitly do NOT return an empty list in that case, because the
      frontend's "No jobs found" copy would be a lie.
    - 200 with empty ``jobs`` only if LinkedIn legitimately had nothing.
    """
    query = (body.query or "").strip()
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query must not be empty",
        )
    try:
        raw_jobs = await scrape_linkedin_jobs(
            query=query,
            location=body.location or "",
            limit=body.limit,
            user_id=str(user.id),
        )
    except ScraperError as exc:
        logger.warning("Scraper infrastructure failure: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Job search is temporarily unavailable. LinkedIn could not be "
                "reached. Please retry in a minute."
            ),
        ) from exc
    except Exception as exc:  # defensive — never let a scraper bug 500 us
        logger.exception("Unexpected scraper error")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Scraper error: {exc}",
        ) from exc

    saved = []
    for jdata in raw_jobs:
        url = jdata.get("url", "")
        if not url:
            continue
        existing = await Job.find_one(Job.url == url)
        if existing:
            # Surface a copy owned by this user. Other users' jobs are hidden
            # by the list endpoint's user_id filter anyway, but dedup lets us
            # preserve LinkedIn's global URL-uniqueness constraint.
            saved.append(existing)
            continue

        job = Job(
            user_id=str(user.id),
            title=jdata.get("title", "") or "Untitled",
            company=jdata.get("company", "") or "Unknown",
            location=jdata.get("location", ""),
            url=url,
            description=jdata.get("description", ""),
            source="linkedin",
        )
        try:
            await job.insert()
        except DuplicateKeyError:
            # Race with another request inserting the same URL.
            existing = await Job.find_one(Job.url == url)
            if existing is not None:
                saved.append(existing)
            continue
        saved.append(job)

    return {
        "jobs": [_job_to_dict(j) for j in saved],
        "total": len(saved),
    }


@router.get("")
async def list_jobs(
    user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """List the user's scraped jobs with pagination."""
    query = Job.find(Job.user_id == str(user.id))
    total = await query.count()
    items = await query.sort(-Job.captured_at).skip(skip).limit(limit).to_list()
    return {
        "jobs": [_job_to_dict(j) for j in items],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/{job_id}")
async def get_job(
    job_id: str,
    user: User = Depends(get_current_user),
):
    """Get a single job by ID."""
    job = await Job.get(PydanticObjectId(job_id))
    if not job or job.user_id != str(user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return _job_to_dict(job)


@router.delete("/{job_id}")
async def delete_job(
    job_id: str,
    user: User = Depends(get_current_user),
):
    """Delete a scraped job."""
    job = await Job.get(PydanticObjectId(job_id))
    if not job or job.user_id != str(user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    await job.delete()
    return {"deleted": True}


def _job_to_dict(job: Job) -> dict:
    return {
        "id": str(job.id),
        "user_id": job.user_id,
        "source": job.source,
        "external_id": job.external_id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "url": job.url,
        "description": job.description,
        "min_salary": job.min_salary,
        "max_salary": job.max_salary,
        "currency": job.currency,
        "skills": job.skills,
        "captured_at": job.captured_at.isoformat(),
    }
