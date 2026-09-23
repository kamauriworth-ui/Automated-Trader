"""Price data from Alpaca's market-data service.

This client can only READ prices. Alpaca's market-data service has no ability
to place orders at all, so it cannot touch money, paper or real.
"""

from datetime import datetime, timedelta, timezone

import requests
from alpaca.common.exceptions import APIError
from alpaca.data.enums import Adjustment, DataFeed
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockLatestTradeRequest
from alpaca.data.timeframe import TimeFrame

from trader.broker.alpaca_paper import translate_alpaca_error
from trader.config import Settings
from trader.errors import ConfigError, DataFeedNotPermittedError
from trader.market_data.models import Bar, LatestPrice


class AlpacaMarketData:
    def __init__(self, client: StockHistoricalDataClient, feed: str, adjustment: str) -> None:
        self._client = client
        self._feed = DataFeed(feed)
        self._adjustment = Adjustment(adjustment)

    @classmethod
    def from_settings(cls, settings: Settings) -> "AlpacaMarketData":
        if not settings.has_api_keys:
            raise ConfigError("Alpaca paper API keys are missing; they are needed for price data too.")
        client = StockHistoricalDataClient(settings.alpaca_api_key, settings.alpaca_secret_key)
        return cls(client, settings.market_data_feed, settings.price_adjustment)

    def get_daily_bars(self, symbol: str, days: int) -> list[Bar]:
        request = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Day,
            start=datetime.now(timezone.utc) - timedelta(days=days),
            feed=self._feed,
            adjustment=self._adjustment,
        )
        try:
            bar_set = self._client.get_stock_bars(request)
        except (APIError, requests.RequestException) as exc:
            raise translate_alpaca_error(f"get price history for {symbol}", exc) from exc
        return [self._to_bar(symbol, b) for b in bar_set.data.get(symbol, [])]

    def get_daily_bars_range(self, symbol: str, start: datetime, end: datetime, feed: str) -> list[Bar]:
        """Daily candles between two moments, from a specific feed (used by backtesting).

        Raises DataFeedNotPermittedError if the account's data plan refuses this feed,
        so the caller can fall back to another one.
        """
        request = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Day,
            start=start,
            end=end,
            feed=DataFeed(feed),
            adjustment=self._adjustment,
        )
        try:
            bar_set = self._client.get_stock_bars(request)
        except APIError as exc:
            if exc.status_code == 403 and "subscription" in str(exc).lower():
                raise DataFeedNotPermittedError(
                    f"Your Alpaca data plan does not allow the '{feed}' feed for this request."
                ) from exc
            raise translate_alpaca_error(f"get price history for {symbol}", exc) from exc
        except requests.RequestException as exc:
            raise translate_alpaca_error(f"get price history for {symbol}", exc) from exc
        return [self._to_bar(symbol, b) for b in bar_set.data.get(symbol, [])]

    @staticmethod
    def _to_bar(symbol: str, b) -> Bar:
        return Bar(
            symbol=symbol,
            timestamp=b.timestamp,
            open=float(b.open),
            high=float(b.high),
            low=float(b.low),
            close=float(b.close),
            volume=float(b.volume),
        )

    def get_latest_price(self, symbol: str) -> LatestPrice | None:
        request = StockLatestTradeRequest(symbol_or_symbols=symbol, feed=self._feed)
        try:
            trades = self._client.get_stock_latest_trade(request)
        except (APIError, requests.RequestException) as exc:
            raise translate_alpaca_error(f"get the latest price for {symbol}", exc) from exc
        trade = trades.get(symbol)
        if trade is None:
            return None
        return LatestPrice(symbol=symbol, price=float(trade.price), timestamp=trade.timestamp)
