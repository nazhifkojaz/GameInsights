"""Shared schema definitions for sync and async source pairs.

Label tuples, authentication types, and response TypedDicts that are
identical between sync and async source implementations.
"""

from __future__ import annotations

from enum import IntEnum
from typing import Any, NamedTuple, TypedDict

# --- SteamStore ---
_STEAM_LABELS = (
    "steam_appid",
    "name",
    "type",
    "is_free",
    "developers",
    "publishers",
    "price_currency",
    "price_initial",
    "price_final",
    "platforms",
    "categories",
    "genres",
    "metacritic_score",
    "recommendations",
    "achievements",
    "is_coming_soon",
    "release_date",
    "content_rating",
)

# --- SteamSpy ---
_STEAMSPY_LABELS = (
    "steam_appid",
    "name",
    "developers",
    "publishers",
    "positive_reviews",
    "negative_reviews",
    "owners",
    "average_forever",
    "average_playtime_min",
    "average_2weeks",
    "median_forever",
    "median_2weeks",
    "price",
    "initial_price",
    "discount",
    "ccu",
    "languages",
    "genres",
    "tags",
)

# --- SteamCharts ---
_STEAMCHARTS_LABELS = (
    "steam_appid",
    "name",
    "active_player_24h",
    "peak_active_player_all_time",
    "monthly_active_player",
)

# --- ProtonDB ---
_PROTONDB_LABELS = (
    "protondb_tier",
    "protondb_score",
    "protondb_trending",
    "protondb_confidence",
    "protondb_total",
)

# --- SteamAchievements ---
_STEAMACHIEVEMENT_LABELS = (
    "achievements_count",
    "achievements_percentage_average",
    "achievements_list",
)

# --- SteamReview ---
_STEAMREVIEW_SUMMARY_LABELS = (
    "review_score",
    "review_score_desc",
    "total_positive",
    "total_negative",
    "total_reviews",
)

_STEAMREVIEW_REVIEW_LABELS = (
    "recommendation_id",
    "author_steamid",
    "author_num_games_owned",
    "author_num_reviews",
    "author_playtime_forever",
    "author_playtime_last_two_weeks",
    "author_playtime_at_review",
    "author_last_played",
    "language",
    "review",
    "timestamp_created",
    "timestamp_updated",
    "voted_up",
    "votes_up",
    "votes_funny",
    "weighted_vote_score",
    "comment_count",
    "steam_purchase",
    "received_for_free",
    "written_during_early_access",
    "primarily_steam_deck",
)


class SteamReviewResponse(TypedDict):
    success: bool
    cursor: str | None
    reviews: list[dict[str, Any]]
    query_summary: dict[str, Any]


# --- SteamUser ---
_STEAMUSER_LABELS = (
    "steamid",
    "community_visibility_state",
    "profile_state",
    "persona_name",
    "profile_url",
    "last_log_off",
    "real_name",
    "time_created",
    "loc_country_code",
    "loc_state_code",
    "loc_city_id",
    "owned_games",
    "recently_played_games",
)


class CommunityVisibilityState(IntEnum):
    PUBLIC = 3


# --- HowLongToBeat ---
_HOWLONGTOBEAT_LABELS = (
    "game_id",
    "game_name",
    "game_type",
    "comp_main",
    "comp_plus",
    "comp_100",
    "comp_all",
    "comp_main_count",
    "comp_plus_count",
    "comp_100_count",
    "comp_all_count",
    "invested_co",
    "invested_mp",
    "invested_co_count",
    "invested_mp_count",
    "count_comp",
    "count_speed_run",
    "count_backlog",
    "count_review",
    "review_score",
    "count_playing",
    "count_retired",
)


class _SearchAuth(NamedTuple):
    """Authentication data extracted from HLTB init endpoint.

    Known fields (token, hp_key, hp_val) are explicit for clarity.
    The extras dict carries any future auth fields HLTB adds to the
    init response, forwarding them automatically to search requests.
    """

    token: str
    hp_key: str
    hp_val: str
    user_agent: str
    extras: dict[str, str]
