"""Central configuration — loads .env and exposes a global `settings` object."""

from pathlib import Path
from datetime import timezone

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# Load .env from project root
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV_PATH)


class Settings(BaseSettings):
    """Application settings — populated from environment variables."""

    # ── API Keys ────────────────────────────────────────
    OPENROUTER_API_KEY: str = Field(default="", description="OpenRouter API key")
    OPENROUTER_MODEL: str = Field(
        default="meta-llama/llama-3.3-70b-instruct:free",
        description="Default LLM model on OpenRouter",
    )
    APIFY_API_TOKEN: str = Field(default="", description="Apify API token")

    # ── RAG ─────────────────────────────────────────────
    RAG_MODE: str = Field(
        default="simple",
        description='"simple" (JSON keyword) or "advanced" (ChromaDB)',
    )

    # ── Paths (derived, not from env) ───────────────────
    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = PROJECT_ROOT / "data"
    DB_PATH: Path = DATA_DIR / "predictions.db"
    MEMORY_DIR: Path = PROJECT_ROOT / "memory" / "store"
    SKILLS_DIR: Path = PROJECT_ROOT / "memory" / "store" / "skills"

    # ── Constants ───────────────────────────────────────
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    TIMEZONE: timezone = timezone.utc

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "arbitrary_types_allowed": True,
    }

    def validate_keys(self) -> list[str]:
        """Check which API keys are configured. Returns list of warnings."""
        warnings = []
        if not self.OPENROUTER_API_KEY:
            warnings.append("⚠️  OPENROUTER_API_KEY not set — LLM calls will fail")
        if not self.APIFY_API_TOKEN:
            warnings.append("⚠️  APIFY_API_TOKEN not set — Apify scraping will be skipped")
        return warnings


# Global singleton — import this everywhere
settings = Settings()
