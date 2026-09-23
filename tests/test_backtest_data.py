"""Tests for backtest periods, warm-up and loading history (with the SIP -> IEX fallback)."""

from datetime import date

import pytest

from trader.backtest.data import compute_periods, load_history, shift_years, warmup_calendar_days
from trader.errors import DataFeedNotPermittedError
from tests.fakes import CLOCK_DURING_TUESDAY, make_bar, utc


def test_periods_split_development_and_holdout():
    development, holdout = compute_periods(date(2026, 9, 23), years=5, holdout_years=1)
    assert (development.start, development.end) == (date(2021, 9, 23), date(2025, 9, 22))
    assert (holdout.start, holdout.end) == (date(2025, 9, 23), date(2026, 9, 23))


def test_no_holdout_means_one_period():
    development, holdout = compute_periods(date(2026, 9, 23), years=3, holdout_years=0)
    assert development.start == date(2023, 9, 23) and holdout is None


def test_leap_day_shifts_safely():
    assert shift_years(date(2024, 2, 29), 1) == date(2023, 2, 28)


def test_warm_up_covers_the_trading_days_needed():
    assert warmup_calendar_days(50) >= 50 * 365 / 252


class FakeHistory:
    def __init__(self, allowed_feeds=("sip", "iex")):
        self.allowed = allowed_feeds
        self.requests = []

    def get_daily_bars_range(self, symbol, start, end, feed):
        self.requests.append((symbol, feed))
        if feed not in self.allowed:
            raise DataFeedNotPermittedError("not allowed")
        return [make_bar(d, 100, symbol=symbol) for d in range(22)]   # through Tue 09-22


NOW = utc(2026, 9, 22, 18, 0)   # Tuesday, market open


def test_uses_the_preferred_feed_when_allowed():
    bars, feed = load_history(FakeHistory(), ("AAPL", "NVDA"), NOW, CLOCK_DURING_TUESDAY, "sip", NOW)
    assert feed == "sip"
    assert set(bars) == {"AAPL", "NVDA"}


def test_falls_back_to_iex_for_every_symbol():
    provider = FakeHistory(allowed_feeds=("iex",))
    bars, feed = load_history(provider, ("AAPL", "NVDA"), NOW, CLOCK_DURING_TUESDAY, "sip", NOW)
    assert feed == "iex"
    assert all(f == "iex" for sym, f in provider.requests[1:])


def test_iex_refused_too_is_an_error():
    with pytest.raises(DataFeedNotPermittedError):
        load_history(FakeHistory(allowed_feeds=()), ("AAPL",), NOW, CLOCK_DURING_TUESDAY, "sip", NOW)


def test_todays_unfinished_candle_is_dropped():
    bars, _ = load_history(FakeHistory(), ("AAPL",), NOW, CLOCK_DURING_TUESDAY, "sip", NOW)
    assert len(bars["AAPL"]) == 21   # the 22nd candle (today, market open) is left out
