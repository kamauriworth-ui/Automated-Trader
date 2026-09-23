"""Entry point. Run from the project folder:

    python -m trader                 # startup checks + paper account status
    python -m trader search apple    # find stocks by name or symbol
    python -m trader prices          # recent prices + daily candles for the watchlist
    python -m trader signals         # BUY / SELL / WATCH for each watchlist stock (no orders)
    python -m trader backtest        # test the strategy on past years (development period)
    python -m trader backtest --holdout   # the sealed final exam - run once, at the end
    python -m trader backtest --all-trades  # also print every single trade

Everything so far only READS information. There is no code anywhere in the
project that can place an order yet.
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


def show_prices(settings: Settings) -> None:
    from trader.broker.alpaca_paper import AlpacaPaperBroker
    from trader.market_data.alpaca_data import AlpacaMarketData
    from trader.market_report import build_price_report

    broker = AlpacaPaperBroker.connect(settings)  # confirms the keys belong to a paper account
    clock = broker.get_market_clock()               # the real market time, from Alpaca
    provider = AlpacaMarketData.from_settings(settings)
    print(
        build_price_report(
            provider,
            clock,
            settings.watchlist,
            settings.history_days,
            settings.market_data_feed,
            settings.max_price_age_minutes,
        )
    )


def show_signals(settings: Settings) -> None:
    from trader.broker.alpaca_paper import AlpacaPaperBroker
    from trader.market_data.alpaca_data import AlpacaMarketData
    from trader.signals_report import build_signals_report, evaluate_watchlist
    from trader.strategy.trend_momentum import TrendMomentumStrategy

    broker = AlpacaPaperBroker.connect(settings)
    clock = broker.get_market_clock()
    provider = AlpacaMarketData.from_settings(settings)
    strategy = TrendMomentumStrategy(settings.strategy)
    results = evaluate_watchlist(
        strategy, provider, clock, settings.watchlist, settings.history_days, settings.max_price_age_minutes
    )
    print(build_signals_report(results, strategy.name, clock))


def run_backtest_command(settings: Settings, holdout: bool, all_trades: bool) -> None:
    from datetime import datetime, timedelta, timezone

    from trader.backtest.data import compute_periods, load_history, warmup_calendar_days
    from trader.backtest.engine import run_backtest
    from trader.backtest.report import build_backtest_report, save_trades_csv
    from trader.broker.alpaca_paper import AlpacaPaperBroker
    from trader.config import PROJECT_ROOT
    from trader.market_data.alpaca_data import AlpacaMarketData
    from trader.market_data.snapshot import market_date
    from trader.strategy.trend_momentum import TrendMomentumStrategy

    bt = settings.backtest
    broker = AlpacaPaperBroker.connect(settings)
    clock = broker.get_market_clock()
    now = datetime.now(timezone.utc)
    development, holdout_period = compute_periods(market_date(now), bt.years, bt.holdout_years)
    if holdout and holdout_period is None:
        raise ConfigError("There is no holdout period: backtest.holdout_years is 0 in settings.yaml.")
    period = holdout_period if holdout else development

    strategy = TrendMomentumStrategy(settings.strategy)
    warmup = timedelta(days=warmup_calendar_days(strategy.params.days_needed))
    start = datetime.combine(period.start, datetime.min.time(), tzinfo=timezone.utc) - warmup
    log.info("Backtest: downloading history for %s from %s", ", ".join(settings.watchlist), start.date())
    provider = AlpacaMarketData.from_settings(settings)
    bars, feed_used = load_history(provider, settings.watchlist, start, clock, bt.feed, now)

    result = run_backtest(strategy, bars, period, bt, feed_used)
    print(build_backtest_report(result, all_trades))
    path = save_trades_csv(result, PROJECT_ROOT / "results")
    print(f"All trades saved to: {path.relative_to(PROJECT_ROOT)}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m trader", description="Paper-trading system")
    commands = parser.add_subparsers(dest="command")
    find = commands.add_parser("search", help="find stocks by company name or symbol")
    find.add_argument("text", help="for example: apple, nvidia, anthropic")
    commands.add_parser("prices", help="show recent prices and daily candles for the watchlist")
    commands.add_parser("signals", help="show BUY / SELL / WATCH signals (no orders are placed)")
    backtest = commands.add_parser("backtest", help="test the strategy on past years")
    backtest.add_argument("--holdout", action="store_true", help="run the sealed final-exam period instead")
    backtest.add_argument("--all-trades", action="store_true", help="print every trade, not just the best and worst")
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
        elif args.command == "prices":
            show_prices(settings)
        elif args.command == "signals":
            show_signals(settings)
        elif args.command == "backtest":
            run_backtest_command(settings, args.holdout, args.all_trades)
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
