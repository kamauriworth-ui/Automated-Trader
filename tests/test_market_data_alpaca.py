"""Tests for the Alpaca price-data adapter, using a fake Alpaca client."""

from alpaca.data.enums import Adjustment, DataFeed
from alpaca.data.timeframe import TimeFrame

from trader.market_data.alpaca_data import AlpacaMarketData
from tests.fakes import FakeAlpacaDataClient


def test_bars_are_converted_to_our_bar_objects():
    client = FakeAlpacaDataClient()
    bars = AlpacaMarketData(client, "iex", "all").get_daily_bars("AAPL", 30)
    assert len(bars) == 1
    assert bars[0].symbol == "AAPL" and bars[0].close == 104.0


def test_request_uses_configured_feed_adjustment_and_daily_candles():
    client = FakeAlpacaDataClient()
    AlpacaMarketData(client, "iex", "all").get_daily_bars("AAPL", 30)
    request = client.last_bars_request
    assert request.feed == DataFeed.IEX
    assert request.adjustment == Adjustment.ALL
    assert request.timeframe.value == TimeFrame.Day.value


def test_latest_price_is_converted():
    latest = AlpacaMarketData(FakeAlpacaDataClient(), "iex", "all").get_latest_price("AAPL")
    assert latest.price == 104.5


def test_unknown_symbol_has_no_latest_price():
    assert AlpacaMarketData(FakeAlpacaDataClient(), "iex", "all").get_latest_price("ZZZZ") is None


# ---------- history for backtesting ----------

import json  # noqa: E402
from datetime import datetime, timezone  # noqa: E402
from types import SimpleNamespace  # noqa: E402

import pytest  # noqa: E402
from alpaca.common.exceptions import APIError  # noqa: E402

from trader.errors import BrokerError, DataFeedNotPermittedError  # noqa: E402


def api_error(status: int, message: str) -> APIError:
    http_error = SimpleNamespace(response=SimpleNamespace(status_code=status), request=None)
    return APIError(json.dumps({"code": status, "message": message}), http_error)


class RefusingClient(FakeAlpacaDataClient):
    def __init__(self, error):
        super().__init__()
        self.error = error

    def get_stock_bars(self, request):
        raise self.error


START, END = datetime(2021, 1, 1, tzinfo=timezone.utc), datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_history_request_uses_the_requested_feed():
    client = FakeAlpacaDataClient()
    bars = AlpacaMarketData(client, "iex", "all").get_daily_bars_range("AAPL", START, END, "sip")
    assert client.last_bars_request.feed == DataFeed.SIP
    assert len(bars) == 1


def test_data_plan_refusal_becomes_a_specific_error():
    client = RefusingClient(api_error(403, "subscription does not permit querying recent SIP data"))
    with pytest.raises(DataFeedNotPermittedError):
        AlpacaMarketData(client, "iex", "all").get_daily_bars_range("AAPL", START, END, "sip")


def test_other_refusals_stay_general_errors():
    client = RefusingClient(api_error(403, "forbidden"))
    with pytest.raises(BrokerError) as caught:
        AlpacaMarketData(client, "iex", "all").get_daily_bars_range("AAPL", START, END, "sip")
    assert not isinstance(caught.value, DataFeedNotPermittedError)
