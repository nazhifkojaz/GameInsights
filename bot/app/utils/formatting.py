def format_number(num: int | float | None) -> str:
    """Format a number with thousand separators.

    Args:
        num: Number to format, or None for "N/A".

    Returns:
        Formatted number string with commas as thousand separators.
        Floats are formatted with 2 decimal places.

    Example:
        >>> format_number(1234567)
        '1,234,567'
        >>> format_number(1234.56)
        '1,234.56'
        >>> format_number(None)
        'N/A'
    """
    if num is None:
        return "N/A"
    if isinstance(num, float):
        return f"{num:,.2f}"
    return f"{num:,}"


def format_currency(num: float | None, currency: str = "$") -> str:
    """Format a number as currency.

    Args:
        num: Number to format, or None for "N/A".
        currency: Currency symbol prefix (default: "$").

    Returns:
        Formatted currency string with 2 decimal places.

    Example:
        >>> format_currency(1234567.89)
        '$1,234,567.89'
        >>> format_currency(99.99, "€")
        '€99.99'
        >>> format_currency(None)
        'N/A'
    """
    if num is None:
        return "N/A"
    return f"{currency}{num:,.2f}"
