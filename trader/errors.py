"""Custom error types.

Giving each kind of problem its own error class lets the rest of the program
react differently to "your config file is broken" versus "this would be unsafe".
"""


class TraderError(Exception):
    """Base class for every error this application raises on purpose."""


class ConfigError(TraderError):
    """A setting is missing, misspelled, or has an invalid value."""


class SafetyError(TraderError):
    """Something could lead to live (real-money) trading. The app must stop."""


class BrokerError(TraderError):
    """Talking to the broker (Alpaca) failed: bad keys, no internet, outage, ..."""


class DataFeedNotPermittedError(BrokerError):
    """The account's data plan doesn't allow the requested data feed (e.g. recent SIP data)."""
