from datetime import datetime
from enum import Enum

import pymongo
from beanie import Document
from pydantic import Field
from pymongo import IndexModel


class ArtifactType(str, Enum):
    resume_pdf = "resume_pdf"
    cover_letter_pdf = "cover_letter_pdf"
    resume_md = "resume_md"
    cover_letter_md = "cover_letter_md"
    qa_json = "qa_json"
    screenshot = "screenshot"
    raw_job_json = "raw_job_json"
    imported_resume = "imported_resume"


class Artifact(Document):
    application_id: str
    type: ArtifactType
    # Cloudinary fields are empty for inline text artifacts (resume_md, cover_letter_md, qa_json).
    cloudinary_url: str = ""
    cloudinary_public_id: str = ""
    # Inline content for markdown + JSON artifacts — avoids an extra Cloudinary
    # round-trip for text-only artifacts.
    content: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "artifacts"
        indexes = [
            IndexModel([("application_id", pymongo.ASCENDING)]),
            IndexModel(
                [("application_id", pymongo.ASCENDING), ("type", pymongo.ASCENDING)]
            ),
        ]
