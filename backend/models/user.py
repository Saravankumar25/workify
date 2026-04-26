from datetime import datetime
from typing import Optional

import pymongo
from beanie import Document
from pydantic import Field
from pymongo import IndexModel


class User(Document):
    firebase_uid: str
    email: str
    display_name: str = ""
    photo_url: str = ""
    is_admin: bool = False
    is_active: bool = True
    daily_apply_cap: int = 20
    # --- atomic daily counters (reset lazily when day changes) ---
    # Counters are modified only via atomic find_one_and_update in
    # core.rate_limit.reserve_* — never written from application code.
    daily_apply_count: int = 0
    daily_apply_day: Optional[str] = None          # YYYY-MM-DD UTC
    daily_artifact_count: int = 0
    daily_artifact_day: Optional[str] = None       # YYYY-MM-DD UTC
    # --- per-user LinkedIn circuit breaker state ---
    linkedin_consecutive_failures: int = 0
    linkedin_last_failure_at: Optional[datetime] = None
    linkedin_circuit_open_until: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"
        indexes = [
            IndexModel([("firebase_uid", pymongo.ASCENDING)], unique=True),
            IndexModel([("email", pymongo.ASCENDING)], unique=True),
        ]
