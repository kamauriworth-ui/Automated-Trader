"""Builds the human-readable status report printed by `python -m trader`.

It only uses the Broker "checklist" from broker/base.py, so it works with the
real Alpaca broker and with the fake broker in our tests.
"""

from zoneinfo import ZoneInfo

from trader.broker.alpaca_paper import mask_account_number
from trader.broker.base import Broker
from trader.broker.models import MarketClock
from trader.formatting import money, signed_money

MARKET_TIMEZONE = ZoneInfo("America/New_York")  # US stock market hours are in Eastern Time
LINE = "=" * 62


def describe_market(clock: MarketClock) -> str:
    if clock.is_open:
        closes = clock.next_close.astimezone(MARKET_TIMEZONE)
        return f"OPEN  (closes {closes:%a %Y-%m-%d %H:%M} ET)"
    opens = clock.next_open.astimezone(MARKET_TIMEZONE)
    return f"CLOSED  (next open {opens:%a %Y-%m-%d %H:%M} ET)"


def build_status_report(broker: Broker, watchlist: tuple[str, ...]) -> str:
    account = broker.get_account()
    positions = broker.get_positions()
    clock = broker.get_market_clock()

    lines = [
        LINE,
        "  ALPACA PAPER ACCOUNT  -  SIMULATED MONEY, NOT REAL",
        LINE,
        "Account",
        f"  Account number : {mask_account_number(account.account_number)} (paper)",
        f"  Status         : {account.status}",
        f"  Equity         : {money(account.equity)}",
        f"  Cash           : {money(account.cash)}",
        f"  Buying power   : {money(account.buying_power)}",
        f"  Change today   : {signed_money(account.change_today)}",
        f"  Trading blocked: {'YES' if account.trading_blocked else 'no'}",
        "",
        f"Market: {describe_market(clock)}",
        "",
        f"Open positions ({len(positions)})",
    ]
    if not positions:
        lines.append("  none")
    for p in positions:
        lines.append(
            f"  {p.symbol:<6} {p.quantity:g} shares @ {money(p.average_entry_price)}"
            f"  now {money(p.current_price)}  P/L {signed_money(p.unrealized_pl)}"
            f" ({p.unrealized_pl_percent:+.2f}%)"
        )

    lines += ["", "Watchlist"]
    for symbol in watchlist:
        asset = broker.get_asset(symbol)
        if asset is None:
            lines.append(f"  {symbol:<6} NOT FOUND at Alpaca - check the symbol in settings.yaml")
        else:
            state = "tradable" if asset.tradable else "NOT tradable"
            lines.append(f"  {symbol:<6} {state:<12} {asset.name}")
    lines.append(LINE)
    return "\n".join(lines)
