"""Health endpoint.

- `/health`       → liveness: returns 200 unconditionally so Render's health
                    check and frontend uptime checks don't flap on a slow
                    Mongo/Groq response.
- `/health/ready` → readiness: probes each upstream (Mongo, Firebase, Groq,
                    Cloudinary). Returns 503 if any required service is down.
"""
from __future__ import annotations

import asyncio
import logging

import firebase_admin
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from core.config import settings
from db.mongo import is_db_ready, ping as mongo_ping

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Health"])


@router.get("/health")
async def liveness():
    return {
        "status": "ok",
        "service": "workify-api",
        "version": "1.0.0",
        "db_ready": is_db_ready(),
    }


@router.get("/health/ready")
async def readiness():
    checks: dict = {}

    # MongoDB
    checks["mongodb"] = await mongo_ping()

    # Firebase Admin — was it initialised?
    checks["firebase"] = bool(firebase_admin._apps)

    # Groq — cheap models.list call with short timeout.
    checks["groq"] = await _check_groq()

    # Cloudinary — only mark ok if creds were configured; we don't burn the
    # API budget on every health check. "configured" is enough for readiness.
    checks["cloudinary"] = bool(
        settings.CLOUDINARY_CLOUD_NAME
        and settings.CLOUDINARY_API_KEY
        and settings.CLOUDINARY_API_SECRET
    )

    required = ("mongodb", "firebase", "groq")
    ok = all(checks[k] for k in required)
    status_code = 200 if ok else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": "ok" if ok else "degraded", "checks": checks},
    )


async def _check_groq() -> bool:
    try:
        from core.llm_pool import next_groq_key
        from groq import AsyncGroq

        key = next_groq_key()
        if not key:
            logger.warning("Groq health check: no keys configured")
            return False
        client = AsyncGroq(api_key=key, timeout=5.0)
        await asyncio.wait_for(client.models.list(), timeout=5.0)
        return True
    except Exception as exc:
        logger.warning("Groq health check failed: %s", exc)
        return False


@router.get("/health/llm-pool")
async def llm_pool_status():
    """Shows how many keys are configured per provider. No keys exposed."""
    from core.config import settings
    return {
        "groq_keys": len(settings.groq_keys_list),
        "gemini_keys": len(settings.gemini_keys_list),
        "mistral_keys": len(settings.mistral_keys_list),
        "task_routing": {
            "resume_generation": "groq → gemini",
            "cover_letter": "groq → gemini",
            "qa_generation": "mistral → groq",
            "pdf_parsing": "mistral → groq",
            "browser_agent": "gemini → groq",
        },
    }


@router.get("/test-browser")
async def test_browser():
    """Verify Playwright and Chromium work in this environment."""
    try:
        from services.apply_service import _create_playwright_context

        playwright, browser, context = await _create_playwright_context(
            headless=True,
            slow_mo=0.0,
            storage_state=None,
        )
        try:
            page = await context.new_page()
            await page.goto("https://example.com")
            title = await page.title()
        finally:
            await context.close()
            await browser.close()
            await playwright.stop()
        return {"status": "ok", "test_page_title": title}
    except Exception as exc:
        logger.error("Browser health check failed: %s", exc)
        return JSONResponse(
            status_code=503,
            content={"status": "error", "detail": str(exc)},
        )
