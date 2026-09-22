"""Tests for the price report, using fake price data."""

from trader.market_report import build_price_report
from tests.fakes import CLOCK_AFTER_TUESDAY_CLOSE, CLOCK_DURING_TUESDAY, FakeMarketData, make_bar, utc

AFTER_CLOSE = utc(2026, 9, 22, 21, 0)


def report(provider, watchlist=("AAPL",), feed="iex", clock=CLOCK_AFTER_TUESDAY_CLOSE, now=AFTER_CLOSE):
    return build_price_report(provider, clock, watchlist, 30, feed, 5, now)


def test_report_shows_latest_price_summary_and_candles():
    bars = [make_bar(day, 100 + day) for day in range(10)]
    report_text = report(FakeMarketData({"AAPL": bars}, {"AAPL": 109.5}))
    assert "feed: IEX" in report_text
    assert "Latest trade     : $109.50" in report_text
    assert "Last close (IEX) : $109.00" in report_text
    assert "10 completed daily candles" in report_text
    assert report_text.count("2026-09-") >= 5  # the recent-candles table


def test_report_handles_symbol_with_no_data():
    report_text = report(FakeMarketData({}), ("ZZZZ",))
    assert "Latest trade     : not available" in report_text
    assert "No completed price history returned." in report_text


def test_close_label_follows_the_feed_setting():
    bars = [make_bar(0, 100), make_bar(1, 101)]
    report_text = report(FakeMarketData({"AAPL": bars}), feed="sip")
    assert "Last close (SIP) : $101.00" in report_text


def test_report_marks_todays_candle_in_progress():
    bars = [make_bar(day, 100 + day) for day in range(22)]          # through Tue 09-22
    provider = FakeMarketData({"AAPL": bars}, {"AAPL": 121.0}, latest_time=utc(2026, 9, 22, 18, 0))
    text = report(provider, clock=CLOCK_DURING_TUESDAY, now=utc(2026, 9, 22, 18, 1))
    assert "market OPEN" in text
    assert "IN PROGRESS" in text
    assert "Last close (IEX) : $120.00" in text    # Monday: the last FINISHED day
    assert "21 completed daily candles" in text
    assert "Data check       : OK" in text


def test_report_flags_stale_data_while_market_is_open():
    bars = [make_bar(day, 100 + day) for day in range(22)]
    provider = FakeMarketData({"AAPL": bars}, {"AAPL": 121.0}, latest_time=utc(2026, 9, 22, 17, 30))
    text = report(provider, clock=CLOCK_DURING_TUESDAY, now=utc(2026, 9, 22, 18, 0))
    assert "Data check       : STALE - latest trade is 30 min old" in text
