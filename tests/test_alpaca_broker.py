"""Tests for the Alpaca paper broker's safety checks, using a fake Alpaca client."""

import pytest

from trader.broker.alpaca_paper import AlpacaPaperBroker, mask_account_number
from trader.config import build_settings
from trader.errors import ConfigError, SafetyError
from tests.fakes import FakeAlpacaClient

ENV = {"PAPER_TRADING": "TRUE", "ALPACA_BASE_URL": "https://paper-api.alpaca.markets"}
FILE = {"watchlist": ["AAPL"]}


def test_paper_account_is_read_and_converted():
    account = AlpacaPaperBroker(FakeAlpacaClient()).get_account()
    assert account.equity == 100500.25
    assert account.status == "ACTIVE"
    assert account.change_today == pytest.approx(500.25)


def test_client_pointed_at_live_url_is_refused():
    with pytest.raises(SafetyError):
        AlpacaPaperBroker(FakeAlpacaClient(base_url="https://api.alpaca.markets"))


def test_non_paper_account_is_refused():
    broker = AlpacaPaperBroker(FakeAlpacaClient(account_number="123456789"))
    with pytest.raises(SafetyError):
        broker.get_account()


def test_connect_without_keys_is_a_config_error():
    settings = build_settings(ENV, FILE)
    with pytest.raises(ConfigError):
        AlpacaPaperBroker.connect(settings)


def test_account_number_is_masked():
    assert mask_account_number("PA3ABCDE1234") == "PA…1234"


def test_real_alpaca_client_passes_the_url_check():
    """Uses Alpaca's real client object (creating it needs no internet)."""
    from alpaca.trading.client import TradingClient

    AlpacaPaperBroker(TradingClient("PKTEST", "secret", paper=True))  # should not raise


def test_real_alpaca_live_client_is_refused():
    from alpaca.trading.client import TradingClient

    with pytest.raises(SafetyError):
        AlpacaPaperBroker(TradingClient("PKTEST", "secret", paper=False))
