"""FastAPI auth dependencies.

Two variants:
- get_current_user: reads Bearer token from Authorization header.
- get_current_user_sse: additionally accepts ?token= query param, because
  browser EventSource cannot set custom headers.

Defense in depth vs the classic `/auth/sync` race
-------------------------------------------------
The frontend is expected to call POST /auth/sync immediately after Firebase
sign-in so the Mongo User doc exists before any data-fetching pages mount.
If the frontend slips (race, network blip), we must NOT return 404 — that
makes the whole app flap between loading and error states. Instead we
**lazily create the User doc** from the verified Firebase claims, identical
to what /auth/sync does. Subsequent /auth/sync calls are idempotent.
"""
from __future__ import annotations

import logging

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pymongo.errors import DuplicateKeyError

from core.config import settings
from core.security import verify_firebase_token
from models.user import User

logger = logging.getLogger(__name__)
bearer_scheme = HTTPBearer(auto_error=False)


async def _lazy_create_user(decoded: dict) -> User:
    """Upsert a User doc from verified Firebase token claims. Mirrors the
    /auth/sync path so both converge on the same document shape."""
    uid = decoded["uid"]
    email = (decoded.get("email") or "").lower().strip()
    is_admin = bool(settings.ADMIN_EMAIL) and email == settings.ADMIN_EMAIL.lower()
    new = User(
        firebase_uid=uid,
        email=email,
        display_name=decoded.get("name", "") or "",
        photo_url=decoded.get("picture", "") or "",
        is_admin=is_admin,
        daily_apply_cap=settings.RATE_LIMIT_APPLIES_PER_DAY_DEFAULT,
    )
    try:
        await new.insert()
        logger.info(
            "Auto-provisioned User doc for uid=%s (frontend skipped /auth/sync)",
            uid,
        )
        return new
    except DuplicateKeyError:
        existing = await User.find_one(User.firebase_uid == uid)
        if existing is not None:
            return existing
        # Extremely rare — email collision with a different uid.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered under a different account",
        )


async def _user_from_decoded(decoded: dict) -> User:
    uid = decoded["uid"]
    user = await User.find_one(User.firebase_uid == uid)
    if not user:
        user = await _lazy_create_user(decoded)
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account deactivated"
        )
    return user


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> User:
    if creds is None or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer token",
        )
    decoded = verify_firebase_token(creds.credentials)
    return await _user_from_decoded(decoded)


async def get_current_user_sse(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> User:
    """Auth for SSE endpoints — accepts header OR ?token= query string."""
    token: str | None = None
    if creds and creds.credentials:
        token = creds.credentials
    else:
        token = request.query_params.get("token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Firebase token (header or ?token= query)",
        )
    decoded = verify_firebase_token(token)
    return await _user_from_decoded(decoded)
