from datetime import datetime
from typing import List, Optional

import pymongo
from beanie import Document
from pydantic import Field
from pymongo import IndexModel


class Job(Document):
    user_id: str
    source: str = "linkedin"
    external_id: Optional[str] = None
    title: str
    company: str
    location: str = ""
    url: str
    description: str = ""
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
    currency: Optional[str] = None
    skills: List[str] = []
    captured_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "jobs"
        indexes = [
            IndexModel([("user_id", pymongo.ASCENDING)]),
            IndexModel([("url", pymongo.ASCENDING)], unique=True),
            IndexModel([("captured_at", pymongo.DESCENDING)]),
        ]
