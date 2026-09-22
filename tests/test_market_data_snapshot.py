"""Tests for the freshness check and complete/in-progress candle handling."""

from trader.market_data.models import LatestPrice
from trader.market_data.snapshot import check_freshness, is_bar_complete, split_completed, take_snapshot
from tests.fakes import (
    CLOCK_AFTER_TUESDAY_CLOSE,
    CLOCK_DURING_TUESDAY,
    FakeMarketData,
    make_bar,
    make_clock,
    utc,
)

# make_bar(day=N) is dated 2026-09-01 + N days, so day 20 = Mon 09-21 and day 21 = Tue 09-22.
MONDAY, TUESDAY, WEDNESDAY = 20, 21, 22


# ---------- which candles are finished? ----------

def test_during_trading_todays_candle_is_in_progress():
    now = utc(2026, 9, 22, 18, 0)  # Tuesday 2:00 PM ET
    assert is_bar_complete(make_bar(MONDAY, 100), CLOCK_DURING_TUESDAY, now)
    assert not is_bar_complete(make_bar(TUESDAY, 100), CLOCK_DURING_TUESDAY, now)


def test_after_the_close_todays_candle_is_complete():
    now = utc(2026, 9, 22, 21, 0)  # Tuesday 5:00 PM ET
    assert is_bar_complete(make_bar(TUESDAY, 100), CLOCK_AFTER_TUESDAY_CLOSE, now)


def test_before_the_open_a_candle_for_today_is_in_progress():
    now = utc(2026, 9, 23, 12, 0)  # Wednesday 8:00 AM ET, market opens 9:30
    clock = make_clock(False, utc(2026, 9, 23, 13, 30), utc(2026, 9, 23, 20, 0))
    assert is_bar_complete(make_bar(TUESDAY, 100), clock, now)
    assert not is_bar_complete(make_bar(WEDNESDAY, 100), clock, now)


def test_on_a_weekend_fridays_candle_is_complete():
    now = utc(2026, 9, 26, 16, 0)  # Saturday
    clock = make_clock(False, utc(2026, 9, 28, 13, 30), utc(2026, 9, 28, 20, 0))
    assert is_bar_complete(make_bar(24, 100), clock, now)  # Fri 09-25


def test_a_candle_dated_in_the_future_is_never_trusted():
    now = utc(2026, 9, 22, 21, 0)
    assert not is_bar_complete(make_bar(WEDNESDAY, 100), CLOCK_AFTER_TUESDAY_CLOSE, now)


def test_split_separates_todays_candle():
    bars = [make_bar(MONDAY - 1, 99), make_bar(MONDAY, 100), make_bar(TUESDAY, 101)]
    completed, in_progress = split_completed(bars, CLOCK_DURING_TUESDAY, utc(2026, 9, 22, 18, 0))
    assert [b.close for b in completed] == [99, 100]
    assert in_progress.close == 101


# ---------- is the latest price fresh? ----------

def latest_at(moment):
    return LatestPrice("AAPL", 100.0, moment)


def test_recent_price_while_open_is_fresh():
    now = utc(2026, 9, 22, 18, 0)
    result = check_freshness(latest_at(utc(2026, 9, 22, 17, 59)), CLOCK_DURING_TUESDAY, now, 5)
    assert result.ok


def test_old_price_while_open_is_stale():
    now = utc(2026, 9, 22, 18, 0)
    result = check_freshness(latest_at(utc(2026, 9, 22, 17, 50)), CLOCK_DURING_TUESDAY, now, 5)
    assert not result.ok
    assert "10 min old" in result.reason


def test_missing_price_while_open_is_stale():
    assert not check_freshness(None, CLOCK_DURING_TUESDAY, utc(2026, 9, 22, 18, 0), 5).ok


def test_price_from_the_future_is_stale():
    now = utc(2026, 9, 22, 18, 0)
    result = check_freshness(latest_at(utc(2026, 9, 22, 18, 30)), CLOCK_DURING_TUESDAY, now, 5)
    assert not result.ok and "future" in result.reason


def test_old_price_while_closed_is_fine():
    now = utc(2026, 9, 22, 23, 0)
    result = check_freshness(latest_at(utc(2026, 9, 22, 19, 59)), CLOCK_AFTER_TUESDAY_CLOSE, now, 5)
    assert result.ok and "market closed" in result.reason


# ---------- the whole package ----------

def test_snapshot_during_trading():
    bars = [make_bar(day, 100 + day) for day in range(TUESDAY + 1)]
    provider = FakeMarketData({"AAPL": bars}, {"AAPL": 121.5})  # fake latest trade is 19:59 UTC
    snapshot = take_snapshot(provider, CLOCK_DURING_TUESDAY, "AAPL", 30, 5, now=utc(2026, 9, 22, 19, 59, 30))
    assert snapshot.market_open
    assert snapshot.completed_bars[-1].close == 100 + MONDAY
    assert snapshot.in_progress_bar.close == 100 + TUESDAY
    assert snapshot.freshness.ok
