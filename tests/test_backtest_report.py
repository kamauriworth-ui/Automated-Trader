"""Tests for the backtest report and CSV file."""

import csv
from datetime import date

from trader.backtest.models import BacktestResult, BacktestSettings, Period, SymbolResult, Trade
from trader.backtest.report import build_backtest_report, save_trades_csv


def make_trade(n: int, entry: float, exit_: float, still_open: bool = False) -> Trade:
    return Trade("AAPL", date(2024, 1, n), entry, date(2024, 2, n), exit_, 10, "in", "Trend is broken: close is below the 50-day average", still_open)


def make_result(trades, period_name="development", feed="sip") -> BacktestResult:
    days = [date(2024, 1, 1), date(2024, 6, 1), date(2024, 12, 31)]
    symbol = SymbolResult(
        "AAPL", 10_000, trades,
        equity=list(zip(days, [10_000, 11_000, 10_500])),
        buy_hold_equity=list(zip(days, [10_000, 12_000, 13_000])),
        days_holding=2,
    )
    return BacktestResult("Trend/Momentum", Period(period_name, date(2024, 1, 1), date(2024, 12, 31)), feed, BacktestSettings(), [symbol])


def test_report_sections_and_cautions():
    text = build_backtest_report(make_result([make_trade(2, 100, 110), make_trade(3, 100, 95)]))
    for heading in ("STRATEGY RESULTS", "COMPARED WITH BUY & HOLD", "BY YEAR", "TRADES", "CAUTIONS"):
        assert heading in text
    assert "SEALED" in text
    assert "Only 2 trades" in text                    # small-sample warning
    assert "earned LESS than simply holding" in text  # +5% vs +30% buy & hold
    assert "sold because: close is below the 50-day average" in text


def test_many_trades_show_only_best_and_worst_by_default():
    trades = [make_trade(n, 100, 100 + n) for n in range(1, 11)]
    text = build_backtest_report(make_result(trades))
    assert "BEST 3 TRADES (of 10)" in text and "WORST 3 TRADES" in text
    assert text.count("sold because") == 6
    assert build_backtest_report(make_result(trades), show_all_trades=True).count("sold because") == 10


def test_open_position_is_labelled_as_status_not_sold():
    text = build_backtest_report(make_result([make_trade(2, 100, 104, still_open=True)]))
    assert "status:" in text and "(open)" in text


def test_holdout_and_iex_notes():
    text = build_backtest_report(make_result([], period_name="holdout", feed="iex"))
    assert "FINAL EXAM" in text
    assert "IEX only" in text


def test_trades_are_saved_to_csv(tmp_path):
    path = save_trades_csv(make_result([make_trade(2, 100, 110)]), tmp_path)
    rows = list(csv.DictReader(path.open()))
    assert path.name == "backtest_development_trades.csv"
    assert rows[0]["symbol"] == "AAPL" and rows[0]["return_pct"] == "10.00"
