"""Indicators: small calculations that summarise price history.

Each function takes plain numbers or candles (oldest first) and returns one
number describing the most recent day. They are deliberately simple so they
can be checked by hand.
"""

from trader.market_data.models import Bar


def simple_moving_average(values: list[float], days: int) -> float:
    """The average of the last `days` values.

    Example: closes 10, 11, 12, 13 with days=2 -> (12 + 13) / 2 = 12.5
    """
    if len(values) < days:
        raise ValueError(f"need {days} values, got {len(values)}")
    return sum(values[-days:]) / days


def percent_change(values: list[float], days: int) -> float:
    """How much the latest value changed versus `days` values earlier, in percent.

    Example: 100 ten days ago, 105 now -> +5.0
    """
    if len(values) < days + 1:
        raise ValueError(f"need {days + 1} values, got {len(values)}")
    past = values[-1 - days]
    return (values[-1] - past) / past * 100


def volume_ratio(bars: list[Bar], days: int) -> float:
    """The latest day's volume divided by the average of the `days` days BEFORE it.

    1.0 = a normal day, 2.0 = twice the usual trading, 0.5 = half.
    The latest day is left out of its own average so it's compared against history.
    """
    if len(bars) < days + 1:
        raise ValueError(f"need {days + 1} candles, got {len(bars)}")
    previous = [b.volume for b in bars[-1 - days:-1]]
    average = sum(previous) / days
    return bars[-1].volume / average if average > 0 else 0.0


def true_range(bar: Bar, previous_close: float) -> float:
    """How far the price travelled in one day, including any overnight jump.

    Usually that's just high - low. But if the stock opened far away from
    yesterday's close (a "gap"), that jump counts too.
    """
    return max(bar.high - bar.low, abs(bar.high - previous_close), abs(bar.low - previous_close))


def average_true_range(bars: list[Bar], days: int) -> float:
    """ATR: the average daily travel over the last `days` days (a volatility measure)."""
    if len(bars) < days + 1:
        raise ValueError(f"need {days + 1} candles, got {len(bars)}")
    recent = bars[-days - 1:]
    ranges = [true_range(recent[i], recent[i - 1].close) for i in range(1, len(recent))]
    return sum(ranges) / days
