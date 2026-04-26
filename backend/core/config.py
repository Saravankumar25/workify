"""Application settings loaded from environment + backend/.env.

Hardened against:
- malformed .env (extra keys, quoted JSON, trailing whitespace)
- missing required vars (fails at startup with explicit error, never at request time)
- Render vs local path differences (.env is resolved relative to this file)
- impossible concurrency / timeout values that would OOM Render Starter or
  allow unbounded browser-use runs.
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# backend/ is one level above core/.
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ENV_FILE = _BACKEND_DIR / ".env"

# Render Starter has 512 MB RAM. Each headless Chromium instance costs
# ~250-400 MB. More than 2 concurrent apply runs will OOM-kill the worker.
# Hard ceiling below is enforced regardless of env override.
_RENDER_SAFE_APPLY_CEILING = 2
_APPLY_HARD_CEILING = 8  # never allow more than this even if env requests it


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # never crash on unknown keys in .env
    )

    # --- FastAPI ---
    API_HOST: str = "0.0.0.0"
    # Dev default matches frontend's VITE_API_URL (http://localhost:8000).
    # Render overrides with its own PORT → uvicorn --port $PORT.
    API_PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:5174"

    # --- MongoDB ---
    MONGODB_URL: str = Field(..., min_length=10)
    MONGODB_DB_NAME: str = "workify"

    # --- Firebase ---
    # Single-line service-account JSON (both Render env + local .env).
    FIREBASE_CREDENTIALS_JSON: str = Field(..., min_length=10)

    # --- Groq ---
    # Legacy single key — kept for backward compat. Prefer GROQ_API_KEYS pool.
    # Do NOT mark required (Field(...)) so deployments using only GROQ_API_KEYS work.
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_MODEL_FALLBACK: str = "llama-3.1-8b-instant"
    # llama-3.1-8b-instant has 30k TPM on Groq free tier vs 12k for the 70b model.
    # Browser-use sends the full task prompt on every step (~5k tokens each), so the
    # 70b model exhausts the free-tier budget after 2 steps.  The 8b model completes
    # a full apply run within the free-tier window.
    GROQ_MODEL_APPLY: str = "llama-3.1-8b-instant"

    # --- LLM key pools (comma-separated) ---
    GROQ_API_KEYS: str = ""     # preferred over GROQ_API_KEY; rotated round-robin
    GEMINI_API_KEYS: str = ""
    MISTRAL_API_KEYS: str = ""

    # --- Per-task model selections ---
    GROQ_MODEL_RESUME: str = "llama-3.3-70b-versatile"
    GROQ_MODEL_COVER_LETTER: str = "llama-3.3-70b-versatile"
    GROQ_MODEL_QA: str = "llama-3.3-70b-versatile"
    GROQ_MODEL_PDF_PARSE: str = "llama-3.3-70b-versatile"
    GEMINI_MODEL_AGENT: str = "gemini-2.0-flash"
    MISTRAL_MODEL_QA: str = "mistral-large-latest"
    MISTRAL_MODEL_PDF: str = "mistral-large-latest"

    # --- Cloudinary ---
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    # --- Encryption ---
    FERNET_KEY: str = Field(..., min_length=32)

    # --- Browser-use / Playwright ---
    PLAYWRIGHT_HEADLESS: bool = True
    PLAYWRIGHT_SLOWMO_MS: int = 40
    BROWSER_USE_MAX_STEPS: int = 75

    # --- Concurrency & limits ---
    # Default of 2 targets Render Starter (512MB). Bump to 6-8 on a paid plan.
    MAX_CONCURRENT_APPLY_RUNS: int = 2
    RATE_LIMIT_APPLIES_PER_DAY_DEFAULT: int = 20
    RATE_LIMIT_APPLIES_PER_DAY_MAX: int = 50

    # --- Hard timeouts (seconds) — enforced with asyncio.wait_for ---
    APPLY_RUN_TIMEOUT_SECONDS: int = 420          # 7 min total per apply run
    LINKEDIN_LOGIN_TIMEOUT_SECONDS: int = 90
    BROWSER_PHASE_TIMEOUT_SECONDS: int = 180      # per major browser phase
    PDF_UPLOAD_TIMEOUT_SECONDS: int = 45
    PDF_RENDER_TIMEOUT_SECONDS: int = 30
    GROQ_REQUEST_TIMEOUT_SECONDS: int = 60

    # --- Circuit breaker (per-user LinkedIn failures) ---
    LINKEDIN_FAILURE_THRESHOLD: int = 5           # consecutive failures
    LINKEDIN_FAILURE_WINDOW_SECONDS: int = 1800   # 30 min rolling window
    LINKEDIN_CIRCUIT_COOLDOWN_SECONDS: int = 3600 # 1 h block after trip

    # --- Per-user artifact (Cloudinary PDF) daily cap ---
    ARTIFACT_EXPORTS_PER_DAY_DEFAULT: int = 40

    # --- Admin ---
    ADMIN_EMAIL: str = ""

    # ---------- validators ----------

    @field_validator("FIREBASE_CREDENTIALS_JSON")
    @classmethod
    def _validate_firebase_json(cls, v: str) -> str:
        v = v.strip()
        # Render's UI sometimes wraps pasted values in single/double quotes.
        if (v.startswith("'") and v.endswith("'")) or (
            v.startswith('"') and v.endswith('"') and v.count('"') == 2
        ):
            v = v[1:-1]
        try:
            data = json.loads(v)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"FIREBASE_CREDENTIALS_JSON is not valid JSON: {exc}. "
                "Paste the full service-account JSON as a single line."
            ) from exc
        required = {"type", "project_id", "private_key", "client_email"}
        missing = required - set(data)
        if missing:
            raise ValueError(
                f"FIREBASE_CREDENTIALS_JSON missing required keys: {sorted(missing)}"
            )
        return v

    @field_validator("FERNET_KEY")
    @classmethod
    def _validate_fernet(cls, v: str) -> str:
        from cryptography.fernet import Fernet

        try:
            Fernet(v.encode())
        except Exception as exc:
            raise ValueError(
                f"FERNET_KEY is not a valid Fernet key ({exc}). "
                "Regenerate with: python -c \"from cryptography.fernet "
                "import Fernet; print(Fernet.generate_key().decode())\""
            ) from exc
        return v

    @field_validator("CORS_ORIGINS")
    @classmethod
    def _strip_cors(cls, v: str) -> str:
        return ",".join(o.strip() for o in v.split(",") if o.strip())

    @field_validator("MAX_CONCURRENT_APPLY_RUNS")
    @classmethod
    def _clamp_apply_concurrency(cls, v: int) -> int:
        if v < 1:
            raise ValueError(
                "MAX_CONCURRENT_APPLY_RUNS must be >= 1 "
                "(semaphore cannot be zero)."
            )
        if v > _APPLY_HARD_CEILING:
            raise ValueError(
                f"MAX_CONCURRENT_APPLY_RUNS={v} exceeds hard ceiling "
                f"{_APPLY_HARD_CEILING}. Each Chromium instance uses "
                "~250-400 MB; Render Starter (512 MB) will OOM."
            )
        return v

    @field_validator("BROWSER_USE_MAX_STEPS")
    @classmethod
    def _validate_max_steps(cls, v: int) -> int:
        if v < 5:
            raise ValueError("BROWSER_USE_MAX_STEPS must be >= 5")
        if v > 150:
            raise ValueError(
                "BROWSER_USE_MAX_STEPS > 150 is a cost/runaway risk; "
                "apply flows should never need this many steps."
            )
        return v

    @field_validator(
        "APPLY_RUN_TIMEOUT_SECONDS",
        "LINKEDIN_LOGIN_TIMEOUT_SECONDS",
        "BROWSER_PHASE_TIMEOUT_SECONDS",
        "PDF_UPLOAD_TIMEOUT_SECONDS",
        "PDF_RENDER_TIMEOUT_SECONDS",
        "GROQ_REQUEST_TIMEOUT_SECONDS",
    )
    @classmethod
    def _validate_positive_timeout(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Timeout values must be > 0")
        if v > 1800:
            raise ValueError(
                "Timeout > 30 min is a request-hang risk; cap lower."
            )
        return v

    # ---------- key pool properties ----------

    @property
    def groq_keys_list(self) -> list[str]:
        """All configured Groq keys. Falls back to GROQ_API_KEY if pool is empty."""
        if self.GROQ_API_KEYS.strip():
            return [k.strip() for k in self.GROQ_API_KEYS.split(",") if k.strip()]
        if self.GROQ_API_KEY.strip():
            return [self.GROQ_API_KEY.strip()]
        return []

    @property
    def gemini_keys_list(self) -> list[str]:
        return [k.strip() for k in self.GEMINI_API_KEYS.split(",") if k.strip()]

    @property
    def mistral_keys_list(self) -> list[str]:
        return [k.strip() for k in self.MISTRAL_API_KEYS.split(",") if k.strip()]

    # ---------- cross-field validators ----------

    @model_validator(mode="after")
    def _check_groq_key_available(self) -> "Settings":
        if not self.groq_keys_list:
            raise ValueError(
                "No Groq API keys configured. Set GROQ_API_KEYS (comma-separated pool) "
                "or GROQ_API_KEY (single legacy key)."
            )
        return self

    def firebase_credentials(self) -> dict[str, Any]:
        return json.loads(self.FIREBASE_CREDENTIALS_JSON)

    def cors_origins_list(self) -> list[str]:
        return [o for o in self.CORS_ORIGINS.split(",") if o]


def _load() -> Settings:
    try:
        return Settings()  # type: ignore[call-arg]
    except Exception as exc:
        print(
            f"FATAL: failed to load Workify settings — {exc}",
            file=sys.stderr,
            flush=True,
        )
        raise


settings = _load()


def validate_runtime_environment() -> None:
    """Called from the FastAPI lifespan. Emits warnings for production-risky
    configurations that are valid but sub-optimal for Render Starter."""
    if settings.MAX_CONCURRENT_APPLY_RUNS > _RENDER_SAFE_APPLY_CEILING:
        logger.warning(
            "MAX_CONCURRENT_APPLY_RUNS=%d exceeds Render Starter safe "
            "ceiling of %d — OOM risk from parallel Chromium instances. "
            "Reduce unless you are on a plan with >= 1 GB RAM.",
            settings.MAX_CONCURRENT_APPLY_RUNS,
            _RENDER_SAFE_APPLY_CEILING,
        )

    total_timeout = settings.APPLY_RUN_TIMEOUT_SECONDS
    if total_timeout < settings.BROWSER_PHASE_TIMEOUT_SECONDS:
        raise RuntimeError(
            f"APPLY_RUN_TIMEOUT_SECONDS ({total_timeout}) must be >= "
            f"BROWSER_PHASE_TIMEOUT_SECONDS "
            f"({settings.BROWSER_PHASE_TIMEOUT_SECONDS}); otherwise phases "
            "get cancelled before they run."
        )

    if (
        settings.RATE_LIMIT_APPLIES_PER_DAY_DEFAULT
        > settings.RATE_LIMIT_APPLIES_PER_DAY_MAX
    ):
        raise RuntimeError(
            "RATE_LIMIT_APPLIES_PER_DAY_DEFAULT must be <= "
            "RATE_LIMIT_APPLIES_PER_DAY_MAX."
        )

    if not (
        settings.CLOUDINARY_CLOUD_NAME
        and settings.CLOUDINARY_API_KEY
        and settings.CLOUDINARY_API_SECRET
    ):
        logger.warning(
            "Cloudinary is not fully configured — PDF export will fail at "
            "request time. Set CLOUDINARY_* env vars."
        )

    logger.info(
        "Runtime config OK: apply_concurrency=%d apply_timeout=%ds "
        "max_steps=%d",
        settings.MAX_CONCURRENT_APPLY_RUNS,
        settings.APPLY_RUN_TIMEOUT_SECONDS,
        settings.BROWSER_USE_MAX_STEPS,
    )
