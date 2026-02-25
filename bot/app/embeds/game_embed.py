import discord
from typing import Any
from app.utils.formatting import format_number, format_currency


def build_game_embed(data: dict[str, Any]) -> discord.Embed:
    title = data.get("name", "Unknown Game")
    appid = data.get("steam_appid", "")
    url = f"https://store.steampowered.com/app/{appid}" if appid else None

    embed = discord.Embed(title=title, url=url, color=discord.Color.blue())

    # Pricing
    price = "Free" if data.get("is_free") else format_currency(data.get("price_final"))
    embed.add_field(name="Price", value=price, inline=True)

    # Reviews
    review_desc = data.get("review_score_desc", "N/A")
    total_reviews = format_number(data.get("total_reviews"))
    embed.add_field(
        name="Reviews", value=f"{review_desc} ({total_reviews})", inline=True
    )

    # Players
    ccu = format_number(data.get("ccu") or data.get("active_player_24h"))
    peak = format_number(data.get("peak_active_player_all_time"))
    embed.add_field(name="Current Players (24h)", value=ccu, inline=True)
    embed.add_field(name="All-Time Peak", value=peak, inline=True)

    # Sales
    copies = format_number(data.get("copies_sold"))
    rev = format_currency(data.get("estimated_revenue"))
    embed.add_field(name="Copies Sold", value=copies, inline=True)
    embed.add_field(name="Est. Revenue", value=rev, inline=True)

    # ProtonDB
    proton_tier = data.get("protondb_tier", "Unknown")
    embed.add_field(name="ProtonDB Tier", value=proton_tier, inline=True)

    # Metadata
    devs = ", ".join(data.get("developers", [])) or "Unknown"
    release = data.get("release_date", "Unknown")
    embed.add_field(name="Developer", value=devs, inline=True)
    embed.add_field(name="Release Date", value=release, inline=True)

    embed.set_footer(text=f"AppID: {appid}")

    return embed


def build_players_embed(data: list[dict[str, Any]], appid: str = "") -> discord.Embed:
    if not data:
        return discord.Embed(
            title="Player History",
            description="No data found.",
            color=discord.Color.red(),
        )

    game_data = data[0]
    title = f"Player History: {game_data.get('name', appid)}"
    embed = discord.Embed(title=title, color=discord.Color.green())

    embed.add_field(
        name="All-Time Peak",
        value=format_number(game_data.get("peak_active_player_all_time")),
        inline=False,
    )

    # Add up to 10 most recent months
    count = 0
    # filter keys that look like YYYY-MM
    for key, value in sorted(game_data.items(), reverse=True):
        if len(key) == 7 and "-" in key and count < 10:
            embed.add_field(name=key, value=format_number(value), inline=True)
            count += 1

    return embed
