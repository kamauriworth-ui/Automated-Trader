"""Paper-trading safety checks.

Every function here either returns quietly (all good) or raises SafetyError
(stop the program). The application calls these at startup, before it does
anything else. Later phases will call them again right before sending orders.

Design rule: we use an ALLOW-list, not a block-list. Instead of trying to
recognise every possible "bad" setting, we accept exactly one known-good
value and reject everything else.
"""

from collections.abc import Mapping

from trader.errors import SafetyError

# The ONLY Alpaca address this project is ever allowed to talk to.
PAPER_API_URL = "https://paper-api.alpaca.markets"

# Alpaca paper-account API key IDs start with "PK". Live keys start differently.
PAPER_KEY_PREFIX = "PK"

# Environment variable names that Alpaca's own tools may read on their own.
# If any of them point somewhere other than the paper URL, the setup is
# ambiguous and we refuse to start.
ALPACA_URL_VARIABLES = ("APCA_API_BASE_URL", "ALPACA_API_BASE_URL")


def require_paper_trading_flag(value: str | None) -> None:
    """PAPER_TRADING must be set, and it must be exactly TRUE."""
    if value is None or value.strip() == "":
        raise SafetyError(
            "PAPER_TRADING is not set. Add the line PAPER_TRADING=TRUE to your .env file."
        )
    if value.strip().upper() != "TRUE":
        raise SafetyError(
            f"PAPER_TRADING is set to {value!r}. This project only supports paper "
            "trading, so the only accepted value is TRUE."
        )


def require_paper_endpoint(url: str | None) -> str:
    """The Alpaca URL must be the paper-trading URL, and nothing else.

    Returns the cleaned-up URL so callers use one consistent spelling.
    """
    if url is None or url.strip() == "":
        raise SafetyError(
            f"ALPACA_BASE_URL is not set. Add ALPACA_BASE_URL={PAPER_API_URL} to your .env file."
        )
    cleaned = url.strip().rstrip("/")
    if cleaned != PAPER_API_URL:
        raise SafetyError(
            f"ALPACA_BASE_URL is {url!r}, which is not the paper-trading endpoint. "
            f"The only allowed value is {PAPER_API_URL}"
        )
    return cleaned


def require_paper_api_key(api_key: str | None) -> None:
    """If an API key is provided, it must look like a paper key (starts with 'PK').

    A missing key is allowed here; the code that actually connects to Alpaca
    (Phase 2) will insist on having one.
    """
    if api_key is None or api_key.strip() == "":
        return
    if not api_key.strip().startswith(PAPER_KEY_PREFIX):
        raise SafetyError(
            f"ALPACA_API_KEY does not start with {PAPER_KEY_PREFIX!r}, so it does not look "
            "like a paper-trading key. Generate keys from the PAPER dashboard on Alpaca."
        )


def require_no_conflicting_alpaca_urls(env: Mapping[str, str]) -> None:
    """Other Alpaca URL variables, if present, must also point at paper trading."""
    for name in ALPACA_URL_VARIABLES:
        value = env.get(name)
        if value is None or value.strip() == "":
            continue
        if value.strip().rstrip("/") != PAPER_API_URL:
            raise SafetyError(
                f"The environment variable {name} is set to {value!r}. It conflicts with "
                "paper-only trading. Remove it or set it to the paper URL."
            )


def run_startup_safety_checks(env: Mapping[str, str]) -> None:
    """Run every safety check. Called once when the application starts."""
    require_paper_trading_flag(env.get("PAPER_TRADING"))
    require_paper_endpoint(env.get("ALPACA_BASE_URL"))
    require_paper_api_key(env.get("ALPACA_API_KEY"))
    require_no_conflicting_alpaca_urls(env)
