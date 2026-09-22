"""Tests for the paper-trading safety checks.

Each test sets up one situation and checks that the app either accepts it
or refuses with a SafetyError.
"""

import pytest

from trader import safety
from trader.errors import SafetyError

GOOD_ENV = {
    "PAPER_TRADING": "TRUE",
    "ALPACA_BASE_URL": "https://paper-api.alpaca.markets",
}


def test_good_paper_setup_passes():
    safety.run_startup_safety_checks(GOOD_ENV)  # should not raise


@pytest.mark.parametrize("value", [None, "", "FALSE", "false", "yes", "1", "maybe", "TRUE!"])
def test_paper_flag_must_be_exactly_true(value):
    with pytest.raises(SafetyError):
        safety.require_paper_trading_flag(value)


@pytest.mark.parametrize("value", ["TRUE", "true", " True "])
def test_paper_flag_accepts_true(value):
    safety.require_paper_trading_flag(value)


@pytest.mark.parametrize(
    "url",
    [
        None,
        "",
        "https://api.alpaca.markets",               # the LIVE endpoint
        "http://paper-api.alpaca.markets",          # not https
        "https://paper-api.alpaca.markets.evil.com",
        "https://example.com",
    ],
)
def test_non_paper_endpoints_are_rejected(url):
    with pytest.raises(SafetyError):
        safety.require_paper_endpoint(url)


def test_paper_endpoint_trailing_slash_is_cleaned():
    assert safety.require_paper_endpoint("https://paper-api.alpaca.markets/") == safety.PAPER_API_URL


def test_live_looking_api_key_is_rejected():
    with pytest.raises(SafetyError):
        safety.require_paper_api_key("AKXXXXXXXXXXXXXXXX")


def test_paper_api_key_and_missing_key_are_allowed():
    safety.require_paper_api_key("PKXXXXXXXXXXXXXXXX")
    safety.require_paper_api_key(None)
    safety.require_paper_api_key("")


def test_conflicting_alpaca_url_variable_is_rejected():
    env = {**GOOD_ENV, "APCA_API_BASE_URL": "https://api.alpaca.markets"}
    with pytest.raises(SafetyError):
        safety.run_startup_safety_checks(env)


def test_paper_account_number_is_accepted():
    safety.require_paper_account("PA3ABCDEFGH")


@pytest.mark.parametrize("number", [None, "", "123456789", "LIVE123", "pa3abc"])
def test_non_paper_account_numbers_are_rejected(number):
    with pytest.raises(SafetyError):
        safety.require_paper_account(number)


def test_client_pointed_at_live_url_is_rejected():
    with pytest.raises(SafetyError):
        safety.require_paper_client_url("https://api.alpaca.markets")
