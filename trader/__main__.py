"""Entry point. Run the app from the project folder with:

    python -m trader

Phase 1: loads settings, runs the safety checks, sets up logging, and
reports what it found. It does NOT connect to Alpaca or trade yet.
"""

import logging
import sys

from trader.config import Settings, load_settings
from trader.errors import ConfigError, SafetyError
from trader.logging_setup import setup_logging

BANNER = """
==============================================================
            PAPER TRADING ENVIRONMENT - NO REAL MONEY
=============================================================="""


def print_startup_summary(settings: Settings) -> None:
    log = logging.getLogger("trader.main")
    log.info("Paper trading: %s", settings.paper_trading)
    log.info("Alpaca endpoint: %s", settings.alpaca_base_url)
    log.info("Watchlist (%d symbols): %s", len(settings.watchlist), ", ".join(settings.watchlist))
    if settings.has_api_keys:
        log.info("Alpaca paper API keys: found (not used until Phase 2)")
    else:
        log.info("Alpaca paper API keys: not set yet (needed in Phase 2)")
    log.info("Log file: %s", settings.log_file)


def main() -> int:
    """Returns an exit code: 0 = success, 1 = refused to start."""
    print(BANNER)
    try:
        settings = load_settings()
    except SafetyError as exc:
        print(f"\n[SAFETY STOP] {exc}\nThe application will not start.", file=sys.stderr)
        return 1
    except ConfigError as exc:
        print(f"\n[CONFIG ERROR] {exc}\nThe application will not start.", file=sys.stderr)
        return 1

    setup_logging(settings.log_level, settings.log_file)
    print_startup_summary(settings)
    logging.getLogger("trader.main").info("Startup checks passed. Phase 1 complete - no trading yet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
