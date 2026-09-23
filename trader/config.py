"""Loads and validates all settings in one place.

Two sources of settings:
  * .env                 -> secrets and the paper-trading switch
  * config/settings.yaml -> everything else (watchlist, logging, ...)

The rest of the program never reads those files directly. It receives a
`Settings` object from `load_settings()`. That way, if a setting is wrong we
find out immediately at startup, not halfway through a trading day.
"""

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import dotenv_values

from trader.errors import ConfigError
from trader import safety
from trader.strategy.trend_momentum import TrendMomentumParams
from trader.backtest.models import BacktestSettings

# The folder that contains this project (one level above the `trader` package).
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"
DEFAULT_SETTINGS_FILE = PROJECT_ROOT / "config" / "settings.yaml"

# A ticker symbol: 1-5 capital letters, optionally a dot and a class letter (e.g. BRK.B).
SYMBOL_PATTERN = re.compile(r"^[A-Z]{1,5}(\.[A-Z])?$")
LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")
DATA_FEEDS = ("iex", "sip")
PRICE_ADJUSTMENTS = ("raw", "split", "dividend", "all")


@dataclass(frozen=True)
class Settings:
    """All validated settings. `frozen=True` means nothing can change them later."""

    paper_trading: bool
    alpaca_base_url: str
    alpaca_api_key: str | None
    alpaca_secret_key: str | None
    watchlist: tuple[str, ...]
    log_level: str
    log_file: Path
    market_data_feed: str = "iex"
    price_adjustment: str = "all"
    history_days: int = 120
    max_price_age_minutes: int = 5
    strategy: TrendMomentumParams = TrendMomentumParams()
    backtest: BacktestSettings = BacktestSettings()

    @property
    def has_api_keys(self) -> bool:
        return bool(self.alpaca_api_key and self.alpaca_secret_key)


def read_environment(env_file: Path = DEFAULT_ENV_FILE) -> dict[str, str]:
    """Combine the .env file with the real environment variables.

    Real environment variables win if both define the same name.
    """
    if not env_file.exists():
        raise ConfigError(
            f"No .env file found at {env_file}. Create one by copying .env.example."
        )
    from_file = {k: v for k, v in dotenv_values(env_file).items() if v is not None}
    return {**from_file, **os.environ}


def read_settings_file(settings_file: Path = DEFAULT_SETTINGS_FILE) -> dict:
    """Read the YAML settings file into a Python dictionary."""
    if not settings_file.exists():
        raise ConfigError(f"Settings file not found: {settings_file}")
    try:
        data = yaml.safe_load(settings_file.read_text())
    except yaml.YAMLError as exc:
        raise ConfigError(f"{settings_file} is not valid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"{settings_file} is empty or not laid out as 'key: value' pairs.")
    return data


def parse_watchlist(raw: object) -> tuple[str, ...]:
    """Turn the watchlist from the YAML file into a clean tuple of symbols."""
    if not isinstance(raw, list) or len(raw) == 0:
        raise ConfigError("'watchlist' in settings.yaml must be a non-empty list of symbols.")

    symbols: list[str] = []
    for item in raw:
        symbol = str(item).strip().upper()
        if not SYMBOL_PATTERN.match(symbol):
            raise ConfigError(f"'{item}' in the watchlist is not a valid ticker symbol.")
        if symbol not in symbols:  # silently drop duplicates
            symbols.append(symbol)
    return tuple(symbols)


def parse_logging(raw: object) -> tuple[str, Path]:
    """Read the logging section; fall back to sensible defaults if it is missing."""
    section = raw if isinstance(raw, dict) else {}
    level = str(section.get("level", "INFO")).strip().upper()
    if level not in LOG_LEVELS:
        raise ConfigError(f"logging.level must be one of {LOG_LEVELS}, not '{level}'.")
    log_file = Path(section.get("file", "logs/trader.log"))
    if not log_file.is_absolute():
        log_file = PROJECT_ROOT / log_file
    return level, log_file


def parse_market_data(raw: object) -> tuple[str, str, int, int]:
    """Read the market_data section; fall back to sensible defaults if it is missing."""
    section = raw if isinstance(raw, dict) else {}
    feed = str(section.get("feed", "iex")).strip().lower()
    if feed not in DATA_FEEDS:
        raise ConfigError(f"market_data.feed must be one of {DATA_FEEDS}, not '{feed}'.")
    adjustment = str(section.get("adjustment", "all")).strip().lower()
    if adjustment not in PRICE_ADJUSTMENTS:
        raise ConfigError(f"market_data.adjustment must be one of {PRICE_ADJUSTMENTS}, not '{adjustment}'.")
    history_days = section.get("history_days", 120)
    if not isinstance(history_days, int) or not 5 <= history_days <= 3650:
        raise ConfigError("market_data.history_days must be a whole number between 5 and 3650.")
    max_age = section.get("max_price_age_minutes", 5)
    if not isinstance(max_age, int) or not 1 <= max_age <= 60:
        raise ConfigError("market_data.max_price_age_minutes must be a whole number between 1 and 60.")
    return feed, adjustment, history_days, max_age


def parse_strategy(raw: object) -> TrendMomentumParams:
    """Read the strategy section; any missing number uses the default."""
    section = raw if isinstance(raw, dict) else {}
    defaults = TrendMomentumParams()
    values = {}
    for name in ("short_ma_days", "long_ma_days", "momentum_days", "volume_avg_days", "atr_days"):
        value = section.get(name, getattr(defaults, name))
        if not isinstance(value, int) or isinstance(value, bool) or not 2 <= value <= 250:
            raise ConfigError(f"strategy.{name} must be a whole number between 2 and 250.")
        values[name] = value
    if values["short_ma_days"] >= values["long_ma_days"]:
        raise ConfigError("strategy.short_ma_days must be smaller than strategy.long_ma_days.")
    return TrendMomentumParams(**values)


def _number(section: dict, name: str, default, low: float, high: float, whole: bool = False):
    value = section.get(name, default)
    ok_type = isinstance(value, int) if whole else isinstance(value, (int, float))
    if isinstance(value, bool) or not ok_type or not low <= value <= high:
        kind = "a whole number" if whole else "a number"
        raise ConfigError(f"backtest.{name} must be {kind} between {low:g} and {high:g}.")
    return value


def parse_backtest(raw: object) -> BacktestSettings:
    """Read the backtest section; any missing value uses the default."""
    section = raw if isinstance(raw, dict) else {}
    d = BacktestSettings()
    years = _number(section, "years", d.years, 1, 20, whole=True)
    holdout = _number(section, "holdout_years", d.holdout_years, 0, 19, whole=True)
    if holdout >= years:
        raise ConfigError("backtest.holdout_years must be smaller than backtest.years.")
    feed = str(section.get("feed", d.feed)).strip().lower()
    if feed not in DATA_FEEDS:
        raise ConfigError(f"backtest.feed must be one of {DATA_FEEDS}, not '{feed}'.")
    return BacktestSettings(
        years=years,
        holdout_years=holdout,
        trade_amount=float(_number(section, "trade_amount", d.trade_amount, 100, 1_000_000)),
        slippage_pct=float(_number(section, "slippage_pct", d.slippage_pct, 0, 2)),
        feed=feed,
    )


def build_settings(env: Mapping[str, str], file_data: Mapping) -> Settings:
    """Validate everything and build the Settings object.

    Kept separate from file reading so tests can pass in plain dictionaries.
    """
    # Safety first: if anything here fails, nothing else is even looked at.
    safety.run_startup_safety_checks(env)

    level, log_file = parse_logging(file_data.get("logging"))
    feed, adjustment, history_days, max_age = parse_market_data(file_data.get("market_data"))
    return Settings(
        paper_trading=True,
        alpaca_base_url=safety.require_paper_endpoint(env.get("ALPACA_BASE_URL")),
        alpaca_api_key=(env.get("ALPACA_API_KEY") or "").strip() or None,
        alpaca_secret_key=(env.get("ALPACA_SECRET_KEY") or "").strip() or None,
        watchlist=parse_watchlist(file_data.get("watchlist")),
        log_level=level,
        log_file=log_file,
        market_data_feed=feed,
        price_adjustment=adjustment,
        history_days=history_days,
        max_price_age_minutes=max_age,
        strategy=parse_strategy(file_data.get("strategy")),
        backtest=parse_backtest(file_data.get("backtest")),
    )


def load_settings(
    env_file: Path = DEFAULT_ENV_FILE,
    settings_file: Path = DEFAULT_SETTINGS_FILE,
) -> Settings:
    """The one function the rest of the app calls to get its settings."""
    return build_settings(read_environment(env_file), read_settings_file(settings_file))
