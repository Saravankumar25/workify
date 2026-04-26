"""
Quick diagnostic: run the browser-use agent against a real LinkedIn job URL
and print the FULL result payload so we can see exactly what the agent returns.

Usage:
    python test_apply_debug.py
"""
import asyncio
import sys
import os
import logging
import traceback

# Must come before all other imports on Windows
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
logger = logging.getLogger("debug_apply")

# Suppress noisy browser-use telemetry
logging.getLogger("telemetry").setLevel(logging.WARNING)


async def main():
    from core.config import settings
    from core.security import decrypt
    from models.linkedin_credentials import LinkedInCredentials
    from db.mongo import init_db, close_db
    from browser_use import Agent
    from browser_use.browser import BrowserProfile
    from langchain_groq import ChatGroq

    logger.info("Initialising DB...")
    await init_db()

    # Get the first available user's LinkedIn credentials
    cred = await LinkedInCredentials.find_one({})
    if not cred:
        logger.error("No LinkedIn credentials in DB! Add them first.")
        await close_db()
        return

    li_email = decrypt(cred.encrypted_email)
    li_password = decrypt(cred.encrypted_password)
    logger.info(f"Testing with email: {li_email}")

    # Use a real LinkedIn Easy Apply job URL
    # Simple search URL - agent will find and apply to first Easy Apply job
    JOB_URL = "https://www.linkedin.com/jobs/search/?keywords=python+developer&location=India&f_LF=f_AL&f_E=2"

    task = f"""
You are applying to jobs on LinkedIn.
1. Go to {JOB_URL}
2. Find the FIRST job listing shown and click on it to view details.
3. If it has an 'Easy Apply' button, click it.
4. If prompted to log in, use email: {li_email} and password: {li_password}
5. Fill out the application with generic professional information (use any reasonable placeholder data for required fields).
6. Submit the application.
7. If you see a CAPTCHA, stop and call done() with text 'CAPTCHA_DETECTED'.
8. When successfully submitted, call done() with text 'APPLICATION_SUBMITTED: [job title] at [company name]'.
"""

    logger.info("Building browser profile (headless=False)...")
    # Pass browser_profile to Agent (not BrowserSession - that causes asyncio event loop issues)
    browser_profile = BrowserProfile(
        headless=False,
        slow_mo=100.0,
        user_data_dir=None,  # fresh ephemeral profile
    )

    llm = ChatGroq(
        model=settings.GROQ_MODEL,
        api_key=settings.GROQ_API_KEY,
        temperature=0,
        timeout=60,
        max_retries=0,
    )

    logger.info("Constructing Agent in thread (needed because Agent.__init__ calls asyncio.run() internally)...")
    try:
        agent = await asyncio.to_thread(
            lambda: Agent(
                task=task,
                llm=llm,
                browser_profile=browser_profile,
            )
        )
    except Exception as e:
        logger.error(f"Agent construction failed: {type(e).__name__}: {e}")
        traceback.print_exc()
        await close_db()
        return

    logger.info(f"Agent ready: model={agent.model_name}, version={agent.version}")

    logger.info("Running agent (max_steps=40)...")
    try:
        result = await agent.run(max_steps=40)
    except Exception as e:
        logger.error(f"Agent.run() failed: {type(e).__name__}: {e}")
        traceback.print_exc()
        await close_db()
        return

    # Print FULL result diagnostics
    print("\n" + "="*60)
    print("FULL RESULT DIAGNOSTICS")
    print("="*60)
    print(f"type(result):              {type(result).__name__}")
    print(f"result.is_done():          {result.is_done()}")
    print(f"result.is_successful():    {result.is_successful()}")
    print(f"result.final_result():     {repr(result.final_result())}")
    print(f"result.number_of_steps():  {result.number_of_steps()}")
    print(f"result.has_errors():       {result.has_errors()}")
    print(f"result.errors() (last 3):  {result.errors()[-3:]}")
    print(f"result.action_names() (last 5): {result.action_names()[-5:]}")
    print(f"result.urls() (last 3):    {result.urls()[-3:]}")
    
    all_content = result.extracted_content()
    print(f"\nresult.extracted_content() ({len(all_content)} items):")
    for i, c in enumerate(all_content):
        print(f"  [{i}] {repr(c[:200])}")

    print("="*60)

    if result.is_done() and result.is_successful():
        print("\n✅ APPLICATION SUBMITTED SUCCESSFULLY!")
    elif "APPLICATION_SUBMITTED" in str(result.final_result() or "").upper():
        print("\n✅ APPLICATION_SUBMITTED keyword found in final_result!")
    else:
        print("\n❌ Application was NOT submitted successfully")

    await close_db()
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
