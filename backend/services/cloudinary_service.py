"""Cloudinary uploads.

Cloudinary's Python SDK is synchronous and does HTTP I/O; we wrap calls in
asyncio.to_thread to avoid blocking the event loop (browser-use + SSE run
concurrently).

Retries ONLY on transient network/5xx (see is_cloudinary_retryable).
Every upload has a hard asyncio timeout; blocked threads cannot leak.
"""
from __future__ import annotations

import asyncio
import io
import logging

import cloudinary
import cloudinary.uploader

from core.config import settings
from utils.retry import async_retry, is_cloudinary_retryable

logger = logging.getLogger(__name__)

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True,
)


def _configured() -> bool:
    return bool(
        settings.CLOUDINARY_CLOUD_NAME
        and settings.CLOUDINARY_API_KEY
        and settings.CLOUDINARY_API_SECRET
    )


def _upload_kwargs(public_id: str, folder: str) -> dict:
    return dict(
        public_id=public_id,
        folder=folder,
        resource_type="raw",
        overwrite=True,
        use_filename=False,
        unique_filename=False,
        timeout=settings.PDF_UPLOAD_TIMEOUT_SECONDS,
    )


@async_retry(
    max_attempts=3,
    delay=1.0,
    backoff=2.0,
    max_delay=10.0,
    should_retry=is_cloudinary_retryable,
)
async def upload_pdf(file_path: str, public_id: str, folder: str = "workify") -> dict:
    if not _configured():
        raise RuntimeError("Cloudinary credentials not configured")

    result = await asyncio.wait_for(
        asyncio.to_thread(
            cloudinary.uploader.upload,
            file_path,
            **_upload_kwargs(public_id, folder),
        ),
        timeout=settings.PDF_UPLOAD_TIMEOUT_SECONDS + 5,
    )
    return {"url": result["secure_url"], "public_id": result["public_id"]}


@async_retry(
    max_attempts=3,
    delay=1.0,
    backoff=2.0,
    max_delay=10.0,
    should_retry=is_cloudinary_retryable,
)
async def upload_pdf_bytes(
    pdf_bytes: bytes, public_id: str, folder: str = "workify"
) -> dict:
    if not _configured():
        raise RuntimeError("Cloudinary credentials not configured")
    if not pdf_bytes:
        raise ValueError("Cannot upload empty PDF")

    buf = io.BytesIO(pdf_bytes)
    buf.seek(0)

    result = await asyncio.wait_for(
        asyncio.to_thread(
            cloudinary.uploader.upload,
            buf,
            **_upload_kwargs(public_id, folder),
        ),
        timeout=settings.PDF_UPLOAD_TIMEOUT_SECONDS + 5,
    )
    return {"url": result["secure_url"], "public_id": result["public_id"]}


async def delete_asset(public_id: str) -> None:
    if not _configured():
        return
    try:
        await asyncio.wait_for(
            asyncio.to_thread(
                cloudinary.uploader.destroy, public_id, resource_type="raw"
            ),
            timeout=settings.PDF_UPLOAD_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        logger.warning("Failed to delete Cloudinary asset %s: %s", public_id, exc)
