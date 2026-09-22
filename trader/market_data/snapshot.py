"""Decides whether market data is safe to make decisions with.

Two protections:

1. COMPLETE vs IN-PROGRESS candles
   While the market is open, today's daily candle is still forming: its volume
   is only partial and its "close" is just the latest price. Decisions must use
   finished days only, so we split today's candle off.

2. FRESHNESS
   If the market is open but our latest price is old (say the data connection
   stalled), we must not act on it. The data is marked "stale" and the reason
   is recorded, so later phases can refuse to trade.

"What time is it in the market?" comes from Alpaca's market clock, not from
guessing, so weekends, holidays and early-close days are handled for us.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from trader.broker.models import MarketClock
from trader.market_data.base import MarketDataProvider
from trader.market_data.models import Bar, LatestPrice
from trader.market_data.processing import fetch_clean_daily_bars

MARKET_TIMEZONE = ZoneInfo("America/New_York")


@dataclass(frozen=True)
class Freshness:
    ok: bool
    reason: str


@dataclass(frozen=True)
class MarketSnapshot:
    """Everything known about one stock at one moment, checked and labelled.

    This is the package the strategy (Phase 4) will receive.
    """

    symbol: str
    completed_bars: list[Bar]      # finished trading days only, oldest first
    in_progress_bar: Bar | None    # today's still-forming candle, if the market is open
    latest: LatestPrice | None
    freshness: Freshness
    market_open: bool
    taken_at: datetime


def market_date(moment: datetime):
    """The calendar date in New York (the stock market's home time zone)."""
    return moment.astimezone(MARKET_TIMEZONE).date()


def todays_session_is_finished(clock: MarketClock, now: datetime) -> bool:
    """Has today's trading session ended (or is there no session today)?"""
    if clock.is_open:
        return False
    if market_date(clock.next_open) == market_date(now):
        return False  # it's before today's opening bell
    return True


def is_bar_complete(bar: Bar, clock: MarketClock, now: datetime) -> bool:
    bar_day, today = market_date(bar.timestamp), market_date(now)
    if bar_day < today:
        return True
    if bar_day == today:
        return todays_session_is_finished(clock, now)
    return False  # a candle dated in the future: never trust it


def split_completed(bars: list[Bar], clock: MarketClock, now: datetime) -> tuple[list[Bar], Bar | None]:
    """Separate finished candles from today's still-forming one."""
    completed = [b for b in bars if is_bar_complete(b, clock, now)]
    in_progress = [b for b in bars if not is_bar_complete(b, clock, now)]
    return completed, (in_progress[-1] if in_progress else None)


def check_freshness(
    latest: LatestPrice | None, clock: MarketClock, now: datetime, max_age_minutes: int
) -> Freshness:
    """While the market is open, the latest price must be recent."""
    if not clock.is_open:
        return Freshness(True, "market closed - using the last finished trading day")
    if latest is None:
        return Freshness(False, "market is open but no latest price is available")
    age_minutes = (now - latest.timestamp).total_seconds() / 60
    if age_minutes < -1:
        # A price "from the future" means a clock is wrong somewhere. Don't trust it.
        return Freshness(False, "latest trade is timestamped in the future - a clock is wrong somewhere")
    if age_minutes > max_age_minutes:
        return Freshness(
            False,
            f"latest trade is {age_minutes:.0f} min old (limit {max_age_minutes} min) while the market is open",
        )
    return Freshness(True, f"latest trade is {age_minutes * 60:.0f} seconds old")


def take_snapshot(
    provider: MarketDataProvider,
    clock: MarketClock,
    symbol: str,
    days: int,
    max_age_minutes: int,
    now: datetime | None = None,
) -> MarketSnapshot:
    """Fetch, clean, split and freshness-check the data for one stock."""
    now = now or datetime.now(timezone.utc)
    bars = fetch_clean_daily_bars(provider, symbol, days)
    completed, in_progress = split_completed(bars, clock, now)
    latest = provider.get_latest_price(symbol)
    return MarketSnapshot(
        symbol=symbol,
        completed_bars=completed,
        in_progress_bar=in_progress,
        latest=latest,
        freshness=check_freshness(latest, clock, now, max_age_minutes),
        market_open=clock.is_open,
        taken_at=now,
    )
