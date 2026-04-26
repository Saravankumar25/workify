"""MongoDB Atlas connection + Beanie ODM init.

Uses AsyncIOMotorClient with server selection timeout so startup surfaces
connection errors in Render logs quickly. If MongoDB is unreachable the app
still starts in degraded mode — the liveness endpoint responds but readiness
reports the DB as down.
"""
from __future__ import annotations

import logging

from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from core.config import settings
from models.application import Application
from models.artifact import Artifact
from models.job import Job
from models.linkedin_credentials import LinkedInCredentials
from models.profile import Profile
from models.run import Run
from models.user import User

logger = logging.getLogger(__name__)

ALL_MODELS = [User, Profile, LinkedInCredentials, Job, Application, Artifact, Run]

_client: AsyncIOMotorClient | None = None
_db_ready: bool = False


def _tls_kwargs() -> dict:
    """Return TLS CA file path from certifi when available."""
    try:
        import certifi
        return {"tlsCAFile": certifi.where()}
    except ImportError:
        return {}


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=10_000,
            connectTimeoutMS=10_000,
            maxPoolSize=50,
            retryWrites=True,
            **_tls_kwargs(),
        )
    return _client


def is_db_ready() -> bool:
    return _db_ready


async def init_db() -> None:
    global _db_ready
    client = get_client()
    try:
        await client.admin.command("ping")
    except Exception as exc:
        logger.error(
            "MongoDB connection failed at startup: %s. "
            "Check: 1) MONGODB_URL is correct, 2) your IP is whitelisted "
            "in MongoDB Atlas, 3) the cluster is not paused. "
            "App will start in DEGRADED mode — all DB operations will fail.",
            exc,
        )
        _db_ready = False
        return

    db = client[settings.MONGODB_DB_NAME]
    await init_beanie(database=db, document_models=ALL_MODELS)
    _db_ready = True
    logger.info(
        "Connected to MongoDB database=%s collections=%d",
        settings.MONGODB_DB_NAME,
        len(ALL_MODELS),
    )


async def ping() -> bool:
    try:
        await get_client().admin.command("ping")
        return True
    except Exception as exc:
        logger.warning("MongoDB ping failed: %s", exc)
        return False


async def close_db() -> None:
    global _client, _db_ready
    if _client is not None:
        _client.close()
        _client = None
        _db_ready = False
