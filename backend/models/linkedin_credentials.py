from datetime import datetime
from typing import Optional

import pymongo
from beanie import Document
from pydantic import Field
from pymongo import IndexModel


class LinkedInCredentials(Document):
    user_id: str
    encrypted_email: str
    encrypted_password: str
    session_cookies: Optional[str] = None
    cookies_valid_until: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "linkedin_credentials"
        indexes = [IndexModel([("user_id", pymongo.ASCENDING)], unique=True)]
