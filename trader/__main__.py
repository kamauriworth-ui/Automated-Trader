"""Entry point. Run from the project folder:

    python -m trader                 # startup checks + paper account status
    python -m trader search apple    # find stocks by name or symbol

Phase 2: connects to Alpaca PAPER trading and READS information only.
There is no code anywhere in the project that can place an order yet.
"""

import argparse
import logging
import sys

from trader.config import Settings, load_settings
from trader.errors import BrokerError, ConfigError, SafetyError
from trader.logging_setup import setup_logging

BANNER = """
==============================================================
            PAPER TRADING ENVIRONMENT - NO REAL MONEY
=============================================================="""

log = logging.getLogger("trader.main")


def print_startup_summary(settings: Settings) -> None:
    log.info("Paper trading: %s", settings.paper_trading)
    log.info("Alpaca endpoint: %s", settings.alpaca_base_url)
    log.info("Watchlist (%d symbols): %s", len(settings.watchlist), ", ".join(settings.watchlist))
    log.info("Log file: %s", settings.log_file)


def show_status(settings: Settings) -> None:
    if not settings.has_api_keys:
        log.warning(
            "No Alpaca paper API keys set - skipping the connection check. "
            "Add ALPACA_API_KEY and ALPACA_SECRET_KEY to connect."
        )
        return
    # Imported here so Phase-1-style runs (no keys) don't need Alpaca at all.
    from trader.broker.alpaca_paper import AlpacaPaperBroker
    from trader.status_report import build_status_report

    broker = AlpacaPaperBroker.connect(settings)
    print(build_status_report(broker, settings.watchlist))


def search(settings: Settings, text: str) -> None:
    from trader.broker.alpaca_paper import AlpacaPaperBroker

    broker = AlpacaPaperBroker.connect(settings)
    matches = broker.search_assets(text)
    print(f"\n{len(matches)} active US stock(s) at Alpaca matching {text!r}:")
    for asset in matches[:25]:
        print(f"  {asset.symbol:<8} {'tradable' if asset.tradable else 'NOT tradable':<12} {asset.name}")
    if len(matches) > 25:
        print(f"  ... and {len(matches) - 25} more. Try a more specific search.")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m trader", description="Paper-trading system")
    commands = parser.add_subparsers(dest="command")
    find = commands.add_parser("search", help="find stocks by company name or symbol")
    find.add_argument("text", help="for example: apple, nvidia, anthropic")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Returns an exit code: 0 = success, 1 = stopped because of a problem."""
    args = parse_args(sys.argv[1:] if argv is None else argv)
    print(BANNER)
    try:
        settings = load_settings()
        setup_logging(settings.log_level, settings.log_file)
        print_startup_summary(settings)
        if args.command == "search":
            search(settings, args.text)
        else:
            show_status(settings)
    except SafetyError as exc:
        print(f"\n[SAFETY STOP] {exc}\nThe application will not continue.", file=sys.stderr)
        return 1
    except ConfigError as exc:
        print(f"\n[CONFIG ERROR] {exc}\nThe application will not continue.", file=sys.stderr)
        return 1
    except BrokerError as exc:
        print(f"\n[CONNECTION ERROR] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
