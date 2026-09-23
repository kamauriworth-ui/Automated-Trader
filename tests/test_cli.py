"""Tests for the command-line options (no internet needed: nothing is run, only parsed)."""

import pytest

from trader.__main__ import apply_backtest_overrides, parse_args
from trader.config import build_settings

SETTINGS = build_settings(
    {"PAPER_TRADING": "TRUE", "ALPACA_BASE_URL": "https://paper-api.alpaca.markets"}, {"watchlist": ["AAPL"]}
)


def test_backtest_experiment_options_override_settings_for_one_run():
    args = parse_args(["backtest", "--reinvest", "--volume-min", "0", "--slippage", "0.1"])
    changed = apply_backtest_overrides(SETTINGS, args)
    assert changed.backtest.reinvest is True
    assert changed.backtest.slippage_pct == 0.1
    assert changed.strategy.volume_min_ratio == 0
    assert SETTINGS.backtest.reinvest is False     # the original settings are untouched


def test_no_options_means_no_changes():
    assert apply_backtest_overrides(SETTINGS, parse_args(["backtest"])) == SETTINGS


@pytest.mark.parametrize("bad", [["--slippage", "5"], ["--volume-min", "-1"], ["--volume-min", "lots"]])
def test_out_of_range_options_are_refused(bad):
    with pytest.raises(SystemExit):
        parse_args(["backtest", *bad])
