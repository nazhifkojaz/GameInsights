def format_number(num: int | float | None) -> str:
    if num is None:
        return "N/A"
    if isinstance(num, float):
        return f"{num:,.2f}"
    return f"{num:,}"


def format_currency(num: float | None, currency: str | None = "$") -> str:
    if num is None:
        return "N/A"
    return f"{currency}{num:,.2f}"
