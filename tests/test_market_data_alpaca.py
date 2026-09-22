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
