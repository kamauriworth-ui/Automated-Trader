"""Read-only connection to an Alpaca PAPER trading account.

One of only two files that import Alpaca's library (the other is
market_data/alpaca_data.py, which can only read prices, never trade).

Safety layers applied here (on top of the startup checks in safety.py):
  1. The Alpaca client is created with paper=True.
  2. We then check which address the client will really use.
  3. We ask Alpaca which account we reached and require a paper account number.
A broker object is only handed to the rest of the app after all three pass.
"""

import logging
from collections.abc import Callable
from typing import TypeVar

import requests
from alpaca.common.exceptions import APIError
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import AssetClass, AssetStatus
from alpaca.trading.requests import GetAssetsRequest

from trader import safety
from trader.broker.models import AccountSummary, AssetInfo, MarketClock, Position
from trader.config import Settings
from trader.errors import BrokerError, ConfigError

log = logging.getLogger(__name__)
T = TypeVar("T")


class AlpacaPaperBroker:
    def __init__(self, client: TradingClient) -> None:
        # Safety layer 2: check the address the library will actually use.
        safety.require_paper_client_url(client._base_url)
        self._client = client

    @classmethod
    def connect(cls, settings: Settings) -> "AlpacaPaperBroker":
        """Create the client, then verify we really reached a paper account."""
        if not settings.has_api_keys:
            raise ConfigError(
                "Alpaca paper API keys are missing. Set ALPACA_API_KEY and ALPACA_SECRET_KEY "
                "(as Codespaces secrets or in .env)."
            )
        # Safety layer 1: paper=True tells the library to use the paper address.
        client = TradingClient(settings.alpaca_api_key, settings.alpaca_secret_key, paper=True)
        broker = cls(client)
        # Safety layer 3: get_account() refuses anything that isn't a paper account.
        account = broker.get_account()
        log.info("Connected to Alpaca PAPER account %s", mask_account_number(account.account_number))
        return broker

    # ----- read-only methods (the Broker "checklist" from base.py) -----

    def get_account(self) -> AccountSummary:
        raw = self._call("get account", self._client.get_account)
        safety.require_paper_account(raw.account_number)
        return AccountSummary(
            account_number=raw.account_number,
            status=_enum_text(raw.status),
            equity=_money(raw.equity),
            last_equity=_money(raw.last_equity),
            cash=_money(raw.cash),
            buying_power=_money(raw.buying_power),
            trading_blocked=bool(raw.trading_blocked or raw.account_blocked),
        )

    def get_positions(self) -> list[Position]:
        raw_positions = self._call("get positions", self._client.get_all_positions)
        return [
            Position(
                symbol=p.symbol,
                quantity=_money(p.qty),
                average_entry_price=_money(p.avg_entry_price),
                current_price=_money(p.current_price),
                market_value=_money(p.market_value),
                unrealized_pl=_money(p.unrealized_pl),
                unrealized_pl_percent=_money(p.unrealized_plpc) * 100,
            )
            for p in raw_positions
        ]

    def get_market_clock(self) -> MarketClock:
        raw = self._call("get market clock", self._client.get_clock)
        return MarketClock(is_open=raw.is_open, next_open=raw.next_open, next_close=raw.next_close)

    def get_asset(self, symbol: str) -> AssetInfo | None:
        try:
            raw = self._client.get_asset(symbol)
        except APIError as exc:
            if exc.status_code == 404:  # "not found": Alpaca doesn't know this symbol
                return None
            raise translate_alpaca_error("look up " + symbol, exc) from exc
        except requests.RequestException as exc:
            raise translate_alpaca_error("look up " + symbol, exc) from exc
        return AssetInfo(symbol=raw.symbol, name=raw.name or "", tradable=bool(raw.tradable))

    def search_assets(self, text: str) -> list[AssetInfo]:
        request = GetAssetsRequest(status=AssetStatus.ACTIVE, asset_class=AssetClass.US_EQUITY)
        everything = self._call("list assets", lambda: self._client.get_all_assets(request))
        needle = text.strip().lower()
        matches = [
            AssetInfo(symbol=a.symbol, name=a.name or "", tradable=bool(a.tradable))
            for a in everything
            if needle in a.symbol.lower() or needle in (a.name or "").lower()
        ]
        return sorted(matches, key=lambda a: a.symbol)

    # ----- helpers -----

    def _call(self, what: str, fn: Callable[[], T]) -> T:
        """Run one Alpaca request, turning its errors into a friendly BrokerError."""
        try:
            return fn()
        except (APIError, requests.RequestException) as exc:
            raise translate_alpaca_error(what, exc) from exc


def translate_alpaca_error(what: str, exc: Exception) -> BrokerError:
    if isinstance(exc, APIError) and exc.status_code in (401, 403):
        return BrokerError(
            f"Alpaca rejected the API keys while trying to {what}. Check that you copied the "
            "PAPER key ID and secret correctly, or generate new paper keys."
        )
    if isinstance(exc, requests.ConnectionError | requests.Timeout):
        return BrokerError(f"Could not reach Alpaca while trying to {what}. Check the internet connection.")
    return BrokerError(f"Alpaca request failed while trying to {what}: {exc}")


def _money(value: object) -> float:
    """Alpaca sends numbers as text (e.g. "100000.00"). Convert to a number."""
    return float(value) if value not in (None, "") else 0.0


def _enum_text(value: object) -> str:
    """Alpaca uses 'enums' (fixed lists of values). Get the plain text out."""
    return str(getattr(value, "value", value))


def mask_account_number(number: str) -> str:
    """Show only enough of the account number to recognise it: PA…1234."""
    return f"{number[:2]}…{number[-4:]}" if len(number) > 6 else number
