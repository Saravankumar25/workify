"""
Minimal test to trigger Playwright failure with diagnosis logging.
"""
import asyncio
import sys
import logging

# Must come before all other imports on Windows
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
logger = logging.getLogger("diagnosis_test")

async def test_playwright_context():
    """Directly call the failing function to see diagnosis logs."""
    from services.apply_service import _create_playwright_context

    logger.info("Starting Playwright context creation test...")
    try:
        playwright, browser, context = await _create_playwright_context()
        logger.info("SUCCESS: Playwright context created")
        await browser.close()
        await playwright.stop()
    except Exception as exc:
        logger.error(f"FAILED: {exc}")
        raise

if __name__ == "__main__":
    asyncio.run(test_playwright_context())