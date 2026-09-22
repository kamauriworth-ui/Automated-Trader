"""Plain data containers for market data."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Bar:
    """One "candle": what a stock's price did during one time period (here, one day).

    open   = price of the first trade in the period
    high   = highest price reached
    low    = lowest price reached
    close  = price of the last trade in the period
    volume = number of shares traded
    """

    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class LatestPrice:
    """The most recent trade we know about for a stock."""

    symbol: str
    price: float
    timestamp: datetime
