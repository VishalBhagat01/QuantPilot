"""Centralized configuration and runtime environment manager for QuantPilot."""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Filesystem Paths
# ---------------------------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent

DATA_DIR = BACKEND_DIR / "data"
TEMP_DIR = DATA_DIR / "temp"
CACHE_DIR = DATA_DIR / "cache"
LOGS_DIR = DATA_DIR / "logs"

# Load backend .env with fallback to root .env
_backend_env = BACKEND_DIR / ".env"
_root_env = PROJECT_ROOT / ".env"

if _backend_env.exists():
    load_dotenv(_backend_env)
elif _root_env.exists():
    load_dotenv(_root_env)


def init_runtime_directories():
    """Ensure all runtime directories exist with proper separation."""
    for directory in (DATA_DIR, TEMP_DIR, CACHE_DIR, LOGS_DIR):
        directory.mkdir(parents=True, exist_ok=True)


# Initialize runtime directories on module import
init_runtime_directories()


# ---------------------------------------------------------------------------
# Application Settings
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Settings:
    """Immutable application settings populated from environment variables."""

    # Project Directories
    project_root: Path = PROJECT_ROOT
    backend_dir: Path = BACKEND_DIR
    data_dir: Path = DATA_DIR
    temp_dir: Path = TEMP_DIR
    cache_dir: Path = CACHE_DIR
    logs_dir: Path = LOGS_DIR

    # Database
    database_url: str = field(
        default_factory=lambda: os.getenv("DATABASE_URL", "").strip()
    )

    # LLM Configuration
    llm_provider: str = field(
        default_factory=lambda: os.getenv("LLM_PROVIDER", "google").strip().lower()
    )
    llm_model_name: str = field(
        default_factory=lambda: os.getenv("LLM_MODEL_NAME", "gemini-flash-latest").strip()
    )

    # LLM API Keys
    google_api_key: str = field(
        default_factory=lambda: os.getenv("GOOGLE_API_KEY", "").strip()
    )
    groq_api_key: str = field(
        default_factory=lambda: os.getenv("GROQ_API_KEY", "").strip()
    )
    huggingfacehub_api_token: str = field(
        default_factory=lambda: os.getenv("HUGGINGFACEHUB_API_TOKEN", "").strip()
    )

    # Market Data API Keys
    finnhub_api_key: str = field(
        default_factory=lambda: os.getenv("FINNHUB_API_KEY", "").strip()
    )
    alphavantage_api_key: str = field(
        default_factory=lambda: os.getenv("ALPHAADVANTAGE_API_KEY", "").strip()
    )

    # Alpaca Trading Keys
    alpaca_api_key: str = field(
        default_factory=lambda: os.getenv("ALPACA_API_KEY", "").strip()
    )
    alpaca_secret_key: str = field(
        default_factory=lambda: os.getenv("ALPACA_SECRET_KEY", "").strip()
    )
    alpaca_paper: bool = field(
        default_factory=lambda: os.getenv("ALPACA_PAPER", "true").lower() == "true"
    )

    # Trading Safety Limits
    max_shares_per_order: int = 100
    max_order_value_usd: int = 10_000

    # HTTP Network Timeout (seconds)
    http_timeout: float = 6.0

    # CORS Allowed Origins
    cors_origins: List[str] = field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "*",
        ]
    )


settings = Settings()
