"""Tests for loading and validating settings."""

import pytest

from trader.config import build_settings, load_settings, parse_watchlist
from trader.errors import ConfigError, SafetyError

GOOD_ENV = {
    "PAPER_TRADING": "TRUE",
    "ALPACA_BASE_URL": "https://paper-api.alpaca.markets",
}
GOOD_FILE = {"watchlist": ["AAPL", "TSLA", "NVDA"], "logging": {"level": "INFO"}}


def test_valid_settings_build():
    settings = build_settings(GOOD_ENV, GOOD_FILE)
    assert settings.paper_trading is True
    assert settings.watchlist == ("AAPL", "TSLA", "NVDA")
    assert settings.has_api_keys is False


def test_safety_is_checked_before_anything_else():
    with pytest.raises(SafetyError):
        build_settings({**GOOD_ENV, "PAPER_TRADING": "FALSE"}, GOOD_FILE)


def test_watchlist_is_cleaned_and_deduplicated():
    assert parse_watchlist([" aapl", "AAPL", "brk.b"]) == ("AAPL", "BRK.B")


@pytest.mark.parametrize("bad", [None, [], "AAPL", ["AAPL", "NOT A TICKER"], ["TOOLONG"]])
def test_bad_watchlists_are_rejected(bad):
    with pytest.raises(ConfigError):
        parse_watchlist(bad)


def test_bad_log_level_is_rejected():
    with pytest.raises(ConfigError):
        build_settings(GOOD_ENV, {**GOOD_FILE, "logging": {"level": "LOUD"}})


def test_missing_env_file_is_a_config_error(tmp_path):
    with pytest.raises(ConfigError):
        load_settings(env_file=tmp_path / "missing.env")


def test_real_settings_file_loads(tmp_path, monkeypatch):
    """The shipped config/settings.yaml + .env.example should be a working setup."""
    for name in ("PAPER_TRADING", "ALPACA_BASE_URL", "ALPACA_API_KEY", "APCA_API_BASE_URL"):
        monkeypatch.delenv(name, raising=False)
    from trader.config import PROJECT_ROOT
    settings = load_settings(env_file=PROJECT_ROOT / ".env.example")
    assert settings.watchlist == ("AAPL", "TSLA", "NVDA")


def test_market_data_defaults():
    settings = build_settings(GOOD_ENV, GOOD_FILE)
    assert (settings.market_data_feed, settings.price_adjustment, settings.history_days) == ("iex", "all", 120)


@pytest.mark.parametrize(
    "section",
    [{"feed": "bloomberg"}, {"adjustment": "sideways"}, {"history_days": 2}, {"history_days": "lots"}],
)
def test_bad_market_data_settings_are_rejected(section):
    with pytest.raises(ConfigError):
        build_settings(GOOD_ENV, {**GOOD_FILE, "market_data": section})
