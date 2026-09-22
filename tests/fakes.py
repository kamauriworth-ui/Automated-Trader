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


# ---------- market data fakes ----------

from datetime import timedelta  # noqa: E402

from trader.market_data.models import Bar, LatestPrice  # noqa: E402

START_DAY = datetime(2026, 9, 1, 4, 0, tzinfo=timezone.utc)  # midnight New York time


def make_bar(day: int, close: float, symbol: str = "AAPL", **overrides) -> Bar:
    """A sensible candle `day` days after START_DAY. Override any field to break it."""
    fields = dict(
        symbol=symbol,
        timestamp=START_DAY + timedelta(days=day),
        open=close - 1,
        high=close + 2,
        low=close - 2,
        close=close,
        volume=1_000_000,
    )
    fields.update(overrides)
    return Bar(**fields)


class FakeMarketData:
    """A pretend price source that returns whatever candles we give it."""

    def __init__(self, bars: dict[str, list[Bar]], latest: dict[str, float] | None = None) -> None:
        self.bars = bars
        self.latest = latest or {}

    def get_daily_bars(self, symbol: str, days: int) -> list[Bar]:
        return list(self.bars.get(symbol, []))

    def get_latest_price(self, symbol: str) -> LatestPrice | None:
        if symbol not in self.latest:
            return None
        return LatestPrice(symbol, self.latest[symbol], datetime(2026, 9, 22, 19, 59, tzinfo=timezone.utc))


class FakeAlpacaDataClient:
    """Imitates the parts of Alpaca's StockHistoricalDataClient that we use."""

    def __init__(self) -> None:
        self.last_bars_request = None

    def get_stock_bars(self, request):
        self.last_bars_request = request
        raw = SimpleNamespace(
            timestamp=START_DAY, open=100.0, high=105.0, low=99.0, close=104.0, volume=5_000_000.0
        )
        return SimpleNamespace(data={"AAPL": [raw]})

    def get_stock_latest_trade(self, request):
        return {"AAPL": SimpleNamespace(price=104.5, timestamp=START_DAY)}
