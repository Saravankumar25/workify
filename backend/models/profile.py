from datetime import datetime
from typing import List

import pymongo
from beanie import Document
from pydantic import Field
from pymongo import IndexModel


class Profile(Document):
    user_id: str
    full_name: str = ""
    location: str = ""
    phone: str = ""
    email: str = ""
    linkedin_url: str = ""
    portfolio_url: str = ""
    linkedin_email: str = ""
    linkedin_password: str = ""
    summary: str = ""
    skills: List[str] = []
    experience_json: str = "[]"
    education_json: str = "[]"
    projects_json: str = "[]"
    certifications_json: str = "[]"
    languages: List[str] = []
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "profiles"
        indexes = [IndexModel([("user_id", pymongo.ASCENDING)], unique=True)]
