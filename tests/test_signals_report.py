"""Tests for running the strategy across the watchlist and printing the results."""

from trader.signals_report import build_signals_report, evaluate_watchlist
from trader.strategy.trend_momentum import TrendMomentumStrategy
from tests.fakes import CLOCK_AFTER_TUESDAY_CLOSE, FakeMarketData, make_bar, utc

AFTER_CLOSE = utc(2026, 9, 22, 21, 0)


def rising_bars(symbol):
    """71 steadily rising candles ending Tue 2026-09-22 (make_bar day 0 = 09-01, day 21 = 09-22)."""
    return [make_bar(day, 160 + day, symbol=symbol) for day in range(-49, 22)]


def test_whole_watchlist_is_evaluated_and_logged(caplog):
    provider = FakeMarketData({"AAPL": rising_bars("AAPL")})
    with caplog.at_level("INFO"):
        results = evaluate_watchlist(
            TrendMomentumStrategy(), provider, CLOCK_AFTER_TUESDAY_CLOSE, ("AAPL", "ZZZZ"), 120, 5, AFTER_CLOSE
        )
    assert [r.symbol for r in results] == ["AAPL", "ZZZZ"]
    assert results[1].signal.value == "WATCH"          # no data at all -> no decision
    assert "SIGNAL AAPL" in caplog.text and "SIGNAL ZZZZ" in caplog.text


def test_report_says_no_orders_and_lists_each_check():
    provider = FakeMarketData({"AAPL": rising_bars("AAPL")})
    results = evaluate_watchlist(
        TrendMomentumStrategy(), provider, CLOCK_AFTER_TUESDAY_CLOSE, ("AAPL",), 120, 5, AFTER_CLOSE
    )
    text = build_signals_report(results, "Trend/Momentum", CLOCK_AFTER_TUESDAY_CLOSE)
    assert "No orders are placed." in text
    assert "Uptrend" in text and "Momentum" in text and "Volume" in text
    assert "ATR 14" in text
