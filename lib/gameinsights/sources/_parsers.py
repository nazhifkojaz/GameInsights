"""Pure transform / parse functions shared by sync and async source pairs.

Every function in this module is stateless: it accepts raw API/HTML data and
returns a plain dict.  When a function needs to emit diagnostic messages it
exposes an optional ``log_fn`` callback so callers can wire in their own
logger (e.g. ``self.logger.log``) without coupling to BaseSource.

The canonical implementations live here; async twins should delegate to the
same functions instead of duplicating the logic.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Literal

from bs4.element import Tag

from gameinsights.sources._schemas import _HOWLONGTOBEAT_LABELS

# ---------------------------------------------------------------------------
# SteamStore
# ---------------------------------------------------------------------------


def transform_steamstore(data: dict[str, Any]) -> dict[str, Any]:
    """Transform raw Steam Store ``appdetails`` data into a normalised dict."""
    price_overview = data.get("price_overview") or {}
    release_date = data.get("release_date") or {}
    platforms = data.get("platforms") or {}
    genres = data.get("genres") or []
    categories = data.get("categories") or []
    ratings = data.get("ratings") or {}

    return {
        "steam_appid": data.get("steam_appid"),
        "name": data.get("name"),
        "type": data.get("type"),
        "is_coming_soon": release_date.get("coming_soon"),
        "release_date": release_date.get("date"),
        "is_free": data.get("is_free"),
        "price_currency": price_overview.get("currency"),
        "price_initial": (
            price_overview.get("initial") / 100  # type: ignore[operator]
            if isinstance(price_overview, dict) and price_overview.get("initial") is not None
            else None
        ),
        "price_final": (
            price_overview.get("final") / 100  # type: ignore[operator]
            if isinstance(price_overview, dict) and price_overview.get("final") is not None
            else None
        ),
        "developers": data.get("developers"),
        "publishers": data.get("publishers"),
        "platforms": [
            platform
            for platform, is_supported in platforms.items()
            if isinstance(platforms, dict) and is_supported
        ],
        "categories": [category.get("description") for category in categories],
        "genres": [genre.get("description") for genre in genres],
        "metacritic_score": data.get("metacritic", {}).get("score"),
        "recommendations": (
            data.get("recommendations", {}).get("total")
            if isinstance(data.get("recommendations"), dict)
            else data.get("recommendations")
        ),
        "achievements": data.get("achievements", {}).get("total"),
        "content_rating": (
            [
                {"rating_type": rating_type, "rating": rating.get("rating")}
                for rating_type, rating in ratings.items()
                if isinstance(ratings, dict) and isinstance(rating, dict)
            ]
            if ratings
            else []
        ),
    }


# ---------------------------------------------------------------------------
# SteamSpy
# ---------------------------------------------------------------------------


def transform_steamspy(data: dict[str, Any]) -> dict[str, Any]:
    """Transform raw SteamSpy ``appdetails`` data into a normalised dict.

    Fixes the tag-parsing bug present in the async twin: SteamSpy returns
    tags as ``{"TagName": count, ...}`` so we extract ``list(tags.keys())``.
    """
    tags = data.get("tags", [])
    tags = list(tags.keys()) if isinstance(tags, dict) else []

    # Split comma-separated languages string into a proper list
    raw_languages = data.get("languages")
    if isinstance(raw_languages, str):
        languages = [lang.strip() for lang in raw_languages.split(",") if lang.strip()]
    elif isinstance(raw_languages, list):
        languages = raw_languages
    else:
        languages = []

    return {
        "steam_appid": data.get("appid", None),
        "name": data.get("name", None),
        "developers": data.get("developer", None),
        "publishers": data.get("publisher", None),
        "positive_reviews": data.get("positive", None),
        "negative_reviews": data.get("negative", None),
        "owners": data.get("owners", None),
        "average_forever": data.get("average_forever", None),
        "average_playtime_min": data.get("average_forever", None),
        "average_2weeks": data.get("average_2weeks", None),
        "median_forever": data.get("median_forever", None),
        "median_2weeks": data.get("median_2weeks", None),
        "price": data.get("price", None),
        "initial_price": data.get("initialprice", None),
        "discount": data.get("discount", None),
        "ccu": data.get("ccu", None),
        "languages": languages,
        "genres": data.get("genre", None),
        "tags": tags,
    }


# ---------------------------------------------------------------------------
# SteamCharts
# ---------------------------------------------------------------------------


def safe_span_text(element: Tag | None) -> str | None:
    """Safely extract text from a span element inside *element*.

    Args:
        element: A BeautifulSoup Tag that may contain a ``<span>`` child.

    Returns:
        The span's text content, or ``None`` if element/span is missing.
    """
    if element is None:
        return None
    span = element.span
    if span is None:
        return None
    return span.get_text()


def transform_steamcharts(
    data: dict[str, Any],
    log_fn: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Transform parsed SteamCharts HTML elements into a normalised dict.

    Args:
        data: Dict with keys ``game_name`` (Tag), ``peak_data`` (list[Tag]),
            ``player_data_rows`` (list[Tag]).
        log_fn: Optional logger callback for warning messages about
            unexpected row structures.

    Returns:
        Normalised dict with name, active/peak player counts, and monthly data.
    """
    game_name_text = data["game_name"].get_text()
    active_24h = safe_span_text(data["peak_data"][1])
    peak_active = safe_span_text(data["peak_data"][2])

    monthly_active_player: list[dict[str, Any]] = []
    for row in data.get("player_data_rows", []):
        cols = [col.get_text(strip=True) for col in row.find_all("td")]
        if len(cols) != 5:
            if log_fn is not None:
                log_fn(f"Unexpected row structure: expected 5 cells, got {len(cols)}")
            continue
        month, avg_players, gain, percentage_gain, peak_players = cols

        monthly_active_player.append(
            {
                "month": datetime.strptime(month, "%B %Y").strftime("%Y-%m"),
                "average_players": float(avg_players.replace(",", "")),
                "gain": float(gain.replace(",", "")) if gain not in ("-", "") else None,
                "percentage_gain": (
                    float(percentage_gain.replace("%", "").replace(",", "").strip())
                    if percentage_gain not in ("-", "")
                    else 0
                ),
                "peak_players": float(peak_players.replace(",", "")),
            }
        )

    return {
        "name": game_name_text,
        "active_player_24h": int(active_24h) if active_24h else None,
        "peak_active_player_all_time": int(peak_active) if peak_active else None,
        "monthly_active_player": monthly_active_player,
    }


# ---------------------------------------------------------------------------
# ProtonDB
# ---------------------------------------------------------------------------


def transform_protondb(data: dict[str, Any]) -> dict[str, Any]:
    """Transform ProtonDB API summary into the expected format."""
    return {
        "protondb_tier": data.get("tier"),
        "protondb_score": data.get("score"),
        "protondb_trending": data.get("trendingTier"),
        "protondb_confidence": data.get("confidence"),
        "protondb_total": data.get("total"),
    }


# ---------------------------------------------------------------------------
# SteamReview
# ---------------------------------------------------------------------------


def transform_steamreview(
    data: dict[str, Any],
    data_type: Literal["summary", "review"] = "summary",
) -> dict[str, Any]:
    """Transform Steam review data depending on *data_type*.

    Args:
        data: Raw dict from the Steam reviews API.  For ``"summary"`` this is
            the ``query_summary`` object; for ``"review"`` it is a single
            review entry.
        data_type: ``"summary"`` for aggregate review numbers,
            ``"review"`` for an individual review entry.

    Returns:
        Normalised dict with the appropriate fields.
    """
    if data_type == "summary":
        return {
            "review_score": data.get("review_score", None),
            "review_score_desc": data.get("review_score_desc", None),
            "total_positive": data.get("total_positive", None),
            "total_negative": data.get("total_negative", None),
            "total_reviews": data.get("total_reviews", None),
        }
    else:
        author = data.get("author", {})
        return {
            "recommendation_id": data.get("recommendationid", None),
            "author_steamid": author.get("steamid", None),
            "author_num_games_owned": author.get("num_games_owned", None),
            "author_num_reviews": author.get("num_reviews", None),
            "author_playtime_forever": author.get("playtime_forever", None),
            "author_playtime_last_two_weeks": author.get("playtime_last_two_weeks", None),
            "author_playtime_at_review": author.get("playtime_at_review", None),
            "author_last_played": author.get("last_played", None),
            "language": data.get("language", None),
            "review": data.get("review", None),
            "timestamp_created": data.get("timestamp_created", None),
            "timestamp_updated": data.get("timestamp_updated", None),
            "voted_up": data.get("voted_up", None),
            "votes_up": data.get("votes_up", None),
            "votes_funny": data.get("votes_funny", None),
            "weighted_vote_score": data.get("weighted_vote_score", None),
            "comment_count": data.get("comment_count", None),
            "steam_purchase": data.get("steam_purchase", None),
            "received_for_free": data.get("received_for_free", None),
            "written_during_early_access": data.get("written_during_early_access", None),
            "primarily_steam_deck": data.get("primarily_steam_deck", None),
        }


# ---------------------------------------------------------------------------
# SteamAchievements
# ---------------------------------------------------------------------------


def calculate_average_percentage(
    achievements: list[dict[str, Any]],
    log_fn: Callable[[str], None] | None = None,
) -> tuple[list[dict[str, Any]], int, float]:
    """Process raw achievement percentage entries.

    Args:
        achievements: Non-empty list of achievement dicts from
            ``GetGlobalAchievementPercentagesForApp``.
        log_fn: Optional logger callback for debug messages about dropped
            entries.

    Returns:
        A 3-tuple of (transformed list, count, average percentage).
    """
    transformed: list[dict[str, Any]] = []
    total = 0.0
    dropped = 0

    for entry in achievements:
        try:
            percentage = float(entry["percent"])
            transformed.append({"name": entry["name"], "percent": percentage})
            total += percentage
        except (KeyError, ValueError):
            dropped += 1
            continue

    if dropped and log_fn is not None:
        log_fn(f"Dropped {dropped} achievement entries due to missing/invalid fields")

    count = len(transformed)
    average = round(total / count, 2) if count > 0 else 0.0
    return transformed, count, average


def merge_achievements(
    base_achievements: list[dict[str, Any]],
    schema_data: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Merge base achievements (name, percentage) with schema data.

    Args:
        base_achievements: List from ``GetGlobalAchievementPercentagesForApp``.
        schema_data: List from ``GetSchemaForGame``.

    Returns:
        Merged list where each entry has ``name``, ``percent``,
        ``display_name``, ``hidden``, and ``description``.
    """
    # schema lookup by name
    schema_lookup: dict[str, dict[str, Any]] = {}
    for entry in schema_data:
        name = entry.get("name")
        display_name = entry.get("displayName")

        # skip bad structure (if any)
        if not name or not display_name:
            continue

        schema_lookup[name] = {
            "display_name": display_name,
            "hidden": entry.get("hidden"),
            "description": entry.get("description"),
        }

    # Merge with base achievements
    merged: list[dict[str, Any]] = []
    for acv in base_achievements:
        name = acv["name"]
        percent = acv["percent"]

        schema_info = schema_lookup.get(name, {})

        merged.append(
            {
                "name": name,
                "percent": percent,
                "display_name": schema_info.get("display_name", None),
                "hidden": schema_info.get("hidden", None),
                "description": schema_info.get("description", None),
            }
        )

    return merged


def transform_steamachievements(
    data: dict[str, Any],
    schema_data: dict[str, Any] | None = None,
    log_fn: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Transform achievement percentage data (optionally merged with schema).

    Args:
        data: Raw response from ``GetGlobalAchievementPercentagesForApp``.
        schema_data: Optional raw response from ``GetSchemaForGame``.
        log_fn: Optional logger callback for debug messages.

    Returns:
        Dict with ``achievements_count``, ``achievements_percentage_average``,
        and ``achievements_list``.
    """
    percentage_data = data.get("achievementpercentages", {}).get("achievements", [])
    if not percentage_data:
        return {
            "achievements_count": None,
            "achievements_percentage_average": None,
            "achievements_list": None,
        }

    base_achievements, achievements_count, achievements_percentage_average = (
        calculate_average_percentage(percentage_data, log_fn=log_fn)
    )

    schema_achievements = (
        schema_data.get("game", {}).get("availableGameStats", {}).get("achievements", [])
        if schema_data
        else None
    )

    # merge achievements
    achievements_list = (
        merge_achievements(base_achievements=base_achievements, schema_data=schema_achievements)
        if schema_achievements
        else base_achievements
    )

    return {
        "achievements_count": achievements_count,
        "achievements_percentage_average": achievements_percentage_average,
        "achievements_list": achievements_list,
    }


# ---------------------------------------------------------------------------
# SteamUser
# ---------------------------------------------------------------------------


def transform_steamuser(
    data: dict[str, Any],
    data_type: Literal["summary", "games_owned", "recent_games"] = "summary",
) -> dict[str, Any]:
    """Transform SteamUser data depending on *data_type*.

    Args:
        data: Raw dict from the relevant Steam API endpoint.
        data_type: ``"summary"`` for player profile, ``"games_owned"`` for
            owned games list, ``"recent_games"`` for recently played games.

    Returns:
        Normalised dict with the appropriate fields.
    """
    if data_type == "games_owned":
        return {
            "game_count": data.get("game_count", 0),
            "games": data.get("games", []),
        }
    elif data_type == "recent_games":
        total_playtime_2weeks = 0
        games = data.get("games", [])
        games_data: list[dict[str, Any]] = []

        for game in games:
            game_dict = {
                "appid": game.get("appid", None),
                "name": game.get("name", None),
                "playtime_2weeks": game.get("playtime_2weeks", 0),
                "playtime_forever": game.get("playtime_forever", 0),
            }
            total_playtime_2weeks += game_dict["playtime_2weeks"]
            games_data.append(game_dict)

        return {
            "games_count": data.get("total_count", 0),
            "total_playtime_2weeks": total_playtime_2weeks,
            "games": games_data,
        }
    else:
        return {
            "steamid": data.get("steamid", None),
            "community_visibility_state": data.get("communityvisibilitystate", 1),
            "profile_state": data.get("profilestate", None),
            "persona_name": data.get("personaname", None),
            "profile_url": data.get("profileurl", None),
            "last_log_off": data.get("lastlogoff", None),
            "real_name": data.get("realname", None),
            "time_created": data.get("timecreated", None),
            "loc_country_code": data.get("loccountrycode", None),
            "loc_state_code": data.get("locstatecode", None),
            "loc_city_id": data.get("loccityid", None),
        }


# ---------------------------------------------------------------------------
# HowLongToBeat
# ---------------------------------------------------------------------------


def generate_search_payload(game_name: str) -> dict[str, Any]:
    """Generate the HLTB search payload for a game name.

    Args:
        game_name: The game name to search for.

    Returns:
        The payload dict for the ``/api/find`` POST request.
    """
    return {
        "searchType": "games",
        "searchTerms": game_name.split(),
        "searchPage": 1,
        "size": 1,
        "searchOptions": {
            "games": {
                "userId": 0,
                "platform": "",
                "sortCategory": "popular",
                "rangeCategory": "main",
                "rangeTime": {"min": 0, "max": 0},
                "gameplay": {
                    "perspective": "",
                    "flow": "",
                    "genre": "",
                    "difficulty": "",
                },
                "rangeYear": {"max": "", "min": ""},
                "modifier": "",
            },
            "users": {"sortCategory": "postcount"},
            "lists": {"sortCategory": "follows"},
            "filter": "",
            "sort": 0,
            "randomizer": 0,
        },
        "useCache": True,
    }


def extract_hltb_game_data(
    html_text: str,
    game_id: int,
    log_fn: Callable[[str], None] | None = None,
) -> dict[str, Any] | None:
    """Extract game data from a HowLongToBeat game page's ``__NEXT_DATA__``.

    This is the pure parsing portion of ``_fetch_game_page``.  The caller is
    responsible for making the HTTP request and passing the response body.

    Args:
        html_text: The full HTML of the game page.
        game_id: The HLTB game ID (used in log messages).
        log_fn: Optional logger callback for debug messages about parse
            failures.

    Returns:
        The game data dict, or ``None`` if extraction failed.
    """
    import json
    import re
    from typing import cast

    match = re.search(
        r'<script id="__NEXT_DATA__".*?>(.*?)</script>',
        html_text,
        re.DOTALL,
    )
    if match:
        try:
            next_data = json.loads(match.group(1))
            # Navigate the nested structure safely
            game_data = (
                next_data.get("props", {}).get("pageProps", {}).get("game", {}).get("data", {})
            )
            game_list = game_data.get("game")
            if isinstance(game_list, list) and len(game_list) > 0:
                return cast(dict[str, Any], game_list[0])
        except (json.JSONDecodeError, KeyError, IndexError) as exc:
            if log_fn is not None:
                log_fn(f"HLTB __NEXT_DATA__ parse failed for game {game_id}: {exc}")

    return None


def transform_howlongtobeat(data: dict[str, Any]) -> dict[str, Any]:
    """Transform raw HLTB game data into a normalised dict.

    Time values (in seconds) are converted to minutes.  Base time labels
    (``comp_main``, etc.) are mapped to their ``_avg`` counterparts which
    represent the average completion time shown on the website.

    Args:
        data: The raw game data from HLTB (full page data or search result).

    Returns:
        Dict with only the valid labels, time values converted to minutes.
    """
    from typing import cast

    result: dict[str, Any] = {}
    time_labels = {
        "comp_main",
        "comp_plus",
        "comp_100",
        "comp_all",
        "invested_co",
        "invested_mp",
    }
    for label in _HOWLONGTOBEAT_LABELS:
        raw_value: Any = None

        # Map time labels to their '_avg' counterparts (average completion time)
        if label in ("comp_main", "comp_plus", "comp_100", "comp_all"):
            avg_label = f"{label}_avg"
            raw_value = data.get(avg_label)
        elif label in ("invested_co", "invested_mp"):
            avg_label = f"{label}_avg"
            raw_value = data.get(avg_label)
        else:
            raw_value = data.get(label, None)

        if raw_value is not None and label in time_labels:
            result[label] = cast(int, raw_value) // 60
        else:
            result[label] = raw_value
    return result
