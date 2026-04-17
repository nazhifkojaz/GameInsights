"""TypedDict definitions for structured data flowing through the pipeline."""

from typing import Any, TypedDict


class MonthlyActivePlayer(TypedDict):
    month: str
    average_players: float
    gain: float | None
    percentage_gain: float
    peak_players: float


class AchievementEntry(TypedDict, total=False):
    name: str
    percent: float
    display_name: str | None
    hidden: int | None
    description: str | None


class ContentRating(TypedDict):
    rating_type: str
    rating: str | None


# --- SteamReview types ---


class ReviewSummary(TypedDict, total=False):
    review_score: int | None
    review_score_desc: str | None
    total_positive: int | None
    total_negative: int | None
    total_reviews: int | None


class ReviewEntry(TypedDict, total=False):
    recommendation_id: str | None
    author_steamid: str | None
    author_num_games_owned: int | None
    author_num_reviews: int | None
    author_playtime_forever: int | None
    author_playtime_last_two_weeks: int | None
    author_playtime_at_review: int | None
    author_last_played: int | None
    language: str | None
    review: str | None
    timestamp_created: int | None
    timestamp_updated: int | None
    voted_up: bool | None
    votes_up: int | None
    votes_funny: int | None
    weighted_vote_score: float | None
    comment_count: int | None
    steam_purchase: bool | None
    received_for_free: bool | None
    written_during_early_access: bool | None
    primarily_steam_deck: bool | None


# --- HowLongToBeat types ---


class HLTBGameData(TypedDict, total=False):
    game_id: int | None
    game_name: str | None
    game_type: str | None
    comp_main: int | None
    comp_plus: int | None
    comp_100: int | None
    comp_all: int | None
    comp_main_count: int | None
    comp_plus_count: int | None
    comp_100_count: int | None
    comp_all_count: int | None
    invested_co: int | None
    invested_mp: int | None
    invested_co_count: int | None
    invested_mp_count: int | None
    count_comp: int | None
    count_speed_run: int | None
    count_backlog: int | None
    count_review: int | None
    review_score: int | None
    count_playing: int | None
    count_retired: int | None


# --- SteamUser types ---


class SteamUserSummary(TypedDict, total=False):
    steamid: str | None
    community_visibility_state: int
    profile_state: int | None
    persona_name: str | None
    profile_url: str | None
    last_log_off: int | None
    real_name: str | None
    time_created: int | None
    loc_country_code: str | None
    loc_state_code: str | None
    loc_city_id: int | None


class SteamUserOwnedGames(TypedDict, total=False):
    game_count: int
    games: list[dict[str, Any]]


class SteamUserRecentGames(TypedDict, total=False):
    games_count: int
    total_playtime_2weeks: int
    games: list[dict[str, Any]]


# --- Recap type ---


class GameDataRecap(TypedDict, total=False):
    steam_appid: str
    name: str | None
    developers: list[str]
    publishers: list[str]
    type: str | None
    release_date: str | None
    days_since_release: int | None
    price_currency: str | None
    price_initial: float | None
    price_final: float | None
    copies_sold: int | None
    estimated_revenue: int | None
    owners: int | None
    followers: int | None
    total_positive: int | None
    total_negative: int | None
    total_reviews: int | None
    comp_main: int | None
    comp_plus: int | None
    comp_100: int | None
    comp_all: int | None
    invested_co: int | None
    invested_mp: int | None
    average_playtime: int | None
    active_player_24h: int | None
    peak_active_player_all_time: int | None
    achievements_count: int | None
    achievements_percentage_average: float | None
    categories: list[str]
    genres: list[str]
    tags: list[str]
    is_free: bool | None
    protondb_tier: str | None
    early_access: bool | None
    metacritic_score: int | None
