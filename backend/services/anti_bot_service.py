import asyncio
import logging
import random
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)


async def add_human_delay() -> None:
    """Add random jitter (20-80 ms) to mimic human interaction timing."""
    delay_ms = random.randint(20, 80)
    await asyncio.sleep(delay_ms / 1000.0)


async def check_robots_txt(url: str) -> bool:
    """Basic robots.txt compliance check.

    Returns True if the path is likely allowed, False if disallowed.
    This is a best-effort check — not a full robots.txt parser.
    """
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(robots_url)
            if resp.status_code != 200:
                return True

            path = parsed.path or "/"
            for line in resp.text.splitlines():
                line = line.strip().lower()
                if line.startswith("disallow:"):
                    disallowed = line.split(":", 1)[1].strip()
                    if disallowed and path.startswith(disallowed):
                        logger.warning(
                            "Path %s may be disallowed by robots.txt", path
                        )
                        return False
            return True

    except Exception as exc:
        logger.warning("Could not fetch robots.txt for %s: %s", url, exc)
        return True
