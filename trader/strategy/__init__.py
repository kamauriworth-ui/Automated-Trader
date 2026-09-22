"""Strategies: turn checked market data into BUY / SELL / WATCH signals.

A strategy only ever receives a MarketSnapshot (from market_data/snapshot.py).
It never talks to Alpaca and never places orders.
"""
