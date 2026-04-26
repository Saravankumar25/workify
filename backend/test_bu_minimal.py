"""
Minimal browser-use test using direct Playwright context creation.
This bypasses browser_use's BrowserProfile.kwargs_for_launch() which passes
'devtools' kwarg (not supported by Playwright 1.44+).
"""
import asyncio
import sys
import traceback
import logging

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
logger = logging.getLogger("test_minimal")


async def main():
    from playwright.async_api import async_playwright
    from browser_use import Agent
    from langchain_groq import ChatGroq
    
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        ",
        temperature=0,
        timeout=60,
        max_retries=2,
    )
    
    # Create Playwright context directly (bypasses browser_use's broken launch kwargs)
    logger.info("Starting Playwright...")
    playwright = await async_playwright().start()
    logger.info("Launching browser (headless=False)...")
    browser = await playwright.chromium.launch(
        headless=False,
        slow_mo=50.0,
        args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
    )
    context = await browser.new_context(
        viewport={"width": 1280, "height": 800},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
    )
    logger.info("Browser context ready!")
    
    # Construct Agent in thread (avoids asyncio.run() conflict in running loop)
    logger.info("Constructing agent in thread...")
    agent = await asyncio.to_thread(
        lambda: Agent(
            task="Go to https://www.google.com, search for 'hello world', and call done() with 'TASK_COMPLETE'",
            llm=llm,
            browser_context=context,
            use_vision=False,  # Groq doesn't support vision/multipart content
        )
    )
    logger.info(f"Agent ready: model={agent.model_name}")
    
    # Run agent
    logger.info("Running agent (max_steps=5)...")
    try:
        result = await agent.run(max_steps=5)
        print(f"\n{'='*50}")
        print(f"is_done():      {result.is_done()}")
        print(f"is_successful():{result.is_successful()}")
        print(f"final_result(): {repr(result.final_result())}")
        print(f"action_names(): {result.action_names()}")
        print(f"extracted_content: {result.extracted_content()}")
        print(f"{'='*50}\n")
        if result.is_done():
            logger.info("✅ Agent completed successfully!")
        else:
            logger.warning("⚠️ Agent did NOT call done() — ran out of steps or hit failures")
    except Exception as e:
        logger.error(f"agent.run() ERROR: {type(e).__name__}: {e}")
        traceback.print_exc()
    finally:
        await browser.close()
        await playwright.stop()
    
    logger.info("Done!")


if __name__ == "__main__":
    asyncio.run(main())
