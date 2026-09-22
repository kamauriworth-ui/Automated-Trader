"""Tests for the price report, using fake price data."""

from trader.market_report import build_price_report
from tests.fakes import FakeMarketData, make_bar


def test_report_shows_latest_price_summary_and_candles():
    bars = [make_bar(day, 100 + day) for day in range(10)]
    report = build_price_report(FakeMarketData({"AAPL": bars}, {"AAPL": 109.5}), ("AAPL",), 30, "iex")
    assert "feed: IEX" in report
    assert "Latest trade     : $109.50" in report
    assert "Last close (IEX) : $109.00" in report
    assert "10 daily candles" in report
    assert report.count("2026-09-") >= 5  # the recent-candles table


def test_report_handles_symbol_with_no_data():
    report = build_price_report(FakeMarketData({}), ("ZZZZ",), 30, "iex")
    assert "Latest trade     : not available" in report
    assert "No price history returned." in report


def test_close_label_follows_the_feed_setting():
    bars = [make_bar(0, 100), make_bar(1, 101)]
    report = build_price_report(FakeMarketData({"AAPL": bars}), ("AAPL",), 30, "sip")
    assert "Last close (SIP) : $101.00" in report
