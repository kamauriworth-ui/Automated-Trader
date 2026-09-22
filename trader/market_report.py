"""Builds the price report printed by `python -m trader prices`.

Uses only the MarketDataProvider checklist and the market clock, so tests can
use fake data and a fake clock.
"""

from datetime import datetime

from trader.broker.models import MarketClock
from trader.formatting import money, percent
from trader.market_data.base import MarketDataProvider
from trader.market_data.models import Bar
from trader.market_data.processing import summarize_bars
from trader.market_data.snapshot import MARKET_TIMEZONE, MarketSnapshot, take_snapshot

LINE = "=" * 62
RECENT_CANDLES_SHOWN = 5


def format_candle_row(b: Bar, note: str = "") -> str:
    day = b.timestamp.astimezone(MARKET_TIMEZONE)
    return (
        f"    {day:%Y-%m-%d} {b.open:>10.2f}{b.high:>10.2f}{b.low:>10.2f}"
        f"{b.close:>10.2f}{b.volume:>12,.0f}{note}"
    )


def format_candle_table(completed: list[Bar], in_progress: Bar | None) -> list[str]:
    lines = [f"    {'Date':<11}{'Open':>10}{'High':>10}{'Low':>10}{'Close':>10}{'Volume':>12}"]
    lines += [format_candle_row(b) for b in completed]
    if in_progress is not None:
        lines.append(format_candle_row(in_progress, "  <- today, IN PROGRESS"))
    return lines


def build_symbol_section(snapshot: MarketSnapshot, feed: str) -> list[str]:
    lines = [snapshot.symbol]
    latest = snapshot.latest
    if latest is not None:
        when = latest.timestamp.astimezone(MARKET_TIMEZONE)
        lines.append(f"  Latest trade     : {money(latest.price)}  ({when:%a %Y-%m-%d %H:%M} ET)")
    else:
        lines.append("  Latest trade     : not available")

    mark = "OK   " if snapshot.freshness.ok else "STALE"
    lines.append(f"  Data check       : {mark} - {snapshot.freshness.reason}")

    summary = summarize_bars(snapshot.completed_bars)
    if summary is None:
        lines.append("  No completed price history returned.")
        return lines

    change = summary.change_from_previous_close_pct
    lines.append(
        # The close from our data feed. Can differ by a few cents from the official
        # close, which is set by the main exchange's closing auction.
        f"  Last close ({feed.upper()}) : {money(summary.last_close)}"
        + (f"  ({percent(change)} vs previous day)" if change is not None else "")
    )
    lines.append(
        f"  History          : {summary.count} completed daily candles, "
        f"{summary.first_date.astimezone(MARKET_TIMEZONE):%Y-%m-%d} to "
        f"{summary.last_date.astimezone(MARKET_TIMEZONE):%Y-%m-%d}"
    )
    lines.append(f"  Range            : low {money(summary.period_low)} / high {money(summary.period_high)}")
    lines.append(f"  Last {RECENT_CANDLES_SHOWN} completed days:")
    lines += format_candle_table(snapshot.completed_bars[-RECENT_CANDLES_SHOWN:], snapshot.in_progress_bar)
    return lines


def build_price_report(
    provider: MarketDataProvider,
    clock: MarketClock,
    watchlist: tuple[str, ...],
    days: int,
    feed: str,
    max_age_minutes: int,
    now: datetime | None = None,
) -> str:
    market = "OPEN" if clock.is_open else "CLOSED"
    lines = [LINE, f"  MARKET DATA  (daily candles, feed: {feed.upper()}, market {market})", LINE]
    for symbol in watchlist:
        snapshot = take_snapshot(provider, clock, symbol, days, max_age_minutes, now)
        lines += build_symbol_section(snapshot, feed)
        lines.append("")
    lines.append(LINE)
    return "\n".join(lines)
