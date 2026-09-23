"""Tests for the backtest engine, using a scripted "spy" strategy and made-up prices."""

from datetime import date

import pytest

from trader.backtest.engine import run_symbol
from trader.backtest.models import BacktestSettings, Period
from trader.market_data.snapshot import market_date
from trader.strategy.models import Signal, SignalResult
from tests.fakes import make_bar

SETTINGS = BacktestSettings(trade_amount=10_000, slippage_pct=0.05)


def day(n: int) -> date:
    return market_date(make_bar(n, 100).timestamp)


class SpyStrategy:
    """Says whatever the script tells it on given days, and records what it was shown."""

    name = "Spy"

    def __init__(self, script: dict[int, Signal] | None = None) -> None:
        self.script = {day(n): signal for n, signal in (script or {}).items()}
        self.seen: list[tuple[date, date]] = []   # (decision day, newest candle it was shown)

    def evaluate(self, snapshot) -> SignalResult:
        decision_day = market_date(snapshot.taken_at)
        newest = market_date(snapshot.completed_bars[-1].timestamp)
        self.seen.append((decision_day, newest))
        return SignalResult(snapshot.symbol, self.script.get(decision_day, Signal.WATCH), f"scripted on {decision_day}")


def bars(n_days: int, close=lambda d: 100.0):
    """Candles for days 0..n_days-1. open = close - 1 (see make_bar)."""
    return [make_bar(d, close(d)) for d in range(n_days)]


def run(strategy, candles, first=0, last=None):
    last = len(candles) - 1 if last is None else last
    return run_symbol(strategy, candles, Period("test", day(first), day(last)), SETTINGS)


def test_strategy_never_sees_the_future():
    spy = SpyStrategy()
    run(spy, bars(30))
    assert spy.seen, "strategy was never asked"
    for decision_day, newest_candle in spy.seen:
        assert newest_candle == decision_day   # it saw today's finished candle, nothing later


def test_warm_up_days_are_seen_but_not_traded():
    spy = SpyStrategy({3: Signal.BUY})          # day 3 is before the test period
    result = run(spy, bars(20), first=10)
    assert result.trades == []
    assert spy.seen[0][0] == day(10)            # first decision is on the first test day


def test_buy_happens_next_morning_at_open_plus_slippage():
    result = run(SpyStrategy({2: Signal.BUY}), bars(10, close=lambda d: 100.0 + d))
    trade = result.trades[0]
    assert trade.entry_date == day(3)                         # the day AFTER the signal
    assert trade.entry_price == pytest.approx(102.0 * 1.0005)  # day 3 open = 103 - 1 = 102
    assert trade.shares == 97                                  # 10,000 / 102.051 = 97.99, rounded DOWN


def test_sell_happens_next_morning_at_open_minus_slippage():
    result = run(SpyStrategy({2: Signal.BUY, 5: Signal.SELL}), bars(10, close=lambda d: 100.0 + d))
    trade = result.trades[0]
    assert trade.exit_date == day(6)
    assert trade.exit_price == pytest.approx(105.0 * 0.9995)   # day 6 open = 106 - 1 = 105
    assert not trade.still_open
    assert trade.pnl == pytest.approx((105.0 * 0.9995 - 102.0 * 1.0005) * 97)


def test_only_one_position_per_stock():
    result = run(SpyStrategy({1: Signal.BUY, 2: Signal.BUY, 3: Signal.BUY}), bars(10))
    assert len(result.trades) == 1            # still-open position only; no extra buys


def test_sell_without_a_position_does_nothing():
    result = run(SpyStrategy({1: Signal.SELL}), bars(10))
    assert result.trades == []


def test_position_open_at_the_end_is_valued_at_last_close():
    result = run(SpyStrategy({1: Signal.BUY}), bars(10, close=lambda d: 100.0 + d))
    trade = result.trades[-1]
    assert trade.still_open
    assert trade.exit_price == 109.0          # last day's close, no selling slippage
    assert result.equity[-1][1] == pytest.approx(result.starting_capital + trade.pnl)


def test_signal_on_the_last_day_is_not_acted_on():
    result = run(SpyStrategy({9: Signal.BUY}), bars(10))
    assert result.trades == []


def test_buy_is_skipped_when_one_share_costs_more_than_the_trade_amount():
    result = run(SpyStrategy({1: Signal.BUY}), bars(10, close=lambda d: 20_000.0))
    assert result.trades == [] and result.skipped_buys == 1


def test_buy_and_hold_buys_on_day_one_and_never_sells():
    result = run(SpyStrategy(), bars(10, close=lambda d: 100.0 + d))
    shares = 10_000 // (99.0 * 1.0005)                      # day 0 open = 99
    cash_left = 10_000 - shares * 99.0 * 1.0005
    assert result.buy_hold_equity[-1][1] == pytest.approx(cash_left + shares * 109.0)


def test_equity_is_recorded_for_every_test_day():
    result = run(SpyStrategy(), bars(15), first=5)
    assert [d for d, _ in result.equity] == [day(n) for n in range(5, 15)]
    assert all(value == 10_000 for _, value in result.equity)   # never traded: cash unchanged
