from typing import Any

import discord


def build_error_embed(error_data: dict[str, Any]) -> discord.Embed:
    """Build a Discord embed for error messages.

    Creates an embed with appropriate color based on error type,
    including error message and optional identifier/source information.

    Args:
        error_data: Dictionary containing error details with keys:
            - error: Error type string
            - message: Human-readable error message
            - identifier: Optional identifier for the resource
            - source: Optional source information

    Returns:
        A discord.Embed object formatted with error information.

    Example:
        >>> data = {"error": "not_found", "message": "Game not found", "identifier": "123"}
        >>> embed = build_error_embed(data)
        >>> embed.title
        'Error'
    """
    error_type = error_data.get("error", "unknown_error")
    message = error_data.get("message", "An unknown error occurred.")

    colors = {
        "not_found": discord.Color.orange(),
        "invalid_request": discord.Color.red(),
        "source_unavailable": discord.Color.gold(),
        "internal_error": discord.Color.dark_red(),
    }

    color = colors.get(error_type, discord.Color.dark_red())

    embed = discord.Embed(title="Error", description=message, color=color)

    if "identifier" in error_data and error_data["identifier"]:
        embed.add_field(name="Identifier", value=error_data["identifier"])

    if "source" in error_data and error_data["source"]:
        embed.add_field(name="Source", value=error_data["source"])

    return embed
