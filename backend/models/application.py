from datetime import datetime
from enum import Enum
from typing import Optional

import pymongo
from beanie import Document
from pydantic import Field
from pymongo import IndexModel


class ApplicationStatus(str, Enum):
    planned = "planned"
    drafted = "drafted"
    submitted = "submitted"
    failed = "failed"
    needs_action = "needs_action"


class Application(Document):
    user_id: str
    job_id: str
    status: ApplicationStatus = ApplicationStatus.planned
    submitted_at: Optional[datetime] = None
    notes: str = ""
    run_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "applications"
        indexes = [
            IndexModel([("user_id", pymongo.ASCENDING)]),
            IndexModel([("status", pymongo.ASCENDING)]),
            IndexModel(
                [("user_id", pymongo.ASCENDING), ("job_id", pymongo.ASCENDING)],
                unique=True,
            ),
            IndexModel([("created_at", pymongo.DESCENDING)]),
        ]
