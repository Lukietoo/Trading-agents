# All credentials and tunables in one place, loaded from the repo-root .env.
#
# Unlike the wire models, this is internal — it never crosses the API boundary,
# so fields are snake_case and map case-insensitively onto the env var names.
#
# Real environment variables take precedence over the .env file, so the
# documented `set -a; source ../.env; set +a` still works, and so does a cron
# or Task Scheduler entry point that sets nothing at all: the file is read
# directly. Nothing here assumes a host, OS, or absolute path.

from pathlib import Path
from urllib.parse import urlparse

from pydantic import ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# app/config.py -> backend/ -> repo root. Resolved from __file__ so it works
# from any working directory and on either OS.
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

# Until the reset-epoch ticket lands, total P&L is measured from the paper
# account's starting balance.
DEFAULT_PNL_BASELINE = 100_000.0
DEFAULT_ALPACA_PAPER_BASE_URL = "https://paper-api.alpaca.markets"

# Hard rule: paper endpoints only. This is the live trading host.
LIVE_ALPACA_HOST = "api.alpaca.markets"


class MissingConfigError(RuntimeError):
    """Raised at startup when a required key is absent, naming every one that
    is missing rather than failing on the first."""


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    alpaca_api_key_id: str
    alpaca_api_secret_key: str
    finnhub_api_key: str
    fred_api_key: str

    alpaca_paper_base_url: str = DEFAULT_ALPACA_PAPER_BASE_URL
    pnl_baseline: float = DEFAULT_PNL_BASELINE

    @field_validator("alpaca_paper_base_url")
    @classmethod
    def _refuse_the_live_trading_host(cls, value: str) -> str:
        # Compared on the parsed hostname, not as a substring: the paper host
        # paper-api.alpaca.markets *ends with* the live one.
        if urlparse(value).hostname == LIVE_ALPACA_HOST:
            raise ValueError(
                f"{LIVE_ALPACA_HOST} is the live trading host and places real "
                "orders. This project is paper-only — use "
                f"{DEFAULT_ALPACA_PAPER_BASE_URL}."
            )
        return value


def load_config(env_file: Path | None = ENV_FILE) -> Config:
    """Build the config, or fail loudly naming what is missing.

    `env_file=None` reads the environment only, which is how the tests get a
    deterministic result regardless of the developer's own .env.
    """
    try:
        return Config(_env_file=env_file)
    except ValidationError as exc:
        missing = [
            str(error["loc"][0]).upper()
            for error in exc.errors()
            if error["type"] == "missing"
        ]
        if not missing:
            raise
        raise MissingConfigError(
            f"Missing required config: {', '.join(sorted(missing))}. "
            f"Add them to {env_file or '.env'} — see .env.example for the "
            "full list and where each key comes from."
        ) from exc
