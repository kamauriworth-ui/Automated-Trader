"""Describes what any broker must be able to do, without saying how.

A `Protocol` is a checklist: "any object that has these methods counts as a
Broker". Alpaca's version lives in alpaca_paper.py; tests use a fake one.
This is how we keep Alpaca from leaking into the rest of the program.

Phase 2 is READ-ONLY: there is deliberately no way to place orders here yet.
"""

from typing import Protocol

from trader.broker.models import AccountSummary, AssetInfo, MarketClock, Position


class Broker(Protocol):
    def get_account(self) -> AccountSummary: ...

    def get_positions(self) -> list[Position]: ...

    def get_market_clock(self) -> MarketClock: ...

    def get_asset(self, symbol: str) -> AssetInfo | None:
        """Look up one symbol. Returns None if the broker doesn't know it."""
        ...

    def search_assets(self, text: str) -> list[AssetInfo]:
        """Find tradable stocks whose symbol or company name contains `text`."""
        ...
