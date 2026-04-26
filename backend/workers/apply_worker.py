#!/usr/bin/env python3
"""
apply_worker.py — LinkedIn apply worker.

Can run two ways:
  1. In-process (default): called directly by apply_service via asyncio.to_thread.
     log_fn receives progress messages; run_apply() returns a result dict.
  2. Standalone CLI: python apply_worker.py — reads config from stdin JSON,
     emits stdout JSON lines (legacy / debugging path).
"""
import asyncio
import json
import os
import sys
import tempfile
import traceback

import logging
logging.basicConfig(level=logging.WARNING, stream=sys.stderr)


def emit(event: str, **kwargs):
    """Write a JSON line to stdout. Used only in standalone CLI mode."""
    line = json.dumps({"event": event, **kwargs})
    print(line, flush=True)


async def _diagnose(history, agent, log) -> tuple[bool, bool, str]:
    """
    Log full AgentHistoryList diagnostics and capture browser state.
    Returns (is_done, is_successful, final_str).
    """
    log("=== AGENT DIAGNOSTICS ===")

    is_done = False
    is_successful = False

    try:
        is_done = history.is_done()
        log(f"  is_done           = {is_done}")
    except Exception as e:
        log(f"  is_done           = ERROR: {e}")

    try:
        is_successful = history.is_successful()
        log(f"  is_successful     = {is_successful}")
    except Exception as e:
        log(f"  is_successful     = ERROR: {e}")

    final_str = ""
    try:
        fr = history.final_result()
        log(f"  final_result      = {repr(fr)[:300]}")
        if fr:
            final_str = str(fr)
    except Exception as e:
        log(f"  final_result      = ERROR: {e}")

    try:
        actions = history.action_names()
        log(f"  action_names      = {actions}")
        log(f"  total_steps_taken = {len(actions) if actions else 0}")
    except Exception as e:
        log(f"  action_names      = ERROR: {e}")

    try:
        urls = history.urls()
        log(f"  urls_visited      = {urls}")
        if urls:
            log(f"  final_url         = {urls[-1]}")
    except Exception as e:
        log(f"  urls              = ERROR: {e}")

    try:
        errors = history.errors()
        non_empty = [str(e)[:150] for e in (errors or []) if e]
        log(f"  errors            = {non_empty}")
    except Exception as e:
        log(f"  errors            = ERROR: {e}")

    try:
        content_list = history.extracted_content()
        trimmed = [c[:100] for c in (content_list or []) if c]
        log(f"  extracted_content = {trimmed[:5]}")
        if not final_str and trimmed:
            for piece in reversed(content_list or []):
                if piece and piece.strip():
                    final_str = piece.strip()
                    break
    except Exception as e:
        log(f"  extracted_content = ERROR: {e}")

    try:
        page = agent.browser_session.agent_current_page
        if page and not page.is_closed():
            current_url = page.url
            log(f"  current_url       = {current_url}")

            if not is_done:
                try:
                    screenshot_path = os.path.join(
                        tempfile.gettempdir(),
                        f"workify_apply_debug_{os.getpid()}.png",
                    )
                    await page.screenshot(path=screenshot_path, full_page=False)
                    log(f"  screenshot        = {screenshot_path}")
                except Exception as ss_err:
                    log(f"  screenshot        = FAILED: {ss_err}")
        else:
            log("  current_url       = (page closed or unavailable)")
    except Exception as e:
        log(f"  browser_state     = ERROR: {e}")

    log("=== END DIAGNOSTICS ===")
    return is_done, is_successful, final_str


async def run_apply(config: dict, log_fn=None) -> dict:
    """
    Run the LinkedIn apply automation.

    log_fn: callable(str) for progress messages. When None (standalone mode),
            messages are emitted as stdout JSON lines instead.
    Returns a result dict with at least {"status": str, "message": str}.
    """
    def log(message: str):
        if log_fn is not None:
            log_fn(message)
        else:
            emit("log", message=message)

    job_url = config["job_url"]
    resume_md = config.get("resume_md", "")
    cover_letter_md = config.get("cover_letter_md", "")
    qa_pairs = config.get("qa_pairs", [])
    li_email = config["linkedin_email"]
    li_password = config["linkedin_password"]
    session_cookies = config.get("session_cookies", None)
    groq_api_key = config["groq_api_key"]
    _APPLY_MODEL = "llama-3.1-8b-instant"
    _requested = config.get("groq_model", _APPLY_MODEL)
    groq_model = _APPLY_MODEL if "70b" in _requested or "versatile" in _requested else _requested

    gemini_api_key = config.get("gemini_api_key", "")
    gemini_model = config.get("gemini_model", "gemini-2.0-flash")

    max_steps = config.get("max_steps", 75)
    headless = config.get("headless", True)
    slow_mo = float(config.get("slowmo_ms", 0))

    log(f"Worker started. Model: {groq_model} (requested: {_requested}) | max_steps: {max_steps} | headless: {headless}")

    try:
        from langchain_groq import ChatGroq
        from browser_use import Agent, BrowserConfig
        from browser_use.browser.profile import BrowserLaunchArgs

        # browser-use passes devtools=False to playwright.chromium.launch() but
        # current Playwright dropped that kwarg. Patch model_dump() so it never emits it.
        _orig_dump = BrowserLaunchArgs.model_dump
        def _dump_no_devtools(self, **kw):
            d = _orig_dump(self, **kw)
            d.pop("devtools", None)
            return d
        BrowserLaunchArgs.model_dump = _dump_no_devtools

        log("Libraries loaded. Creating LLM...")

        llm = None
        if gemini_api_key:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore[import]
                llm = ChatGoogleGenerativeAI(
                    model=gemini_model,
                    google_api_key=gemini_api_key,
                    temperature=0.0,
                )
                log(f"Using Gemini model: {gemini_model}")
            except Exception as _gemini_err:
                log(f"Gemini init failed ({type(_gemini_err).__name__}), falling back to Groq")
                llm = None

        if llm is None:
            llm = ChatGroq(
                api_key=groq_api_key,
                model=groq_model,
                temperature=0.0,
                max_retries=6,
            )
            log(f"Using Groq model: {groq_model}")

        log("LLM ready. Building task...")

        qa_block = ""
        if qa_pairs:
            qa_block = "\nSCREENING QUESTIONS — answer these exactly as written:\n"
            for pair in qa_pairs:
                qa_block += f"Q: {pair.get('question', '')}\nA: {pair.get('answer', '')}\n"

        task = (
            "You are a job application bot. Your ONLY goal is to submit a LinkedIn Easy Apply "
            "application. You must NOT stop until you have called done() with one of the required "
            "exit codes listed at the bottom.\n\n"

            "=== CREDENTIALS ===\n"
            f"LinkedIn Email: {li_email}\n"
            f"LinkedIn Password: {li_password}\n\n"

            "=== JOB TO APPLY FOR ===\n"
            f"{job_url}\n\n"

            "=== APPLICANT RESUME ===\n"
            "Use the information below to fill in every form field:\n"
            f"{resume_md[:1200]}\n\n"

            "=== COVER LETTER ===\n"
            f"{cover_letter_md[:400]}\n"
            f"{qa_block}\n"

            "=== STEP-BY-STEP INSTRUCTIONS ===\n\n"

            f"Step 1 — NAVIGATE\n"
            f"  Go to: {job_url}\n\n"

            "Step 2 — CHECK LOGIN STATUS\n"
            "  Look at the current page:\n"
            "  • If the URL contains /login, /authwall, or /signup, or you see a sign-in form:\n"
            f"    → Find the email input and type: {li_email}\n"
            f"    → Find the password input and type: {li_password}\n"
            "    → Click the Sign In / Continue button\n"
            "    → Wait for the page to load (you should land on /feed or a LinkedIn home page)\n"
            "    → Then go back to the job URL\n"
            "  • If you see a CAPTCHA, verification code, or security challenge:\n"
            "    → call done(\"CAPTCHA_DETECTED\") immediately\n"
            "  • If you are already on a LinkedIn page that is NOT a login page, continue\n\n"

            "Step 3 — VERIFY JOB PAGE\n"
            f"  You must be on the page: {job_url}\n"
            "  If not, navigate back to it.\n\n"

            "Step 4 — FIND EASY APPLY\n"
            "  • Look for a button that says exactly 'Easy Apply' (blue/green button near the job title)\n"
            "  • If the button says 'Apply' and clicking it opens a different website: "
            "    call done(\"NO_EASY_APPLY\")\n"
            "  • If you see 'Applied' (already submitted): call done(\"ALREADY_APPLIED\")\n"
            "  • If you see the Easy Apply button: CLICK IT\n\n"

            "Step 5 — FILL THE APPLICATION FORM\n"
            "  A dialog/modal will appear with one or more steps.\n"
            "  For each step:\n"
            "  • Fill every visible required field using the resume information above\n"
            "  • Phone number: use the phone from the resume\n"
            "  • Resume upload: skip / dismiss — the resume is already on the LinkedIn profile\n"
            "  • Years of experience: read from the resume experience section\n"
            "  • Cover letter text box: paste 2 sentences from the cover letter above\n"
            "  • Screening questions: answer from the Q&A list above; if not listed, answer reasonably\n"
            "  • After filling the current step: click 'Next', 'Continue', or 'Review'\n"
            "  • If a required field rejects your input, try a different format and retry\n"
            "  • If the EXACT same action fails twice in a row with no progress: "
            "    call done(\"STUCK_DETECTED\")\n\n"

            "Step 6 — SUBMIT\n"
            "  On the final review step, click 'Submit application'\n"
            "  After the confirmation screen appears: call done(\"APPLICATION_SUBMITTED\")\n\n"

            "=== REQUIRED EXIT CODES ===\n"
            "You MUST end by calling done() with EXACTLY one of these strings:\n"
            "  done(\"APPLICATION_SUBMITTED\")  — application submitted successfully\n"
            "  done(\"CAPTCHA_DETECTED\")        — CAPTCHA / bot check appeared\n"
            "  done(\"NO_EASY_APPLY\")           — no Easy Apply button on this job\n"
            "  done(\"ALREADY_APPLIED\")         — already applied to this job\n"
            "  done(\"STUCK_DETECTED\")          — repeated failure, cannot proceed\n"
            "  done(\"FAILED: <reason>\")        — unrecoverable error with reason\n\n"

            "CRITICAL RULES:\n"
            "• NEVER stop without calling done()\n"
            "• NEVER navigate away from the job or application flow once Easy Apply is open\n"
            "• NEVER click Easy Apply more than once\n"
            "• If the confirmation / success screen is visible: that means done(\"APPLICATION_SUBMITTED\")\n"
        )

        log("Building browser config...")

        storage_state = None
        if session_cookies and isinstance(session_cookies, list) and session_cookies:
            storage_state = {"cookies": session_cookies, "origins": []}
            log("Using saved LinkedIn session cookies")

        browser_profile = BrowserConfig(
            headless=headless,
            slow_mo=slow_mo,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
            chromium_sandbox=False,
            storage_state=storage_state,
            user_data_dir=None,
        )

        log(f"Starting browser-use agent (max_steps={max_steps}, headless={headless})...")

        # Mark LLM as pre-verified so browser-use skips _detect_best_tool_calling_method().
        # That method calls asyncio.run() internally which fails inside a running event loop.
        llm._verified_api_keys = True

        log("Constructing Agent (tool_calling=function_calling, memory=off)...")
        agent = Agent(
            task=task,
            llm=llm,
            use_vision=False,
            enable_memory=False,
            tool_calling_method="function_calling",
            browser_profile=browser_profile,
        )
        log("Agent constructed. Calling agent.run()...")

        history = await agent.run(max_steps=max_steps)
        log("agent.run() returned.")

        is_done, is_successful, final_str = await _diagnose(history, agent, log)

        if "CAPTCHA_DETECTED" in final_str:
            return {"status": "captcha", "message": "CAPTCHA detected. Manual intervention required."}
        elif "APPLICATION_SUBMITTED" in final_str:
            return {"status": "success", "message": "Application submitted successfully."}
        elif "NO_EASY_APPLY" in final_str:
            return {"status": "no_easy_apply", "message": "No Easy Apply button found for this job."}
        elif "ALREADY_APPLIED" in final_str:
            return {"status": "already_applied", "message": "Already applied to this job."}
        elif "STUCK_DETECTED" in final_str:
            return {"status": "failed", "message": "Agent stuck — same step failed repeatedly."}
        elif "FAILED:" in final_str:
            return {"status": "failed", "message": final_str[:300]}
        elif is_done and is_successful:
            return {"status": "success", "message": "Agent completed task (inferred from is_done+is_successful)."}
        elif is_done:
            return {"status": "uncertain", "message": f"Agent called done() but exit code unclear: {final_str[:200]}"}
        else:
            return {"status": "uncertain", "message": "Agent exited without calling done(). Check screenshot and diagnostics above."}

    except Exception as exc:
        tb = traceback.format_exc()
        log(f"Worker exception: {type(exc).__name__}: {exc}")
        log(f"Traceback:\n{tb[-2000:]}")
        return {"status": "error", "message": str(exc), "tb": tb[-2000:]}


def main():
    raw = sys.stdin.read()
    config = json.loads(raw)
    result = asyncio.run(run_apply(config))
    emit("result", **result)


if __name__ == "__main__":
    main()
