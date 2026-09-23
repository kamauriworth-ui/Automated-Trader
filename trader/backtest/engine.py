"""The backtest engine: replays history one trading day at a time.

For each day D in the test period:
  1. MORNING: carry out any order decided yesterday, at today's OPEN price
     (plus slippage). You can't trade at the price that triggered a decision,
     because you only learn that price after the market has closed.
  2. EVENING: value the holdings at today's CLOSE.
  3. After the close: show the strategy candles up to and including day D -
     never anything later - and note what it wants to do tomorrow.

Rules for now (Phase 6 will replace them with proper risk management):
  - A fixed dollar amount per trade, whole shares only.
  - At most one position per stock.
  - Exit only when the strategy says SELL. No stop-loss yet.
  - Each stock is tested separately, with its own starting money.
"""

import math

from trader.backtest.models import BacktestResult, BacktestSettings, Period, SymbolResult, Trade
from trader.market_data.models import Bar
from trader.market_data.snapshot import Freshness, MarketSnapshot, market_date
from trader.strategy.base import Strategy
from trader.strategy.models import Signal

HISTORICAL = Freshness(True, "historical data (backtest)")


def run_symbol(strategy: Strategy, bars: list[Bar], period: Period, settings: BacktestSettings) -> SymbolResult:
    """Backtest one stock. `bars` must be completed candles, oldest first, including warm-up days."""
    symbol = bars[0].symbol if bars else "?"
    result = SymbolResult(symbol=symbol, starting_capital=settings.trade_amount)
    slip = settings.slippage_pct / 100

    in_period = [i for i, b in enumerate(bars) if period.start <= market_date(b.timestamp) <= period.end]
    if not in_period:
        return result

    cash = settings.trade_amount
    shares = 0
    entry: tuple | None = None          # (date, price, reason) of the open position
    pending: tuple | None = None        # (Signal, reason) decided yesterday, to do this morning

    # Buy-and-hold comparison: buy on the first morning with the same money and slippage, never sell.
    first = bars[in_period[0]]
    hold_price = first.open * (1 + slip)
    hold_shares = math.floor(settings.trade_amount / hold_price)
    hold_cash = settings.trade_amount - hold_shares * hold_price

    for position, i in enumerate(in_period):
        bar = bars[i]
        today = market_date(bar.timestamp)

        # 1. MORNING - carry out yesterday's decision at today's open.
        if pending is not None:
            signal, reason = pending
            if signal == Signal.BUY and shares == 0:
                price = bar.open * (1 + slip)
                quantity = math.floor(min(settings.trade_amount, cash) / price)
                if quantity > 0:
                    cash -= quantity * price
                    shares = quantity
                    entry = (today, price, reason)
                else:
                    result.skipped_buys += 1
            elif signal == Signal.SELL and shares > 0:
                price = bar.open * (1 - slip)
                cash += shares * price
                result.trades.append(Trade(symbol, entry[0], entry[1], today, price, shares, entry[2], reason))
                shares, entry = 0, None
            pending = None

        # 2. EVENING - value everything at today's close.
        result.equity.append((today, cash + shares * bar.close))
        result.buy_hold_equity.append((today, hold_cash + hold_shares * bar.close))
        if shares > 0:
            result.days_holding += 1

        # 3. AFTER THE CLOSE - ask the strategy, showing it history up to today ONLY.
        is_last_day = position == len(in_period) - 1
        if not is_last_day:
            snapshot = MarketSnapshot(symbol, bars[: i + 1], None, None, HISTORICAL, False, bar.timestamp)
            decision = strategy.evaluate(snapshot)
            if decision.signal == Signal.BUY and shares == 0:
                pending = (Signal.BUY, decision.summary)
            elif decision.signal == Signal.SELL and shares > 0:
                pending = (Signal.SELL, decision.summary)

    # A position still open when the test ends is valued at the last close (not sold).
    if shares > 0:
        last = bars[in_period[-1]]
        result.trades.append(
            Trade(symbol, entry[0], entry[1], market_date(last.timestamp), last.close, shares,
                  entry[2], "still open when the test ended (valued at last close)", still_open=True)
        )
    return result


def run_backtest(
    strategy: Strategy,
    bars_by_symbol: dict[str, list[Bar]],
    period: Period,
    settings: BacktestSettings,
    feed_used: str,
) -> BacktestResult:
    results = [run_symbol(strategy, bars, period, settings) for bars in bars_by_symbol.values() if bars]
    return BacktestResult(strategy.name, period, feed_used, settings, results)
