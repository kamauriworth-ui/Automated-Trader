"""Data shapes for backtesting. (No imports from the rest of the app, on purpose.)"""

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class BacktestSettings:
    """From the `backtest:` section of settings.yaml."""

    years: int = 5                  # how far back the test goes
    holdout_years: int = 1          # the most recent part, kept sealed for a final check
    trade_amount: float = 10_000.0  # dollars used per trade
    slippage_pct: float = 0.05      # assumed price penalty per buy and per sell, in percent
    feed: str = "sip"               # preferred data feed; falls back to IEX if not allowed


@dataclass(frozen=True)
class Period:
    name: str
    start: date
    end: date


@dataclass(frozen=True)
class Trade:
    symbol: str
    entry_date: date
    entry_price: float     # what we paid per share, including slippage
    exit_date: date
    exit_price: float      # what we received per share, including slippage
    shares: int
    entry_reason: str
    exit_reason: str
    still_open: bool = False   # True = never sold; valued at the last close of the test

    @property
    def pnl(self) -> float:
        return (self.exit_price - self.entry_price) * self.shares

    @property
    def return_pct(self) -> float:
        return (self.exit_price - self.entry_price) / self.entry_price * 100

    @property
    def holding_days(self) -> int:
        return (self.exit_date - self.entry_date).days


@dataclass
class SymbolResult:
    symbol: str
    starting_capital: float
    trades: list[Trade] = field(default_factory=list)
    equity: list[tuple[date, float]] = field(default_factory=list)          # strategy value each day
    buy_hold_equity: list[tuple[date, float]] = field(default_factory=list)  # buy on day 1, never sell
    days_holding: int = 0
    skipped_buys: int = 0     # BUY signals we couldn't act on (e.g. one share cost more than the trade amount)


@dataclass
class BacktestResult:
    strategy_name: str
    period: Period
    feed_used: str
    settings: BacktestSettings
    symbols: list[SymbolResult]
