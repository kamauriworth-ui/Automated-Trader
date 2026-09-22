"""The checklist any strategy must follow: take a snapshot, return a signal.

Having this lets us add or swap strategies later (Phase 12) without touching
the code that runs them.
"""

from typing import Protocol

from trader.market_data.snapshot import MarketSnapshot
from trader.strategy.models import SignalResult


class Strategy(Protocol):
    name: str

    def evaluate(self, snapshot: MarketSnapshot) -> SignalResult: ...
