"""Tests for the indicator calculations. Every expected number can be checked by hand."""

import pytest

from trader.strategy import indicators
from tests.fakes import make_bar


def test_simple_moving_average_uses_the_last_n_values():
    assert indicators.simple_moving_average([10, 11, 12, 13], 2) == 12.5
    assert indicators.simple_moving_average([10, 11, 12, 13], 4) == 11.5


def test_percent_change():
    assert indicators.percent_change([100, 999, 105], 2) == pytest.approx(5.0)
    assert indicators.percent_change([200, 150], 1) == pytest.approx(-25.0)


def test_volume_ratio_compares_last_day_with_the_days_before_it():
    bars = [make_bar(d, 100, volume=1_000) for d in range(3)] + [make_bar(3, 100, volume=2_000)]
    assert indicators.volume_ratio(bars, 3) == pytest.approx(2.0)


def test_true_range_includes_overnight_gaps():
    # make_bar: high = close + 2, low = close - 2
    normal_day = make_bar(1, 100)                         # high 102, low 98
    assert indicators.true_range(normal_day, previous_close=100) == 4
    assert indicators.true_range(normal_day, previous_close=90) == 12   # gap up from 90 to 102


def test_average_true_range():
    bars = [make_bar(d, 100) for d in range(4)]            # every day travels 4 (98 to 102)
    assert indicators.average_true_range(bars, 3) == pytest.approx(4.0)


@pytest.mark.parametrize(
    "call",
    [
        lambda: indicators.simple_moving_average([1, 2], 3),
        lambda: indicators.percent_change([1, 2], 2),
        lambda: indicators.volume_ratio([make_bar(0, 100)], 1),
        lambda: indicators.average_true_range([make_bar(0, 100)], 1),
    ],
)
def test_too_little_data_is_an_error_not_a_wrong_answer(call):
    with pytest.raises(ValueError):
        call()
