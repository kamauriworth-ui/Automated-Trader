"""Tests for the Trend/Momentum strategy, using made-up price patterns."""

from datetime import timezone, datetime

from trader.market_data.snapshot import Freshness, MarketSnapshot
from trader.strategy.models import Signal
from trader.strategy.trend_momentum import TrendMomentumParams, TrendMomentumStrategy, compare_words
from tests.fakes import make_bar

NOW = datetime(2026, 12, 1, tzinfo=timezone.utc)
FRESH = Freshness(True, "test data")


def snapshot(bars, freshness=FRESH):
    return MarketSnapshot("TEST", bars, None, None, freshness, False, NOW)


def series(closes, last_volume=1_000_000):
    """Candles with the given closes; every day has 1M volume except the last."""
    bars = [make_bar(day, close) for day, close in enumerate(closes)]
    bars[-1] = make_bar(len(closes) - 1, closes[-1], volume=last_volume)
    return bars


RISING = [100 + day for day in range(60)]          # up $1 every day
FALLING = [200 - day for day in range(60)]         # down $1 every day

strategy = TrendMomentumStrategy()


def test_steady_rise_with_strong_volume_is_buy():
    result = strategy.evaluate(snapshot(series(RISING, last_volume=2_000_000)))
    assert result.signal == Signal.BUY
    assert all(check.passed for check in result.checks)
    assert result.price == 159


def test_steady_rise_without_volume_is_watch():
    result = strategy.evaluate(snapshot(series(RISING, last_volume=500_000)))
    assert result.signal == Signal.WATCH
    assert "volume" in result.summary


def test_steady_fall_is_sell():
    result = strategy.evaluate(snapshot(series(FALLING, last_volume=2_000_000)))
    assert result.signal == Signal.SELL
    assert "below the 50-day average" in result.summary


def test_sharp_drop_below_long_average_is_sell_even_in_an_uptrend():
    closes = RISING[:-1] + [120]    # a long rise, then one day crashes to 120
    result = strategy.evaluate(snapshot(series(closes)))
    assert result.signal == Signal.SELL


def test_rise_that_stalled_has_no_momentum_and_is_watch():
    closes = RISING[:50] + [150] * 10 + [149]   # rose, then went flat and dipped slightly
    result = strategy.evaluate(snapshot(series(closes, last_volume=2_000_000)))
    assert result.signal == Signal.WATCH
    assert "momentum" in result.summary


def test_stale_data_means_no_decision():
    stale = Freshness(False, "latest trade is 30 min old")
    result = strategy.evaluate(snapshot(series(RISING, last_volume=2_000_000), stale))
    assert result.signal == Signal.WATCH
    assert "stale" in result.summary
    assert result.checks == []


def test_too_little_history_means_no_decision():
    result = strategy.evaluate(snapshot(series(RISING[:30])))
    assert result.signal == Signal.WATCH
    assert "need 50 completed days" in result.summary


def test_settings_change_the_rules():
    shorter = TrendMomentumStrategy(TrendMomentumParams(short_ma_days=5, long_ma_days=10))
    result = shorter.evaluate(snapshot(series(RISING[:25], last_volume=2_000_000)))
    assert result.signal == Signal.BUY   # 25 days is enough history with a 10-day long average


def test_volatility_is_reported_but_does_not_change_the_signal():
    result = strategy.evaluate(snapshot(series(RISING, last_volume=2_000_000)))
    assert any("ATR 14" in note for note in result.notes)


def test_comparison_wording_matches_what_is_displayed():
    assert compare_words(301.0, 300.0) == "above"
    assert compare_words(299.0, 300.0) == "below"
    assert compare_words(300.996, 301.0) == "level with"   # both display as $301.00


def test_volume_rule_can_be_loosened_or_switched_off():
    weak_volume = series(RISING, last_volume=500_000)   # 0.5x average
    looser = TrendMomentumStrategy(TrendMomentumParams(volume_min_ratio=0.5))
    off = TrendMomentumStrategy(TrendMomentumParams(volume_min_ratio=0))
    assert strategy.evaluate(snapshot(weak_volume)).signal == Signal.WATCH
    assert looser.evaluate(snapshot(weak_volume)).signal == Signal.BUY
    result = off.evaluate(snapshot(weak_volume))
    assert result.signal == Signal.BUY
    assert any("rule OFF" in c.detail for c in result.checks)


def test_describe_states_the_rules_used():
    assert TrendMomentumStrategy().describe() == "20/50-day averages, 10-day momentum, volume >= 1x avg"
    assert "volume rule OFF" in TrendMomentumStrategy(TrendMomentumParams(volume_min_ratio=0)).describe()
