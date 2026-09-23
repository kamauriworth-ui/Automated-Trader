"""Tests for the backtest measurements. Every expected number can be checked by hand."""

from datetime import date

import pytest

from trader.backtest import metrics
from trader.backtest.models import Trade


def trade(entry: float, exit_: float, shares: int = 10, days: int = 5) -> Trade:
    return Trade("TEST", date(2024, 1, 1), entry, date(2024, 1, 1 + days), exit_, shares, "in", "out")


def test_trade_stats():
    trades = [trade(100, 110), trade(100, 120), trade(100, 95), trade(100, 90)]
    s = metrics.trade_stats(trades)
    assert (s.count, s.wins, s.losses) == (4, 2, 2)
    assert s.win_rate_pct == 50
    assert s.avg_gain_pct == pytest.approx(15.0)     # (10 + 20) / 2
    assert s.avg_loss_pct == pytest.approx(-7.5)     # (-5 + -10) / 2
    assert s.risk_reward == pytest.approx(2.0)       # 15 / 7.5
    assert s.total_pnl == pytest.approx(150.0)       # (10 + 20 - 5 - 10) x 10 shares
    assert s.avg_holding_days == 5


def test_trade_stats_with_no_trades():
    s = metrics.trade_stats([])
    assert s.count == 0 and s.win_rate_pct is None and s.risk_reward is None and s.total_pnl == 0


def test_all_winners_has_no_risk_reward():
    assert metrics.trade_stats([trade(100, 110)]).risk_reward is None


def test_max_drawdown():
    assert metrics.max_drawdown_pct([100, 120, 90, 130]) == pytest.approx(-25.0)
    assert metrics.max_drawdown_pct([100, 110, 120]) == 0.0


def test_total_return():
    assert metrics.total_return_pct([100, 50, 150]) == pytest.approx(50.0)
    assert metrics.total_return_pct([100]) is None


def test_combine_curves_fills_missing_days_with_last_known_value():
    a = [(date(2024, 1, 1), 100.0), (date(2024, 1, 2), 110.0), (date(2024, 1, 3), 120.0)]
    b = [(date(2024, 1, 1), 50.0), (date(2024, 1, 3), 70.0)]    # no value on the 2nd
    assert metrics.combine_curves([a, b]) == [
        (date(2024, 1, 1), 150.0),
        (date(2024, 1, 2), 160.0),     # b's 50 carried forward
        (date(2024, 1, 3), 190.0),
    ]


def test_yearly_returns():
    curve = [(date(2022, 1, 3), 100.0), (date(2022, 12, 30), 110.0), (date(2023, 6, 1), 99.0), (date(2023, 12, 29), 121.0)]
    assert metrics.yearly_returns(curve) == pytest.approx({2022: 10.0, 2023: 10.0})
