"""Small helpers for showing numbers to humans. Shared by all reports."""


def money(value: float) -> str:
    return f"-${abs(value):,.2f}" if value < 0 else f"${value:,.2f}"


def signed_money(value: float) -> str:
    return ("+" if value >= 0 else "") + money(value)


def percent(value: float) -> str:
    return f"{value:+.2f}%"
