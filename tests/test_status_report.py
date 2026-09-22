"""Tests for the status report, using a fake broker (no internet needed)."""

from trader.broker.models import Position
from trader.status_report import build_status_report, money, signed_money
from tests.fakes import FakeBroker


def test_money_formatting():
    assert money(1234.5) == "$1,234.50"
    assert money(-20) == "-$20.00"
    assert signed_money(5) == "+$5.00"


def test_report_shows_paper_warning_and_account_values():
    report = build_status_report(FakeBroker(), ("AAPL",))
    assert "SIMULATED MONEY, NOT REAL" in report
    assert "PA…CCT1 (paper)" in report
    assert "$100,500.25" in report
    assert "+$500.25" in report


def test_report_shows_market_closed_in_eastern_time():
    report = build_status_report(FakeBroker(market_open=False), ("AAPL",))
    assert "CLOSED  (next open Wed 2026-09-23 09:30 ET)" in report


def test_report_flags_unknown_watchlist_symbol():
    report = build_status_report(FakeBroker(), ("AAPL", "ZZZZ"))
    assert "Apple Inc." in report
    assert "ZZZZ   NOT FOUND" in report


def test_report_lists_positions():
    position = Position("NVDA", 10, 100.0, 110.0, 1100.0, 100.0, 10.0)
    report = build_status_report(FakeBroker(positions=[position]), ("AAPL",))
    assert "Open positions (1)" in report
    assert "NVDA" in report and "+$100.00 (+10.00%)" in report
