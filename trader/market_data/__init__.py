"""Market data: prices and price history for the watchlist.

The strategy (Phase 4) will only ever see the plain `Bar` objects defined in
models.py, never Alpaca's own objects. That lets us feed it live data, saved
historical data (Phase 5 backtesting), or made-up test data, unchanged.
"""
