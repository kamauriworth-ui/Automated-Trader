"""Turns a BacktestResult into a readable report, and saves the trades to a CSV file.

The CSV (results/backtest_<period>_trades.csv) can be opened from the file list
in your Codespace, or in any spreadsheet app.
"""

import csv
from pathlib import Path

from trader.backtest import metrics
from trader.backtest.models import BacktestResult, SymbolResult, Trade
from trader.formatting import money, signed_money

LINE = "=" * 88
SMALL_SAMPLE = 30   # fewer trades than this = weak evidence
HIGHLIGHTS = 3      # best and worst trades shown by default


def pct(value: float | None, signed: bool = True) -> str:
    if value is None:
        return "n/a"
    return f"{value:+.1f}%" if signed else f"{value:.0f}%"


def ratio(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f}"


def _values(curve):
    return [v for _, v in curve]


def strategy_row(label: str, trades: list[Trade], equity) -> str:
    s = metrics.trade_stats(trades)
    return (
        f"  {label:<6}{s.count:>7}{pct(s.win_rate_pct, False):>10}{pct(s.avg_gain_pct):>10}"
        f"{pct(s.avg_loss_pct):>10}{ratio(s.risk_reward):>7}{signed_money(s.total_pnl):>15}"
        f"{pct(metrics.total_return_pct(_values(equity))):>9}{pct(metrics.max_drawdown_pct(_values(equity))):>10}"
    )


def comparison_row(label: str, equity, hold, days_holding: int | None) -> str:
    in_market = "" if days_holding is None else f"{days_holding / max(len(equity), 1) * 100:>15.0f}%"
    return (
        f"  {label:<6}{pct(metrics.total_return_pct(_values(equity))):>16}"
        f"{pct(metrics.max_drawdown_pct(_values(equity))):>10}     |"
        f"{pct(metrics.total_return_pct(_values(hold))):>18}{pct(metrics.max_drawdown_pct(_values(hold))):>10}"
        f"{in_market}"
    )


def trade_lines(trade: Trade) -> list[str]:
    sold = "(open)" if trade.still_open else f"{trade.exit_date}"
    reason = trade.exit_reason.removeprefix("Trend is broken: ")
    return [
        f"  {trade.symbol:<6}{trade.entry_date!s:>11}{money(trade.entry_price):>11}  {sold:>10}"
        f"{money(trade.exit_price):>11}{trade.shares:>7}{pct(trade.return_pct):>9}"
        f"{signed_money(trade.pnl):>12}{trade.holding_days:>6}",
        f"         {'status' if trade.still_open else 'sold because'}: {reason}",
    ]


def cautions(result: BacktestResult, all_trades: list[Trade], equity, hold) -> list[str]:
    notes = []
    if len(all_trades) < SMALL_SAMPLE:
        notes.append(
            f"Only {len(all_trades)} trades. That is too few to be confident; "
            "these results could easily be luck."
        )
    notes.append(
        "These stocks were chosen knowing they became big winners (hindsight). "
        "Judge the strategy against BUY & HOLD, not against zero."
    )
    strategy_return = metrics.total_return_pct(_values(equity))
    hold_return = metrics.total_return_pct(_values(hold))
    if strategy_return is not None and hold_return is not None and strategy_return < hold_return:
        notes.append(
            "The strategy earned LESS than simply holding. It only earns its keep if its smaller "
            "drops (Max drop) matter more to you than the lost return."
        )
    if all_trades:
        worst = min(all_trades, key=lambda t: t.return_pct)
        notes.append(
            f"No stop-loss yet (Phase 6). Worst single trade: {pct(worst.return_pct)} "
            f"({worst.symbol}, bought {worst.entry_date})."
        )
    skipped = sum(s.skipped_buys for s in result.symbols)
    if skipped:
        notes.append(f"{skipped} BUY signal(s) were skipped because one share cost more than the trade amount.")
    if result.feed_used == "iex":
        notes.append("History came from IEX only (one exchange): volume is a small slice of real trading.")
    notes.append(
        f"Costs assumed: {result.settings.slippage_pct:g}% slippage per buy and per sell, no commission. "
        "Real results would differ."
    )
    return notes


def trade_section(all_trades: list[Trade], show_all: bool) -> list[str]:
    header = (
        f"  {'Stock':<6}{'Bought':>11}{'Paid':>11}  {'Sold':>10}{'Got':>11}{'Shares':>7}{'Result':>9}"
        f"{'P/L':>12}{'Days':>6}"
    )
    if not all_trades:
        return ["", "  TRADES (0)", "  (no trades)"]
    if show_all or len(all_trades) <= HIGHLIGHTS * 2:
        lines = ["", f"  TRADES ({len(all_trades)})", header]
        for trade in sorted(all_trades, key=lambda t: t.entry_date):
            lines += trade_lines(trade)
        return lines
    by_result = sorted(all_trades, key=lambda t: t.return_pct)
    lines = ["", f"  BEST {HIGHLIGHTS} TRADES (of {len(all_trades)})", header]
    for trade in reversed(by_result[-HIGHLIGHTS:]):
        lines += trade_lines(trade)
    lines += ["", f"  WORST {HIGHLIGHTS} TRADES", header]
    for trade in by_result[:HIGHLIGHTS]:
        lines += trade_lines(trade)
    lines.append("  (Every trade is in the CSV file named below. Add --all-trades to print them all.)")
    return lines


def build_backtest_report(result: BacktestResult, show_all_trades: bool = False) -> str:
    s = result.settings
    period = result.period
    symbols: list[SymbolResult] = result.symbols
    all_trades = [t for sr in symbols for t in sr.trades]
    equity = metrics.combine_curves([sr.equity for sr in symbols])
    hold = metrics.combine_curves([sr.buy_hold_equity for sr in symbols])

    lines = [
        LINE,
        f"  BACKTEST - {result.strategy_name} - {period.name.upper()} period {period.start} to {period.end}",
        LINE,
        f"  Data: {result.feed_used.upper()} feed | {money(s.trade_amount)} per trade per stock | "
        f"slippage {s.slippage_pct:g}% per buy and per sell",
    ]
    if period.name == "development" and s.holdout_years:
        lines.append(f"  The most recent {s.holdout_years} year(s) are SEALED. See them once, at the end, with --holdout.")
    if period.name == "holdout":
        lines.append("  FINAL EXAM: if you change settings after seeing this, it is no longer a fair test.")

    lines += [
        "",
        "  STRATEGY RESULTS",
        f"  {'Stock':<6}{'Trades':>7}{'Win rate':>10}{'Avg gain':>10}{'Avg loss':>10}{'R/R':>7}"
        f"{'Profit/loss':>15}{'Return':>9}{'Max drop':>10}",
    ]
    lines += [strategy_row(sr.symbol, sr.trades, sr.equity) for sr in symbols]
    lines.append(strategy_row("ALL", all_trades, equity))

    lines += [
        "",
        "  COMPARED WITH BUY & HOLD (same money, bought on day 1, never sold)",
        f"  {'Stock':<6}{'Strategy return':>16}{'Max drop':>10}     |{'Buy&hold return':>18}{'Max drop':>10}"
        f"{'Time in market':>16}",
    ]
    lines += [comparison_row(sr.symbol, sr.equity, sr.buy_hold_equity, sr.days_holding) for sr in symbols]
    total_days = sum(sr.days_holding for sr in symbols)
    lines.append(comparison_row("ALL", equity, hold, None)
                 + f"{total_days / max(sum(len(sr.equity) for sr in symbols), 1) * 100:>15.0f}%")

    strategy_years, hold_years = metrics.yearly_returns(equity), metrics.yearly_returns(hold)
    closed_by_year = metrics.trades_by_exit_year([t for t in all_trades if not t.still_open])
    lines += ["", "  BY YEAR (all stocks together)", f"  {'Year':<6}{'Strategy':>10}{'Buy&hold':>10}{'Trades closed':>15}"]
    for year in sorted(strategy_years):
        lines.append(
            f"  {year:<6}{pct(strategy_years[year]):>10}{pct(hold_years.get(year)):>10}"
            f"{len(closed_by_year.get(year, [])):>15}"
        )

    lines += trade_section(all_trades, show_all_trades)

    lines += ["", "  CAUTIONS"]
    lines += [f"  - {note}" for note in cautions(result, all_trades, equity, hold)]
    lines.append(LINE)
    return "\n".join(lines)


def save_trades_csv(result: BacktestResult, folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"backtest_{result.period.name}_trades.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["symbol", "entry_date", "entry_price", "exit_date", "exit_price", "shares",
                         "return_pct", "pnl", "holding_days", "still_open", "entry_reason", "exit_reason"])
        for sr in result.symbols:
            for t in sr.trades:
                writer.writerow([t.symbol, t.entry_date, f"{t.entry_price:.4f}", t.exit_date, f"{t.exit_price:.4f}",
                                 t.shares, f"{t.return_pct:.2f}", f"{t.pnl:.2f}", t.holding_days, t.still_open,
                                 t.entry_reason, t.exit_reason])
    return path
