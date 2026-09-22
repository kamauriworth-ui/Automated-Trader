# Automated-Trader

An educational, **paper-trading-only** automated stock trading system built step by step.
No real money is ever used. The app refuses to start unless it is clearly configured for
Alpaca's paper-trading environment.

## Status

| Phase | What | Status |
|---|---|---|
| 1 | Foundation: config, safety checks, logging | ✅ done |
| 2 | Alpaca paper connection (read-only) | ⏳ next |
| 3 | Market data layer | |
| 4 | First simple strategy (signals only) | |
| 5 | Backtesting | |
| 6 | Risk management | |
| 7 | Paper order execution | |
| 8 | Position management | |
| 9 | Trade journal | |
| 10 | Monitoring dashboard | |
| 11 | Testing (expanded) | |
| 12 | Strategy improvement | |

## Setup (first time)

Requires Python 3.11 or newer.

```bash
python3 -m venv .venv               # create an isolated Python environment
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install -r requirements.txt     # install the libraries
cp .env.example .env                # Windows: copy .env.example .env
```

## Run

```bash
python -m trader      # start the app
python -m pytest -v   # run the automated tests
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
tests/                 Automated tests
```

## Safety rules

1. `PAPER_TRADING` must be exactly `TRUE`. Missing or anything else means the app stops.
2. `ALPACA_BASE_URL` must be exactly `https://paper-api.alpaca.markets` (allow-list).
3. An API key that doesn't start with `PK` (Alpaca's paper key prefix) is rejected.
4. Other Alpaca URL variables in your environment that point anywhere else are rejected.
5. API keys live only in `.env`, which git ignores.
