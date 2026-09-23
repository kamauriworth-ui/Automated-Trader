"""Strategy 1: Trend + Momentum + Volume.

In one sentence: buy stocks that are already rising steadily, when there's
evidence the rise is real, and step aside when the rise ends.

  BUY   when ALL are true:
          Uptrend  - last close above the long average, and short average above long
          Momentum - last close higher than `momentum_days` days ago
          Volume   - last day's volume at least `volume_min_ratio` x its recent average
                     (1.0 = at least average; 0 = volume rule switched off)
  SELL  when the trend breaks: close below the long average, OR short average below long
  WATCH everything else, and whenever the data can't be trusted or is too short.

Decisions use COMPLETED trading days only (see market_data/snapshot.py).
Volatility (ATR) is calculated and shown but does not affect the signal;
Phase 6 uses it to place stop-losses.
"""

from dataclasses import dataclass

from trader.formatting import money, percent
from trader.market_data.snapshot import MarketSnapshot
from trader.strategy import indicators
from trader.strategy.models import Check, Signal, SignalResult


@dataclass(frozen=True)
class TrendMomentumParams:
    short_ma_days: int = 20
    long_ma_days: int = 50
    momentum_days: int = 10
    volume_avg_days: int = 20
    atr_days: int = 14
    volume_min_ratio: float = 1.0   # volume must be at least this many times its average; 0 = rule off

    @property
    def days_needed(self) -> int:
        """The fewest completed candles needed to calculate everything."""
        return max(self.long_ma_days, self.momentum_days + 1, self.volume_avg_days + 1, self.atr_days + 1)


def compare_words(a: float, b: float) -> str:
    """Describe a vs b the way a person reading prices to the cent would."""
    a_cents, b_cents = round(a, 2), round(b, 2)
    if a_cents > b_cents:
        return "above"
    if a_cents < b_cents:
        return "below"
    return "level with"


def volume_check(ratio: float, minimum: float, days: int) -> Check:
    if minimum <= 0:
        return Check("Volume", True, f"rule OFF ({ratio:.2f}x its {days}-day average)")
    return Check("Volume", ratio >= minimum, f"{ratio:.2f}x its {days}-day average (needs {minimum:g}x)")


class TrendMomentumStrategy:
    name = "Trend/Momentum"

    def __init__(self, params: TrendMomentumParams | None = None) -> None:
        self.params = params or TrendMomentumParams()

    def describe(self) -> str:
        p = self.params
        volume = "volume rule OFF" if p.volume_min_ratio <= 0 else f"volume >= {p.volume_min_ratio:g}x avg"
        return f"{p.short_ma_days}/{p.long_ma_days}-day averages, {p.momentum_days}-day momentum, {volume}"

    def evaluate(self, snapshot: MarketSnapshot) -> SignalResult:
        p = self.params
        bars = snapshot.completed_bars

        # Guard 1: never decide on data we can't trust.
        if not snapshot.freshness.ok:
            return SignalResult(snapshot.symbol, Signal.WATCH, f"No decision: data is stale ({snapshot.freshness.reason})")
        # Guard 2: never decide without enough history to calculate the averages.
        if len(bars) < p.days_needed:
            return SignalResult(
                snapshot.symbol,
                Signal.WATCH,
                f"No decision: need {p.days_needed} completed days of history, have {len(bars)}",
            )

        closes = [b.close for b in bars]
        close = closes[-1]
        short_ma = indicators.simple_moving_average(closes, p.short_ma_days)
        long_ma = indicators.simple_moving_average(closes, p.long_ma_days)
        momentum = indicators.percent_change(closes, p.momentum_days)
        vol_ratio = indicators.volume_ratio(bars, p.volume_avg_days)
        atr = indicators.average_true_range(bars, p.atr_days)

        uptrend = close > long_ma and short_ma > long_ma
        trend_broken = close < long_ma or short_ma < long_ma

        checks = [
            Check(
                "Uptrend",
                uptrend,
                f"close {money(close)} vs {p.long_ma_days}-day avg {money(long_ma)}; "
                f"{p.short_ma_days}-day avg {money(short_ma)} "
                f"{compare_words(short_ma, long_ma)} {p.long_ma_days}-day",
            ),
            Check("Momentum", momentum > 0, f"{percent(momentum)} vs {p.momentum_days} days ago"),
            volume_check(vol_ratio, p.volume_min_ratio, p.volume_avg_days),
        ]
        notes = [f"Volatility: typical daily move (ATR {p.atr_days}) {money(atr)} ({atr / close * 100:.1f}% of price)"]

        if trend_broken:
            reason = (
                f"close is below the {p.long_ma_days}-day average"
                if close < long_ma
                else f"{p.short_ma_days}-day average is below the {p.long_ma_days}-day average"
            )
            signal, summary = Signal.SELL, f"Trend is broken: {reason}"
        elif all(c.passed for c in checks):
            signal, summary = Signal.BUY, "Uptrend with positive momentum, confirmed by volume"
        else:
            failed = ", ".join(c.name.lower() for c in checks if not c.passed)
            signal, summary = Signal.WATCH, f"Not all BUY conditions met (failed: {failed})"

        return SignalResult(snapshot.symbol, signal, summary, close, checks, notes)
