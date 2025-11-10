"""Load project environment and expose a unified config object."""

from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv as _load_dotenv  # type: ignore
except ImportError:
    _load_dotenv = None

REPO_ROOT = Path(__file__).resolve().parents[3]


def load_env() -> None:
    """Load .env from repo root without overwriting existing environment vars."""
    dotenv_path = REPO_ROOT / ".env"
    if not dotenv_path.exists():
        return

    if _load_dotenv:
        _load_dotenv(dotenv_path=dotenv_path, override=False)
        return

    for line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass
class AppCfg:
    """Central configuration object for Reddit and LLM clients."""
    reddit_client_id: str | None = None
    reddit_client_secret: str | None = None
    reddit_user_agent: str | None = None
    reddit_username: str | None = None
    reddit_password: str | None = None
    openai_api_key: str | None = None

    def model_dump(self) -> dict:
        return self.__dict__.copy()


def get_config() -> AppCfg:
    """Return AppCfg built from environment variables."""
    load_env()
    return AppCfg(
        reddit_client_id=os.getenv("REDDIT_CLIENT_ID"),
        reddit_client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        reddit_user_agent=os.getenv("REDDIT_USER_AGENT"),
        reddit_username=os.getenv("REDDIT_USERNAME"),
        reddit_password=os.getenv("REDDIT_PASSWORD"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )


def require_reddit_creds(cfg: AppCfg | None = None) -> None:
    """Raise if required Reddit credentials are missing."""
    cfg = cfg or get_config()
    missing = [
        key for key, val in {
            "REDDIT_CLIENT_ID": cfg.reddit_client_id,
            "REDDIT_CLIENT_SECRET": cfg.reddit_client_secret,
            "REDDIT_USER_AGENT": cfg.reddit_user_agent,
        }.items() if not val
    ]
    if missing:
        raise RuntimeError(f"Missing Reddit credentials: {', '.join(missing)}")