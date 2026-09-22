"""Runs the strategy on every watchlist stock and formats the results.

Also writes one line per decision to the log file, so there's a permanent
record of what the system concluded and why.
"""

import logging
from datetime import datetime

from trader.broker.models import MarketClock
from trader.formatting import money
from trader.market_data.base import MarketDataProvider
from trader.market_data.snapshot import take_snapshot
from trader.strategy.base import Strategy
from trader.strategy.models import SignalResult

log = logging.getLogger(__name__)
LINE = "=" * 62


def evaluate_watchlist(
    strategy: Strategy,
    provider: MarketDataProvider,
    clock: MarketClock,
    watchlist: tuple[str, ...],
    days: int,
    max_age_minutes: int,
    now: datetime | None = None,
) -> list[SignalResult]:
    results = []
    for symbol in watchlist:
        snapshot = take_snapshot(provider, clock, symbol, days, max_age_minutes, now)
        result = strategy.evaluate(snapshot)
        log.info("SIGNAL %s %s (%s) - %s", result.symbol, result.signal.value, strategy.name, result.summary)
        results.append(result)
    return results


def format_result(result: SignalResult) -> list[str]:
    price = f"close {money(result.price)}" if result.price is not None else "no price"
    lines = [f"{result.symbol:<6} {result.signal.value:<5}  ({price})", f"  {result.summary}"]
    for check in result.checks:
        mark = "✅" if check.passed else "❌"
        lines.append(f"  {mark} {check.name:<9}: {check.detail}")
    for note in result.notes:
        lines.append(f"  -- {note}")
    return lines


def build_signals_report(results: list[SignalResult], strategy_name: str, clock: MarketClock) -> str:
    market = "OPEN" if clock.is_open else "CLOSED"
    lines = [
        LINE,
        f"  SIGNALS  -  strategy: {strategy_name}  (market {market})",
        "  Signals only. No orders are placed.",
        LINE,
    ]
    lines += [f"  {r.symbol:<6} {r.signal.value}" for r in results]
    lines.append(LINE)
    for result in results:
        lines += format_result(result)
        lines.append("")
    lines.append(LINE)
    return "\n".join(lines)
