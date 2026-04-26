"""Firebase token verification + Fernet encryption helpers.

Firebase Admin must be initialised exactly once per process, even under
uvicorn --reload. We guard with firebase_admin._apps.
"""
from __future__ import annotations

import logging
from typing import Any

import firebase_admin
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, status
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials

from core.config import settings

logger = logging.getLogger(__name__)

_fernet: Fernet | None = None
_firebase_app: firebase_admin.App | None = None


def _init_firebase() -> firebase_admin.App:
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app
    if firebase_admin._apps:
        _firebase_app = firebase_admin.get_app()
        return _firebase_app
    cred = credentials.Certificate(settings.firebase_credentials())
    _firebase_app = firebase_admin.initialize_app(cred)
    logger.info("Firebase Admin initialised for project %s",
                settings.firebase_credentials().get("project_id"))
    return _firebase_app


# Initialise eagerly so config errors surface at startup, not on first auth call.
_init_firebase()


def get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(settings.FERNET_KEY.encode())
    return _fernet


def verify_firebase_token(token: str) -> dict[str, Any]:
    """Verify a Firebase ID token. Raises HTTPException on failure."""
    if not token or not isinstance(token, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Firebase ID token",
        )
    _init_firebase()
    try:
        # check_revoked=False — avoids an extra network round-trip per request.
        decoded = firebase_auth.verify_id_token(token, check_revoked=False)
    except firebase_auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired"
        )
    except firebase_auth.RevokedIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked"
        )
    except firebase_auth.InvalidIdTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
        )
    except Exception as exc:  # network / cert fetch failures
        logger.exception("Firebase verify failure")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification failed: {exc}",
        )
    if not decoded.get("uid"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing uid claim",
        )
    return decoded


def encrypt(value: str) -> str:
    return get_fernet().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    try:
        return get_fernet().decrypt(value.encode()).decode()
    except InvalidToken as exc:
        # Key rotated or tampered ciphertext — never leak details.
        logger.error("Fernet decrypt failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stored credential could not be decrypted",
        )
