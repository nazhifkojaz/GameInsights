from typing import Any

import discord
from io import BytesIO
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

from app.constants import STEAM_STORE_URL_TEMPLATE
from app.utils.formatting import format_currency, format_number


def build_game_embed(data: dict[str, Any]) -> discord.Embed:
    """Build a Discord embed for game information."""
    title = data.get("name", "Unknown Game")
    appid = data.get("steam_appid", "")
    url = STEAM_STORE_URL_TEMPLATE.format(appid=appid) if appid else None

    embed = discord.Embed(title=title, url=url, color=discord.Color.blue())

    price = "Free" if data.get("is_free") else format_currency(data.get("price_final"))
    embed.add_field(name="Price", value=price, inline=True)

    review_desc = data.get("review_score_desc", "N/A")
    total_reviews = format_number(data.get("total_reviews"))
    embed.add_field(
        name="Reviews", value=f"{review_desc} ({total_reviews})", inline=True
    )

    ccu = format_number(data.get("ccu") or data.get("active_player_24h"))
    peak = format_number(data.get("peak_active_player_all_time"))
    embed.add_field(name="Current Players (24h)", value=ccu, inline=True)
    embed.add_field(name="All-Time Peak", value=peak, inline=True)

    copies = format_number(data.get("copies_sold"))
    rev = format_currency(data.get("estimated_revenue"))
    embed.add_field(name="Copies Sold", value=copies, inline=True)
    embed.add_field(name="Est. Revenue", value=rev, inline=True)

    proton_tier = data.get("protondb_tier") or "Unknown"
    embed.add_field(name="ProtonDB Tier", value=proton_tier, inline=True)

    devs = ", ".join(data.get("developers") or []) or "Unknown"
    release = data.get("release_date") or "Unknown"
    embed.add_field(name="Developer", value=devs, inline=True)
    embed.add_field(name="Release Date", value=release, inline=True)

    embed.set_footer(text=f"AppID: {appid}")

    return embed


def build_players_graph(data: list[dict[str, Any]], appid: str = "") -> discord.File:
    """Generate a player count history graph as a Discord file attachment.

    Creates a line graph showing historical player count data over time.
    Uses only Pillow (no matplotlib) for a lightweight solution.
    """
    # Discord dark theme colors
    BG_COLOR = (44, 47, 51)  # #2C2F33
    LINE_COLOR = (88, 101, 242)  # #5865F2 (Discord blurple)
    TEXT_COLOR = (255, 255, 255)  # White
    GRID_COLOR = (64, 68, 75)  # #40444B
    PEAK_BADGE_COLOR = (237, 66, 69)  # #ED4245 (Red)
    ALL_TIME_BADGE_COLOR = (59, 165, 93)  # #3BA55D (Green)
    FILL_ALPHA = 0.3

    # Image dimensions
    WIDTH, HEIGHT = 1000, 500
    MARGIN = 80
    GRAPH_TOP = 100
    GRAPH_BOTTOM = HEIGHT - MARGIN
    GRAPH_LEFT = MARGIN
    GRAPH_RIGHT = WIDTH - MARGIN

    # Create image
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    try:
        # Try to load a font, fallback to default if not available
        title_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24
        )
        label_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14
        )
        small_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12
        )
    except OSError:
        default = ImageFont.load_default()
        title_font = default
        label_font = default
        small_font = default

    if not data:
        # No data available
        draw.text(
            (WIDTH // 2, HEIGHT // 2),
            "No player data available",
            fill=TEXT_COLOR,
            font=label_font,
            anchor="mm",
        )
    else:
        game_data = data[0]
        game_name = game_data.get("name", f"AppID {appid}")

        # Extract monthly data (keys like YYYY-MM)
        monthly_data = []
        for key, value in game_data.items():
            if len(key) == 7 and key[4] == "-" and isinstance(value, (int, float)):
                try:
                    date = datetime.strptime(key, "%Y-%m")
                    monthly_data.append((date, int(value)))
                except ValueError:
                    continue

        monthly_data.sort(key=lambda x: x[0])

        if not monthly_data:
            draw.text(
                (WIDTH // 2, HEIGHT // 2),
                "No monthly player data available",
                fill=TEXT_COLOR,
                font=label_font,
                anchor="mm",
            )
        else:
            dates, values = zip(*monthly_data)

            # Calculate scales
            min_val = min(values)
            max_val = max(values)
            val_range = max_val - min_val if max_val != min_val else 1

            # Draw title
            title = f"Player History: {game_name}"
            draw.text(
                (WIDTH // 2, 30), title, fill=TEXT_COLOR, font=title_font, anchor="mm"
            )

            # Draw axes
            draw.line(
                [(GRAPH_LEFT, GRAPH_BOTTOM), (GRAPH_RIGHT, GRAPH_BOTTOM)],
                fill=GRID_COLOR,
                width=2,
            )
            draw.line(
                [(GRAPH_LEFT, GRAPH_TOP), (GRAPH_LEFT, GRAPH_BOTTOM)],
                fill=GRID_COLOR,
                width=2,
            )

            # Draw Y-axis labels and grid lines
            num_y_ticks = 5
            for i in range(num_y_ticks + 1):
                y_ratio = i / num_y_ticks
                y_pos = GRAPH_BOTTOM - y_ratio * (GRAPH_BOTTOM - GRAPH_TOP)
                val = min_val + y_ratio * val_range

                # Grid line
                if i > 0:
                    draw.line(
                        [(GRAPH_LEFT, y_pos), (GRAPH_RIGHT, y_pos)],
                        fill=GRID_COLOR,
                        width=1,
                    )

                # Label
                label = format_number(int(val))
                draw.text(
                    (GRAPH_LEFT - 10, y_pos),
                    label,
                    fill=TEXT_COLOR,
                    font=small_font,
                    anchor="rm",
                )

            # Calculate points
            graph_width = GRAPH_RIGHT - GRAPH_LEFT
            graph_height = GRAPH_BOTTOM - GRAPH_TOP
            num_points = len(values)

            points = []
            for i, val in enumerate(values):
                x = (
                    GRAPH_LEFT + (i / (num_points - 1)) * graph_width
                    if num_points > 1
                    else GRAPH_LEFT + graph_width / 2
                )
                y_ratio = (val - min_val) / val_range
                y = GRAPH_BOTTOM - y_ratio * graph_height
                points.append((x, y))

            # Draw filled area under line
            if len(points) > 1:
                fill_points = (
                    [(GRAPH_LEFT, GRAPH_BOTTOM)]
                    + list(points)
                    + [(GRAPH_RIGHT, GRAPH_BOTTOM)]
                )

                # Create a mask for the fill
                mask = Image.new("L", (WIDTH, HEIGHT), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.polygon(fill_points, fill=int(255 * FILL_ALPHA))

                # Create colored fill layer
                fill_layer = Image.new("RGB", (WIDTH, HEIGHT), LINE_COLOR)
                img = Image.composite(fill_layer, img, mask)
                draw = ImageDraw.Draw(img)

            # Draw line
            if len(points) > 1:
                draw.line(points, fill=LINE_COLOR, width=3)

            # Draw points
            for x, y in points:
                # White circle with blurple center
                r = 5
                draw.ellipse(
                    [(x - r, y - r), (x + r, y + r)],
                    fill=LINE_COLOR,
                    outline=TEXT_COLOR,
                    width=2,
                )

            # Draw X-axis labels (every nth label to avoid crowding)
            label_interval = max(1, len(dates) // 10)
            for i in range(0, len(dates), label_interval):
                x = points[i][0]
                date_label = dates[i].strftime("%b %Y")
                draw.text(
                    (x, GRAPH_BOTTOM + 15),
                    date_label,
                    fill=TEXT_COLOR,
                    font=small_font,
                    anchor="mm",
                )

            # Add peak annotation
            peak_idx = values.index(max_val)
            peak_x, peak_y = points[peak_idx]
            peak_label = f"Peak: {format_number(max_val)}"
            bbox = draw.textbbox((0, 0), peak_label, font=label_font)
            badge_width = bbox[2] - bbox[0] + 20
            badge_height = bbox[3] - bbox[1] + 10
            badge_x = min(peak_x + 10, GRAPH_RIGHT - badge_width)
            badge_y = max(peak_y - badge_height - 10, GRAPH_TOP)

            draw.rounded_rectangle(
                [(badge_x, badge_y), (badge_x + badge_width, badge_y + badge_height)],
                radius=5,
                fill=PEAK_BADGE_COLOR,
            )
            draw.text(
                (badge_x + badge_width // 2, badge_y + badge_height // 2),
                peak_label,
                fill=TEXT_COLOR,
                font=label_font,
                anchor="mm",
            )

            # Add all-time peak text
            all_time_peak = game_data.get("peak_active_player_all_time")
            if all_time_peak:
                all_time_label = f"All-Time Peak: {format_number(all_time_peak)}"
                bbox = draw.textbbox((0, 0), all_time_label, font=label_font)
                badge_width = bbox[2] - bbox[0] + 20
                badge_height = bbox[3] - bbox[1] + 10
                draw.rounded_rectangle(
                    [
                        (GRAPH_LEFT + 10, GRAPH_TOP + 10),
                        (GRAPH_LEFT + 10 + badge_width, GRAPH_TOP + 10 + badge_height),
                    ],
                    radius=5,
                    fill=ALL_TIME_BADGE_COLOR,
                )
                draw.text(
                    (
                        GRAPH_LEFT + 10 + badge_width // 2,
                        GRAPH_TOP + 10 + badge_height // 2,
                    ),
                    all_time_label,
                    fill=TEXT_COLOR,
                    font=label_font,
                    anchor="mm",
                )

    # Save to buffer
    buffer = BytesIO()
    img.save(buffer, format="PNG", optimize=True)
    buffer.seek(0)

    return discord.File(buffer, filename="player_history.png")
