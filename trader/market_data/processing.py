"""Checks and cleans price data before anything else uses it.

Why: bad data leads to bad decisions. A single wrong price (say, a close of $0)
could look like a crash and trigger a SELL. So every candle is checked here, and
anything impossible is thrown away (and logged) instead of silently used.

These functions don't care where the data came from, so they work the same for
live data, historical files, and test data.
"""

import logging
from dataclasses import dataclass
from datetime import datetime

from trader.market_data.base import MarketDataProvider
from trader.market_data.models import Bar

log = logging.getLogger(__name__)


def problems_with_bar(bar: Bar) -> list[str]:
    """Return a list of reasons a candle is impossible. Empty list = it looks fine."""
    problems = []
    if min(bar.open, bar.high, bar.low, bar.close) <= 0:
        problems.append("a price is zero or negative")
    if bar.high < bar.low:
        problems.append("high is below low")
    if not (bar.low <= bar.open <= bar.high and bar.low <= bar.close <= bar.high):
        problems.append("open/close is outside the high-low range")
    if bar.volume < 0:
        problems.append("volume is negative")
    return problems


def clean_bars(bars: list[Bar]) -> list[Bar]:
    """Sort candles oldest -> newest, drop duplicates, and drop impossible ones."""
    cleaned: list[Bar] = []
    seen: set[datetime] = set()
    for bar in sorted(bars, key=lambda b: b.timestamp):
        if bar.timestamp in seen:
            log.warning("%s: dropped duplicate candle for %s", bar.symbol, bar.timestamp)
            continue
        problems = problems_with_bar(bar)
        if problems:
            log.warning("%s: dropped bad candle for %s (%s)", bar.symbol, bar.timestamp, "; ".join(problems))
            continue
        seen.add(bar.timestamp)
        cleaned.append(bar)
    return cleaned


def fetch_clean_daily_bars(provider: MarketDataProvider, symbol: str, days: int) -> list[Bar]:
    """Get daily candles from any provider, cleaned. This is what the strategy will use."""
    return clean_bars(provider.get_daily_bars(symbol, days))


@dataclass(frozen=True)
class BarSummary:
    """A few headline numbers about a run of candles."""

    count: int
    first_date: datetime
    last_date: datetime
    last_close: float
    change_from_previous_close_pct: float | None  # None if only one candle
    period_high: float
    period_low: float


def summarize_bars(bars: list[Bar]) -> BarSummary | None:
    """Summarise cleaned candles. Returns None if there are none."""
    if not bars:
        return None
    last = bars[-1]
    change = None
    if len(bars) >= 2:
        previous_close = bars[-2].close
        change = (last.close - previous_close) / previous_close * 100
    return BarSummary(
        count=len(bars),
        first_date=bars[0].timestamp,
        last_date=last.timestamp,
        last_close=last.close,
        change_from_previous_close_pct=change,
        period_high=max(b.high for b in bars),
        period_low=min(b.low for b in bars),
    )
