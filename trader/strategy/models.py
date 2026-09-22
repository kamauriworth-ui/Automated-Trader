"""The shapes of a strategy's output."""

from dataclasses import dataclass, field
from enum import Enum


class Signal(str, Enum):
    BUY = "BUY"      # conditions favour owning this stock
    SELL = "SELL"    # if we own it, get out (never "bet on a fall" - no short selling)
    WATCH = "WATCH"  # do nothing for now


@dataclass(frozen=True)
class Check:
    """One rule the strategy tested, whether it passed, and the numbers behind it."""

    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class SignalResult:
    symbol: str
    signal: Signal
    summary: str                                  # one plain-English sentence
    price: float | None = None                    # last completed close the decision used
    checks: list[Check] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)  # extra info that didn't affect the decision
