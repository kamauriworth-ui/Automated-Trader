"""Measurements that summarise a backtest.

All functions are small and independent so each can be checked by hand.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from trader.backtest.models import Trade


@dataclass(frozen=True)
class TradeStats:
    count: int
    wins: int
    losses: int
    win_rate_pct: float | None      # None when there are no trades
    avg_gain_pct: float | None      # average % gain of the winning trades
    avg_loss_pct: float | None      # average % loss of the losing trades (a negative number)
    risk_reward: float | None       # avg gain / size of avg loss (above 1 = wins bigger than losses)
    total_pnl: float                # dollars
    avg_holding_days: float | None


def _average(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def trade_stats(trades: list[Trade]) -> TradeStats:
    gains = [t.return_pct for t in trades if t.pnl > 0]
    losses = [t.return_pct for t in trades if t.pnl <= 0]   # break-even counts as "not a win"
    avg_gain, avg_loss = _average(gains), _average(losses)
    risk_reward = None
    if avg_gain is not None and avg_loss is not None and avg_loss < 0:
        risk_reward = avg_gain / abs(avg_loss)
    return TradeStats(
        count=len(trades),
        wins=len(gains),
        losses=len(losses),
        win_rate_pct=len(gains) / len(trades) * 100 if trades else None,
        avg_gain_pct=avg_gain,
        avg_loss_pct=avg_loss,
        risk_reward=risk_reward,
        total_pnl=sum(t.pnl for t in trades),
        avg_holding_days=_average([t.holding_days for t in trades]),
    )


def total_return_pct(values: list[float]) -> float | None:
    """Change from the first value to the last, in percent."""
    if len(values) < 2 or values[0] == 0:
        return None
    return (values[-1] - values[0]) / values[0] * 100


def max_drawdown_pct(values: list[float]) -> float:
    """The worst fall from a high point to a later low point, in percent (0 or negative).

    Example: 100 -> 120 -> 90 -> 130  gives  (90 - 120) / 120 = -25%
    """
    peak = None
    worst = 0.0
    for value in values:
        peak = value if peak is None else max(peak, value)
        if peak > 0:
            worst = min(worst, (value - peak) / peak * 100)
    return worst


def combine_curves(curves: list[list[tuple[date, float]]]) -> list[tuple[date, float]]:
    """Add several daily value curves together into one (the whole portfolio).

    If one curve has no value on a date, its most recent earlier value is used.
    """
    all_dates = sorted({d for curve in curves for d, _ in curve})
    lookups = [dict(curve) for curve in curves]
    last_known = [curve[0][1] if curve else 0.0 for curve in curves]
    combined = []
    for day in all_dates:
        for n, lookup in enumerate(lookups):
            if day in lookup:
                last_known[n] = lookup[day]
        combined.append((day, sum(last_known)))
    return combined


def yearly_returns(curve: list[tuple[date, float]]) -> dict[int, float]:
    """Percent change within each calendar year (from the previous year's last value)."""
    if len(curve) < 2:
        return {}
    last_value_of_year: dict[int, float] = {}
    for day, value in curve:
        last_value_of_year[day.year] = value
    returns = {}
    previous = curve[0][1]
    for year in sorted(last_value_of_year):
        end = last_value_of_year[year]
        if previous:
            returns[year] = (end - previous) / previous * 100
        previous = end
    return returns


def trades_by_exit_year(trades: list[Trade]) -> dict[int, list[Trade]]:
    grouped: dict[int, list[Trade]] = defaultdict(list)
    for t in trades:
        grouped[t.exit_date.year].append(t)
    return dict(grouped)
