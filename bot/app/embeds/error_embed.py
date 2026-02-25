import discord
from typing import Any


def build_error_embed(error_data: dict[str, Any]) -> discord.Embed:
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
