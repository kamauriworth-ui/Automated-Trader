"""Getting historical data ready for a backtest.

- Works out the two test periods: the DEVELOPMENT period (where we're allowed
  to look and adjust) and the HOLDOUT period (the most recent part, kept
  sealed as a final exam - see the Phase 5 notes on overfitting).
- Downloads extra "warm-up" history before the period starts, so the strategy
  has its 50 days of averages ready on the very first day of the test.
- Tries the preferred feed (full-market SIP) and falls back to IEX if the
  account's data plan refuses.
"""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Protocol

from trader.backtest.models import Period
from trader.broker.models import MarketClock
from trader.errors import DataFeedNotPermittedError
from trader.market_data.models import Bar
from trader.market_data.processing import clean_bars
from trader.market_data.snapshot import split_completed

log = logging.getLogger(__name__)

# Recent SIP data is off-limits on Alpaca's free plan, so never ask for the last few minutes.
RECENT_DATA_BUFFER = timedelta(minutes=20)


class HistoricalDataProvider(Protocol):
    def get_daily_bars_range(self, symbol: str, start: datetime, end: datetime, feed: str) -> list[Bar]: ...


def shift_years(day: date, years: int) -> date:
    """The same calendar date `years` earlier (29 Feb becomes 28 Feb)."""
    try:
        return day.replace(year=day.year - years)
    except ValueError:
        return day.replace(year=day.year - years, day=28)


def compute_periods(today: date, years: int, holdout_years: int) -> tuple[Period, Period | None]:
    """Split the last `years` into a development period and a sealed holdout period."""
    start = shift_years(today, years)
    if holdout_years == 0:
        return Period("development", start, today), None
    holdout_start = shift_years(today, holdout_years)
    development = Period("development", start, holdout_start - timedelta(days=1))
    holdout = Period("holdout", holdout_start, today)
    return development, holdout


def warmup_calendar_days(trading_days_needed: int) -> int:
    """Calendar days that comfortably contain `trading_days_needed` trading days.

    There are about 252 trading days in 365 calendar days (weekends + holidays),
    so multiply by ~1.5 and add a margin.
    """
    return int(trading_days_needed * 1.5) + 14


def load_history(
    provider: HistoricalDataProvider,
    symbols: tuple[str, ...],
    start: datetime,
    clock: MarketClock,
    preferred_feed: str,
    now: datetime | None = None,
) -> tuple[dict[str, list[Bar]], str]:
    """Download, clean and keep only COMPLETED daily candles for every symbol.

    Returns the candles and the feed actually used. All symbols always use the
    same feed, so results are comparable.
    """
    now = now or datetime.now(timezone.utc)
    end = now - RECENT_DATA_BUFFER
    feed = preferred_feed
    bars_by_symbol: dict[str, list[Bar]] = {}
    for symbol in symbols:
        try:
            raw = provider.get_daily_bars_range(symbol, start, end, feed)
        except DataFeedNotPermittedError:
            if feed == "iex":
                raise
            log.warning("Data feed '%s' not allowed on this account - switching to 'iex' for all symbols", feed)
            feed = "iex"
            return load_history(provider, symbols, start, clock, "iex", now)
        completed, _ = split_completed(clean_bars(raw), clock, now)
        bars_by_symbol[symbol] = completed
        log.info("Backtest data: %s %d completed daily candles (%s feed)", symbol, len(completed), feed)
    return bars_by_symbol, feed
