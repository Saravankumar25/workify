from datetime import datetime
from enum import Enum
from typing import List, Optional

import pymongo
from beanie import Document
from pydantic import Field
from pymongo import IndexModel


class RunKind(str, Enum):
    scrape = "scrape"
    compose = "compose"
    apply = "apply"


class Run(Document):
    user_id: str
    application_id: Optional[str] = None
    kind: RunKind
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    success: Optional[bool] = None
    log_lines: List[str] = []
    metadata: dict = {}

    class Settings:
        name = "runs"
        indexes = [
            IndexModel([("user_id", pymongo.ASCENDING)]),
            IndexModel([("application_id", pymongo.ASCENDING)]),
            IndexModel(
                [("user_id", pymongo.ASCENDING), ("kind", pymongo.ASCENDING),
                 ("started_at", pymongo.DESCENDING)]
            ),
        ]
