"""Daily cap enforcement with atomic reservation.

No Redis. Correctness under parallel requests (and under future multi-worker
deployment) is guaranteed by MongoDB's atomic ``findOneAndUpdate`` with a
conditional filter — a winning writer increments the counter, a losing
writer's filter doesn't match and it raises 429.

Two caps live here:
- apply runs per day (PRD daily job cap)
- artifact (Cloudinary PDF export) per day — prevents free-tier abuse

Day boundary is UTC. The day string stored in the User doc lets us reset
lazily: if the stored day != today, the same atomic op overwrites the day
and resets the counter to 1.

Also houses the per-user LinkedIn circuit breaker state transitions (atomic
so parallel failures cannot over-increment).
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status

from core.config import settings
from models.user import User


def _today_utc() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")


async def _atomic_reserve(
    user: User,
    *,
    counter_field: str,
    day_field: str,
    cap: int,
    reset_message: str,
    limit_message: str,
) -> None:
    """Atomically increment counter_field if the stored day matches today and
    counter < cap. Otherwise: if the day has rolled over, reset to 1; if cap
    reached, raise 429.
    """
    today = _today_utc()
    coll = User.get_motor_collection()

    # Case 1: same day, under cap → increment.
    res = await coll.find_one_and_update(
        {"_id": user.id, day_field: today, counter_field: {"$lt": cap}},
        {"$inc": {counter_field: 1}},
    )
    if res is not None:
        return

    # Case 2: new day (or never-set day) → reset counter to 1.
    # Filter on day_field != today so we only reset once per boundary even if
    # many requests arrive simultaneously.
    res = await coll.find_one_and_update(
        {
            "_id": user.id,
            "$or": [{day_field: {"$ne": today}}, {day_field: None}],
        },
        {"$set": {day_field: today, counter_field: 1}},
    )
    if res is not None:
        return

    # Case 3: same day AND counter already at cap → denied.
    # (Re-read to distinguish between "cap reached" and "race lost on reset".)
    fresh = await coll.find_one({"_id": user.id}, {counter_field: 1, day_field: 1})
    current = (fresh or {}).get(counter_field, 0)
    if current >= cap:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=limit_message,
        )
    # Extremely rare race: another writer reset in between our queries.
    # Retry the same atomic increment once.
    res = await coll.find_one_and_update(
        {"_id": user.id, day_field: today, counter_field: {"$lt": cap}},
        {"$inc": {counter_field: 1}},
    )
    if res is None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=reset_message,
        )


async def _atomic_release(user_id, *, counter_field: str, day_field: str) -> None:
    """Decrement counter if still on the same UTC day. Used to roll back an
    apply-run reservation when the run is rejected before starting (circuit
    breaker open, invalid inputs, etc)."""
    today = _today_utc()
    coll = User.get_motor_collection()
    await coll.find_one_and_update(
        {"_id": user_id, day_field: today, counter_field: {"$gt": 0}},
        {"$inc": {counter_field: -1}},
    )


async def reserve_daily_apply(user: User) -> None:
    admin_cap = max(1, settings.RATE_LIMIT_APPLIES_PER_DAY_MAX)
    user_cap = max(1, min(user.daily_apply_cap, admin_cap))
    await _atomic_reserve(
        user,
        counter_field="daily_apply_count",
        day_field="daily_apply_day",
        cap=user_cap,
        reset_message="Daily apply cap reached. Try again after 00:00 UTC.",
        limit_message=(
            f"Your daily cap of {user_cap} applies reached. "
            "Raise it in Settings or wait until 00:00 UTC."
        ),
    )


async def release_daily_apply(user_id) -> None:
    await _atomic_release(
        user_id,
        counter_field="daily_apply_count",
        day_field="daily_apply_day",
    )


async def reserve_artifact_export(user: User) -> None:
    cap = max(1, settings.ARTIFACT_EXPORTS_PER_DAY_DEFAULT)
    await _atomic_reserve(
        user,
        counter_field="daily_artifact_count",
        day_field="daily_artifact_day",
        cap=cap,
        reset_message="Daily artifact export cap reached.",
        limit_message=(
            f"Daily Cloudinary export cap of {cap} reached. "
            "Resets at 00:00 UTC."
        ),
    )


# ---------- circuit breaker ----------

async def is_linkedin_circuit_open(user: User) -> Optional[datetime]:
    """Returns the reopen-at datetime if the per-user LinkedIn circuit is
    currently open, else None."""
    until = user.linkedin_circuit_open_until
    if until is None:
        return None
    if until <= datetime.utcnow():
        # Expired — reset state atomically so subsequent requests pass.
        coll = User.get_motor_collection()
        await coll.update_one(
            {"_id": user.id},
            {
                "$set": {
                    "linkedin_circuit_open_until": None,
                    "linkedin_consecutive_failures": 0,
                }
            },
        )
        return None
    return until


async def record_linkedin_failure(user_id) -> None:
    """Atomically increment consecutive failures; trip the breaker if the
    threshold is crossed within the rolling window."""
    now = datetime.utcnow()
    window_start = now - timedelta(
        seconds=settings.LINKEDIN_FAILURE_WINDOW_SECONDS
    )
    coll = User.get_motor_collection()

    # If last failure is outside the window, reset to 1. Otherwise increment.
    doc = await coll.find_one_and_update(
        {
            "_id": user_id,
            "$or": [
                {"linkedin_last_failure_at": None},
                {"linkedin_last_failure_at": {"$lt": window_start}},
            ],
        },
        {"$set": {"linkedin_consecutive_failures": 1, "linkedin_last_failure_at": now}},
        return_document=True,
    )
    if doc is None:
        doc = await coll.find_one_and_update(
            {"_id": user_id},
            {
                "$inc": {"linkedin_consecutive_failures": 1},
                "$set": {"linkedin_last_failure_at": now},
            },
            return_document=True,
        )
    if doc is None:
        return
    failures = int(doc.get("linkedin_consecutive_failures", 0) or 0)
    if failures >= settings.LINKEDIN_FAILURE_THRESHOLD:
        reopen_at = now + timedelta(
            seconds=settings.LINKEDIN_CIRCUIT_COOLDOWN_SECONDS
        )
        await coll.update_one(
            {"_id": user_id},
            {"$set": {"linkedin_circuit_open_until": reopen_at}},
        )


async def record_linkedin_success(user_id) -> None:
    """Clear failure streak on a successful apply run."""
    coll = User.get_motor_collection()
    await coll.update_one(
        {"_id": user_id},
        {
            "$set": {
                "linkedin_consecutive_failures": 0,
                "linkedin_circuit_open_until": None,
            }
        },
    )


# ---------- legacy entry point (kept for API compatibility) ----------

async def check_daily_apply_limit(user: User) -> None:
    """Retained for callers that want the old name — delegates to the
    atomic reserver. Callers now MUST pair this with release_daily_apply on
    pre-run rejection paths."""
    await reserve_daily_apply(user)
