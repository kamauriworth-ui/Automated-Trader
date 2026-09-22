# Automated-Trader

An educational, **paper-trading-only** automated stock trading system built step by step.
No real money is ever used. The app refuses to start unless it is clearly configured for
Alpaca's paper-trading environment.

## Status

| Phase | What | Status |
|---|---|---|
| 1 | Foundation: config, safety checks, logging | ✅ done |
| 2 | Alpaca paper connection (read-only) | ✅ done |
| 3 | Market data layer | ✅ done |
| 4 | First simple strategy (signals only) | |
| 5 | Backtesting | |
| 6 | Risk management | |
| 7 | Paper order execution | |
| 8 | Position management | |
| 9 | Trade journal | |
| 10 | Monitoring dashboard | |
| 11 | Testing (expanded) | |
| 12 | Strategy improvement | |

## Running it from a tablet or browser (no local Python needed)

**Option A: just check the tests (zero setup).** Every push runs the tests automatically on
GitHub. Open the repository's **Actions** tab and tap the latest **Tests** run.
A green check means everything passed.

**Option B: run it yourself in GitHub Codespaces (a cloud computer in your browser).**
1. On the repository page, switch to the branch you want (the branch dropdown).
2. Tap **Code → Codespaces → Create codespace on <branch>**.
3. Wait about 2 minutes while it installs Python and the libraries automatically.
4. In the terminal at the bottom, type:
   ```bash
   python -m trader      # run the app
   python -m pytest -v   # run the tests
   ```
5. When you're done, stop the Codespace (**Code → Codespaces → … → Stop**) to save free hours.

## Connecting your Alpaca paper account (Phase 2)

1. Sign up at alpaca.markets (free). Paper trading needs no deposit.
2. In the Alpaca dashboard, make sure the **Paper** account is selected (account switcher, top-left).
3. Find **API Keys** on the paper dashboard and choose **Generate New Keys**.
   The Key ID starts with `PK`. The Secret is shown **only once**, so copy it right away.
4. On GitHub: your profile picture → **Settings** → **Codespaces** → **New secret**. Add two secrets,
   and under "Repository access" pick this repository for each:
   - `ALPACA_API_KEY` = your Key ID
   - `ALPACA_SECRET_KEY` = your Secret
5. Start (or restart) your Codespace so it picks up the secrets, then run:
   ```bash
   pip install -r requirements.txt   # only needed in a Codespace created before Phase 2
   python -m trader                  # paper account status
   python -m trader search apple     # look up stocks by name or symbol
   python -m trader prices           # recent prices + daily candles for the watchlist
   ```

Never paste your keys into code, chat messages, or screenshots.

## Running it on your own computer (optional)

Requires Python 3.11 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                # Windows: copy .env.example .env
python -m trader
python -m pytest -v
```

## Project layout

```
config/settings.yaml   Non-secret settings (watchlist, logging)
.env                   Secrets + PAPER_TRADING switch (never committed)
.env.example           Template for .env
trader/__main__.py     Entry point (python -m trader)
trader/config.py       Loads and validates all settings
trader/safety.py       Paper-trading safety checks
trader/logging_setup.py Logging to terminal + logs/trader.log
trader/errors.py       Custom error types
trader/broker/         Broker layer: models.py (our data shapes), base.py (the Broker
                       checklist), alpaca_paper.py (the ONLY file that uses Alpaca)
trader/status_report.py Formats the account status report
trader/market_data/    Price data: models.py (Bar = one candle), base.py (the provider
                       checklist), processing.py (checks/cleans data),
                       alpaca_data.py (reads prices from Alpaca),
                       snapshot.py (finished-vs-today candles + freshness check)
trader/market_report.py Formats the price report
trader/formatting.py   Shared number formatting
tests/                 Automated tests
.devcontainer/         Cloud environment setup (GitHub Codespaces)
.github/workflows/     Runs the tests automatically on GitHub
```

## Safety rules

1. `PAPER_TRADING` must be exactly `TRUE`. Missing or anything else means the app stops.
2. `ALPACA_BASE_URL` must be exactly `https://paper-api.alpaca.markets` (allow-list).
3. An API key that doesn't start with `PK` (Alpaca's paper key prefix) is rejected.
4. Other Alpaca URL variables in your environment that point anywhere else are rejected.
5. API keys live only in `.env` (ignored by git) or in Codespaces secrets.
6. The Alpaca client is created with `paper=True`, and the address it will really use is re-checked.
7. After connecting, the account number must start with `PA` (Alpaca paper accounts), or the app disconnects.
8. Everything so far is read-only: no code in the project can place an order yet.
9. Price data comes from Alpaca's market-data service, which cannot place orders at all.
10. Decisions use finished trading days only; today's still-forming candle is kept separate.
11. While the market is open, prices older than `max_price_age_minutes` (or timestamped in the
    future) are marked STALE and must not be used for decisions.
