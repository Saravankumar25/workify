from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pymongo.errors import DuplicateKeyError

from core.config import settings
from core.dependencies import get_current_user
from core.security import verify_firebase_token
from models.user import User

router = APIRouter(prefix="/auth", tags=["Auth"])
bearer = HTTPBearer(auto_error=False)


def _user_to_response(user: User) -> dict:
    return {
        "id": str(user.id),
        "firebase_uid": user.firebase_uid,
        "email": user.email,
        "display_name": user.display_name,
        "photo_url": user.photo_url,
        "is_admin": user.is_admin,
        "is_active": user.is_active,
        "daily_apply_cap": user.daily_apply_cap,
        "created_at": user.created_at.isoformat(),
    }


@router.post("/sync")
async def sync_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if creds is None or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Bearer token"
        )
    decoded = verify_firebase_token(creds.credentials)

    uid = decoded["uid"]
    email = (decoded.get("email") or "").lower().strip()

    user = await User.find_one(User.firebase_uid == uid)
    if user:
        return {"user_id": str(user.id), "email": user.email, "created": False}

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
    except DuplicateKeyError:
        # Concurrent /auth/sync from the same user — re-read.
        existing = await User.find_one(User.firebase_uid == uid)
        if existing is None:
            # Different user already owns this email (Firebase merged account).
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered under a different account",
            )
        return {"user_id": str(existing.id), "email": existing.email, "created": False}

    return {"user_id": str(new.id), "email": new.email, "created": True}


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return _user_to_response(user)
