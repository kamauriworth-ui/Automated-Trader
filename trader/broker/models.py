"""Plain data containers for broker information.

These are *our* shapes, not Alpaca's. Alpaca's library returns its own objects;
`alpaca_paper.py` translates them into these. If we ever switch brokers, only
that translation changes — everything that reads these classes stays the same.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AccountSummary:
    account_number: str
    status: str
    equity: float           # total value: cash + value of everything you own
    last_equity: float      # equity at the end of the previous trading day
    cash: float
    buying_power: float     # how much you could spend on new purchases right now
    trading_blocked: bool

    @property
    def change_today(self) -> float:
        return self.equity - self.last_equity


@dataclass(frozen=True)
class Position:
    """A stock you currently own (a "position")."""

    symbol: str
    quantity: float
    average_entry_price: float  # average price you paid per share
    current_price: float
    market_value: float         # quantity x current price
    unrealized_pl: float        # profit/loss if you sold right now (not locked in yet)
    unrealized_pl_percent: float


@dataclass(frozen=True)
class MarketClock:
    is_open: bool
    next_open: datetime
    next_close: datetime


@dataclass(frozen=True)
class AssetInfo:
    """Basic facts about one stock symbol."""

    symbol: str
    name: str
    tradable: bool
