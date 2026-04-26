"""Workify FastAPI entry point."""
from __future__ import annotations
import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(
        asyncio.WindowsProactorEventLoopPolicy()
    )


import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import settings, validate_runtime_environment
from db.mongo import close_db, init_db
from routers.applications import router as applications_router
from routers.apply import router as apply_router
from routers.auth import router as auth_router
from routers.compose import router as compose_router
from routers.credentials import router as credentials_router
from routers.health import router as health_router
from routers.jobs import router as jobs_router
from routers.logs import router as logs_router
from routers.profile import router as profile_router
from routers.settings import router as settings_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger("workify")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Workify API")
    validate_runtime_environment()
    await init_db()
    try:
        yield
    finally:
        await close_db()
        # Best-effort orphan Chromium cleanup on shutdown so restarts don't
        # accumulate zombie processes on long-lived Render instances.
        try:
            from services.apply_service import kill_orphan_chromium
            kill_orphan_chromium()
        except Exception:
            logger.exception("Orphan Chromium cleanup failed on shutdown")
        logger.info("Workify API shut down")


app = FastAPI(
    title="Workify API",
    description="LLM-powered automated job application platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (
    health_router,
    auth_router,
    profile_router,
    credentials_router,
    jobs_router,
    compose_router,
    apply_router,
    applications_router,
    settings_router,
    logs_router,
):
    app.include_router(r)


@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error — please try again"},
    )


@app.get("/")
async def root():
    return {"name": "Workify API", "version": "1.0.0", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn

    # In script mode, avoid re-importing app as "app:app" so the already-loaded
    # FastAPI instance and the Windows Proactor event-loop policy are preserved.
    uvicorn.run(
        app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=(sys.platform != "win32"),
    )
