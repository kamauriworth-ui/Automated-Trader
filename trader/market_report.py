"""Builds the price report printed by `python -m trader prices`.

Uses only the MarketDataProvider checklist, so tests can use fake data.
"""

from zoneinfo import ZoneInfo

from trader.formatting import money, percent
from trader.market_data.base import MarketDataProvider
from trader.market_data.models import Bar
from trader.market_data.processing import fetch_clean_daily_bars, summarize_bars

MARKET_TIMEZONE = ZoneInfo("America/New_York")
LINE = "=" * 62
RECENT_CANDLES_SHOWN = 5


def format_candle_table(bars: list[Bar]) -> list[str]:
    lines = [f"    {'Date':<11}{'Open':>10}{'High':>10}{'Low':>10}{'Close':>10}{'Volume':>12}"]
    for b in bars:
        day = b.timestamp.astimezone(MARKET_TIMEZONE)
        lines.append(
            f"    {day:%Y-%m-%d} {b.open:>10.2f}{b.high:>10.2f}{b.low:>10.2f}{b.close:>10.2f}{b.volume:>12,.0f}"
        )
    return lines


def build_symbol_section(provider: MarketDataProvider, symbol: str, days: int) -> list[str]:
    bars = fetch_clean_daily_bars(provider, symbol, days)
    summary = summarize_bars(bars)
    latest = provider.get_latest_price(symbol)

    lines = [symbol]
    if latest is not None:
        when = latest.timestamp.astimezone(MARKET_TIMEZONE)
        lines.append(f"  Latest trade : {money(latest.price)}  ({when:%a %Y-%m-%d %H:%M} ET)")
    else:
        lines.append("  Latest trade : not available")

    if summary is None:
        lines.append("  No price history returned.")
        return lines

    change = summary.change_from_previous_close_pct
    lines.append(
        f"  Last close   : {money(summary.last_close)}"
        + (f"  ({percent(change)} vs previous day)" if change is not None else "")
    )
    lines.append(
        f"  History      : {summary.count} daily candles, "
        f"{summary.first_date.astimezone(MARKET_TIMEZONE):%Y-%m-%d} to "
        f"{summary.last_date.astimezone(MARKET_TIMEZONE):%Y-%m-%d}"
    )
    lines.append(f"  Range        : low {money(summary.period_low)} / high {money(summary.period_high)}")
    lines.append(f"  Last {RECENT_CANDLES_SHOWN} days:")
    lines += format_candle_table(bars[-RECENT_CANDLES_SHOWN:])
    return lines


def build_price_report(provider: MarketDataProvider, watchlist: tuple[str, ...], days: int, feed: str) -> str:
    lines = [LINE, f"  MARKET DATA  (daily candles, feed: {feed.upper()})", LINE]
    for symbol in watchlist:
        lines += build_symbol_section(provider, symbol, days)
        lines.append("")
    lines.append(LINE)
    return "\n".join(lines)
