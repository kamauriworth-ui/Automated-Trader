"""Tests for checking and cleaning price data (no internet needed)."""

import pytest

from trader.market_data.processing import clean_bars, problems_with_bar, summarize_bars
from tests.fakes import make_bar


def test_good_bar_has_no_problems():
    assert problems_with_bar(make_bar(0, 100)) == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"low": 0},                             # zero price
        {"high": 90, "low": 110},               # high below low
        {"high": 99.5},                         # close (100) above the high
        {"open": 50},                           # open below the low
        {"volume": -1},                         # negative volume
    ],
)
def test_impossible_bars_are_detected(overrides):
    assert problems_with_bar(make_bar(0, 100, **overrides)) != []


def test_clean_bars_sorts_oldest_first():
    bars = [make_bar(2, 102), make_bar(0, 100), make_bar(1, 101)]
    assert [b.close for b in clean_bars(bars)] == [100, 101, 102]


def test_clean_bars_drops_duplicates_and_bad_bars():
    bars = [make_bar(0, 100), make_bar(0, 100), make_bar(1, 101, volume=-5), make_bar(2, 102)]
    assert [b.close for b in clean_bars(bars)] == [100, 102]


def test_summary_numbers():
    bars = [make_bar(0, 100), make_bar(1, 110)]
    summary = summarize_bars(bars)
    assert summary.count == 2
    assert summary.last_close == 110
    assert summary.change_from_previous_close_pct == pytest.approx(10.0)
    assert summary.period_high == 112   # 110 + 2
    assert summary.period_low == 98     # 100 - 2


def test_summary_of_one_bar_has_no_change():
    assert summarize_bars([make_bar(0, 100)]).change_from_previous_close_pct is None


def test_summary_of_nothing_is_none():
    assert summarize_bars([]) is None
