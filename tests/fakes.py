"""Stand-ins for Alpaca so tests never touch the internet or a real account.

`fake_alpaca_client` imitates the pieces of Alpaca's TradingClient that our
code uses, returning made-up but realistic data.
"""

from datetime import datetime, timezone
from types import SimpleNamespace

from trader.broker.models import AccountSummary, AssetInfo, MarketClock, Position


def fake_alpaca_account(account_number: str = "PA3TESTACCT1") -> SimpleNamespace:
    return SimpleNamespace(
        account_number=account_number,
        status=SimpleNamespace(value="ACTIVE"),
        equity="100500.25",
        last_equity="100000.00",
        cash="90000.00",
        buying_power="190000.00",
        trading_blocked=False,
        account_blocked=False,
    )


class FakeAlpacaClient:
    def __init__(self, account_number: str = "PA3TESTACCT1",
                 base_url: str = "https://paper-api.alpaca.markets") -> None:
        self._base_url = base_url
        self._account_number = account_number

    def get_account(self):
        return fake_alpaca_account(self._account_number)


class FakeBroker:
    """A pretend broker with fixed data, used to test the status report."""

    def __init__(self, positions: list[Position] | None = None, market_open: bool = False) -> None:
        self.positions = positions or []
        self.market_open = market_open

    def get_account(self) -> AccountSummary:
        return AccountSummary("PA3TESTACCT1", "ACTIVE", 100500.25, 100000.0, 90000.0, 190000.0, False)

    def get_positions(self) -> list[Position]:
        return self.positions

    def get_market_clock(self) -> MarketClock:
        return MarketClock(
            is_open=self.market_open,
            next_open=datetime(2026, 9, 23, 13, 30, tzinfo=timezone.utc),   # 09:30 New York
            next_close=datetime(2026, 9, 22, 20, 0, tzinfo=timezone.utc),   # 16:00 New York
        )

    def get_asset(self, symbol: str) -> AssetInfo | None:
        known = {"AAPL": "Apple Inc. Common Stock"}
        return AssetInfo(symbol, known[symbol], True) if symbol in known else None

    def search_assets(self, text: str) -> list[AssetInfo]:
        return []
