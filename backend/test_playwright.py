"""
Minimal test - just launch a Playwright browser.
"""
import asyncio
import sys
import logging

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s - %(message)s")

async def main():
    from playwright.async_api import async_playwright
    
    print("Starting Playwright...")
    async with async_playwright() as p:
        print("Launching browser (headless=False)...")
        browser = await p.chromium.launch(headless=False, slow_mo=50)
        print(f"Browser launched: {browser}")
        context = await browser.new_context()
        page = await context.new_page()
        print("Navigating to LinkedIn...")
        await page.goto("https://www.linkedin.com/login")
        print(f"Current URL: {page.url}")
        await asyncio.sleep(3)
        await browser.close()
        print("Done!")

if __name__ == "__main__":
    asyncio.run(main())
