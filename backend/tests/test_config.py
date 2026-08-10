# Config loading, with env_file=None throughout so a developer's own .env can
# never make a "missing key" test pass.

import pytest
from pydantic import ValidationError

from app.config import (
    DEFAULT_ALPACA_PAPER_BASE_URL,
    DEFAULT_PNL_BASELINE,
    Config,
    MissingConfigError,
    load_config,
)

REQUIRED = {
    "ALPACA_API_KEY_ID": "paper-key-id",
    "ALPACA_API_SECRET_KEY": "paper-secret",
    "FINNHUB_API_KEY": "finnhub-key",
    "FRED_API_KEY": "fred-key",
}

OPTIONAL = ("ALPACA_PAPER_BASE_URL", "PNL_BASELINE")


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    """A clean environment holding exactly the required keys."""
    for name in (*REQUIRED, *OPTIONAL):
        monkeypatch.delenv(name, raising=False)
    for name, value in REQUIRED.items():
        monkeypatch.setenv(name, value)
    return monkeypatch


def test_loads_every_required_key(env: pytest.MonkeyPatch):
    config = load_config(env_file=None)

    assert config.alpaca_api_key_id == "paper-key-id"
    assert config.alpaca_api_secret_key == "paper-secret"
    assert config.finnhub_api_key == "finnhub-key"
    assert config.fred_api_key == "fred-key"


def test_optional_keys_fall_back_to_defaults(env: pytest.MonkeyPatch):
    config = load_config(env_file=None)

    assert config.alpaca_paper_base_url == DEFAULT_ALPACA_PAPER_BASE_URL
    assert config.pnl_baseline == DEFAULT_PNL_BASELINE


def test_optional_keys_are_overridable(env: pytest.MonkeyPatch):
    env.setenv("ALPACA_PAPER_BASE_URL", "http://127.0.0.1:9000")
    env.setenv("PNL_BASELINE", "96400")

    config = load_config(env_file=None)

    assert config.alpaca_paper_base_url == "http://127.0.0.1:9000"
    assert config.pnl_baseline == 96_400.0


@pytest.mark.parametrize("missing", sorted(REQUIRED))
def test_a_missing_key_is_named_in_the_error(env: pytest.MonkeyPatch, missing: str):
    env.delenv(missing)

    with pytest.raises(MissingConfigError, match=missing):
        load_config(env_file=None)


def test_every_missing_key_is_named_at_once(env: pytest.MonkeyPatch):
    # Fail on the whole list, not the first one — otherwise setting up a new
    # machine is four runs and four error messages.
    env.delenv("FINNHUB_API_KEY")
    env.delenv("FRED_API_KEY")

    with pytest.raises(MissingConfigError) as caught:
        load_config(env_file=None)

    assert "FINNHUB_API_KEY" in str(caught.value)
    assert "FRED_API_KEY" in str(caught.value)


def test_the_error_points_at_where_to_put_the_keys(env: pytest.MonkeyPatch):
    env.delenv("FRED_API_KEY")

    with pytest.raises(MissingConfigError, match=r"\.env\.example"):
        load_config(env_file=None)


def test_the_live_trading_host_is_refused(env: pytest.MonkeyPatch):
    # Hard rule: paper endpoints only.
    env.setenv("ALPACA_PAPER_BASE_URL", "https://api.alpaca.markets")

    with pytest.raises(ValueError, match="paper-only"):
        load_config(env_file=None)


def test_the_paper_host_is_not_mistaken_for_the_live_one(env: pytest.MonkeyPatch):
    # paper-api.alpaca.markets ends with api.alpaca.markets, so a substring
    # check would reject the correct host.
    env.setenv("ALPACA_PAPER_BASE_URL", "https://paper-api.alpaca.markets")

    assert load_config(env_file=None).alpaca_paper_base_url == (
        "https://paper-api.alpaca.markets"
    )


def test_a_non_numeric_baseline_is_not_swallowed(env: pytest.MonkeyPatch):
    # Not a missing key, so it surfaces as a plain validation error rather
    # than being reported as absent.
    env.setenv("PNL_BASELINE", "not-a-number")

    with pytest.raises(ValidationError, match="pnl_baseline"):
        load_config(env_file=None)


def test_config_is_frozen(env: pytest.MonkeyPatch):
    config = load_config(env_file=None)

    with pytest.raises(ValidationError, match="frozen"):
        config.fred_api_key = "swapped-at-runtime"


def test_env_vars_win_over_the_env_file(tmp_path, env: pytest.MonkeyPatch):
    # The documented `set -a; source ../.env` path must not be overridden by a
    # stale file on disk.
    env_file = tmp_path / ".env"
    env_file.write_text("FRED_API_KEY=from-the-file\n", encoding="utf-8")

    assert load_config(env_file=env_file).fred_api_key == "fred-key"


def test_the_env_file_supplies_keys_absent_from_the_environment(
    tmp_path, env: pytest.MonkeyPatch
):
    # A cron or Task Scheduler entry point sets nothing; the file alone is
    # enough.
    env.delenv("FRED_API_KEY")
    env_file = tmp_path / ".env"
    env_file.write_text("FRED_API_KEY=from-the-file\n", encoding="utf-8")

    assert load_config(env_file=env_file).fred_api_key == "from-the-file"


def test_a_missing_env_file_is_not_an_error(env: pytest.MonkeyPatch, tmp_path):
    # A fresh clone whose .env has not been created yet still reaches the
    # named-keys error rather than an unhandled file error.
    assert load_config(env_file=tmp_path / "does-not-exist").fred_api_key == "fred-key"


def test_unrelated_environment_variables_are_ignored(env: pytest.MonkeyPatch):
    env.setenv("SOME_OTHER_TOOL_TOKEN", "irrelevant")

    assert isinstance(load_config(env_file=None), Config)
