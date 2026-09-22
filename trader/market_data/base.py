"""Describes what any market-data source must be able to do (a "checklist").

Alpaca's version is in alpaca_data.py. Tests use a fake one. Later,
backtesting can use one that reads saved history from a file.
"""

from typing import Protocol

from trader.market_data.models import Bar, LatestPrice


class MarketDataProvider(Protocol):
    def get_daily_bars(self, symbol: str, days: int) -> list[Bar]:
        """Daily candles covering roughly the last `days` calendar days."""
        ...

    def get_latest_price(self, symbol: str) -> LatestPrice | None:
        """The most recent trade price, or None if there isn't one."""
        ...
