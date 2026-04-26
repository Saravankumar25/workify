"""
Smoke-test / diagnostic runner for apply_worker.py.

Credentials are read from MongoDB (the `profiles` collection) — the same
source apply_service.py uses in production. No .env credentials, no placeholders.

Before running, go to Profile → Profile Form in the app, enter your
LinkedIn email and password, and click Save Profile.

Run from the repo root:
    python backend/workers/test_worker.py [--user-id <mongo_user_id>]

If --user-id is omitted, the first profile with saved credentials is used.
Change JOB_URL below to a specific Easy Apply job to test end-to-end.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


JOB_URL = "https://www.linkedin.com/jobs/"


def _read_env_key(key: str) -> str:
    """Read a single key from backend/.env (infrastructure config only)."""
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith(f"{key}=") and not line.startswith("#"):
                return line.split("=", 1)[1].strip()
    return os.environ.get(key, "")


def _fetch_profile_from_mongo(user_id: str | None) -> dict:
    """Connect to MongoDB and return a profile document that has saved credentials."""
    try:
        import pymongo
    except ImportError:
        print("ERROR: pymongo not installed. Run: pip install pymongo")
        sys.exit(1)

    mongodb_url = _read_env_key("MONGODB_URL")
    if not mongodb_url:
        print("ERROR: MONGODB_URL not found in backend/.env")
        sys.exit(1)

    db_name = _read_env_key("MONGODB_DB_NAME") or "workify"

    client = pymongo.MongoClient(mongodb_url, serverSelectionTimeoutMS=5000)
    db = client[db_name]

    # $type "string" ensures we only match documents where the field actually
    # exists and is a non-empty string. This excludes old profile documents that
    # were created before these fields existed (where the field is absent/null).
    query: dict = {
        "linkedin_email": {"$type": "string", "$ne": ""},
        "linkedin_password": {"$type": "string", "$ne": ""},
    }
    if user_id:
        query["user_id"] = user_id

    profile = db["profiles"].find_one(query, sort=[("updated_at", pymongo.DESCENDING)])
    client.close()

    if not profile:
        hint = f" for user_id={user_id}" if user_id else ""
        print(
            f"ERROR: No profile{hint} with saved LinkedIn credentials found in MongoDB.\n"
            "  → Open the app, go to Profile → Profile Form, enter your LinkedIn\n"
            "    email and password, then click Save Profile."
        )
        sys.exit(1)

    li_email = profile.get("linkedin_email", "")
    li_password = profile.get("linkedin_password", "")
    if not li_email or not li_password:
        print("ERROR: Profile document found but credentials are empty after fetch.")
        sys.exit(1)

    return profile


def main():
    parser = argparse.ArgumentParser(description="Test apply_worker.py against a real LinkedIn job.")
    parser.add_argument("--user-id", help="MongoDB user_id to fetch profile for (omit to use first with credentials)")
    parser.add_argument("--job-url", default=JOB_URL, help="LinkedIn job URL to apply to")
    parser.add_argument("--headless", action="store_true", help="Run browser headless")
    args = parser.parse_args()

    groq_api_key = _read_env_key("GROQ_API_KEY")
    if not groq_api_key:
        print("ERROR: GROQ_API_KEY not found in backend/.env")
        sys.exit(1)

    print("Fetching profile credentials from MongoDB...")
    profile = _fetch_profile_from_mongo(args.user_id)

    li_email = profile.get("linkedin_email", "")
    li_password = profile.get("linkedin_password", "")
    user_id = profile.get("user_id", "unknown")
    print(f"Using profile for user_id={user_id}, linkedin_email={li_email}")

    # Build a resume string from the saved profile fields (same data apply_service uses).
    resume_parts = []
    if profile.get("full_name"):
        resume_parts.append(profile["full_name"])
    contact = " | ".join(filter(None, [
        profile.get("email", ""),
        profile.get("phone", ""),
        profile.get("location", ""),
    ]))
    if contact:
        resume_parts.append(contact)
    if profile.get("summary"):
        resume_parts.append(f"\nSUMMARY:\n{profile['summary']}")
    if profile.get("skills"):
        skills = profile["skills"] if isinstance(profile["skills"], list) else []
        if skills:
            resume_parts.append(f"\nSKILLS: {', '.join(skills)}")
    try:
        exp = json.loads(profile.get("experience_json") or "[]")
        if exp:
            resume_parts.append("\nEXPERIENCE:")
            for e in exp:
                resume_parts.append(
                    f"  {e.get('title','')} — {e.get('company','')} "
                    f"({e.get('start','')}–{e.get('end','')})"
                )
    except Exception:
        pass
    try:
        edu = json.loads(profile.get("education_json") or "[]")
        if edu:
            resume_parts.append("\nEDUCATION:")
            for e in edu:
                resume_parts.append(
                    f"  {e.get('degree','')} — {e.get('institution','')} ({e.get('year','')})"
                )
    except Exception:
        pass

    resume_md = "\n".join(resume_parts) or "Resume not yet filled in."

    config = {
        "job_url": args.job_url,
        "resume_md": resume_md,
        "cover_letter_md": "",
        "qa_pairs": [],
        "linkedin_email": li_email,
        "linkedin_password": li_password,
        "session_cookies": None,
        "groq_api_key": groq_api_key,
        # llama-3.1-8b-instant: 30k TPM on Groq free tier.
        # Never fall back to GROQ_MODEL (llama-3.3-70b-versatile = 12k TPM —
        # exhausted after 2 browser-use steps, kills the browser mid-login).
        "groq_model": _read_env_key("GROQ_MODEL_APPLY") or "llama-3.1-8b-instant",
        "max_steps": 75,
        "headless": args.headless,
        "slowmo_ms": 0 if args.headless else 500,
    }

    worker = str(Path(__file__).parent / "apply_worker.py")

    print(f"Spawning worker: {worker}")
    print(f"Job URL: {config['job_url']}")
    print(f"Headless: {config['headless']}  |  max_steps: {config['max_steps']}")
    print("-" * 60)

    proc = subprocess.run(
        [sys.executable, worker],
        input=json.dumps(config),
        capture_output=True,
        text=True,
        timeout=600,
    )

    print("STDOUT (JSON event lines):")
    for line in proc.stdout.splitlines():
        try:
            event = json.loads(line)
            kind = event.get("event", "?")
            if kind == "log":
                print(f"  [log] {event.get('message', '')}")
            elif kind == "result":
                print(f"  [RESULT] status={event.get('status')} | {event.get('message', '')}")
                if event.get("tb"):
                    print("  TRACEBACK:")
                    print(event["tb"])
            elif kind == "screenshot_path":
                print(f"  [screenshot] → {event.get('path')}")
            else:
                print(f"  [{kind}] {event}")
        except json.JSONDecodeError:
            print(f"  RAW: {line}")

    print("\nSTDERR (first 3000 chars):")
    print(proc.stderr[:3000] or "(empty)")
    print(f"\nReturn code: {proc.returncode}")


if __name__ == "__main__":
    main()
