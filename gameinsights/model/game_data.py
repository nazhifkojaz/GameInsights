from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator
from typing_extensions import Self


class GameDataModel(BaseModel):
    """Complete game data model with Python 3.10+ type hints and Pydantic v2 validation"""

    # Required field
    steam_appid: str

    # Optional fields with defaults (using | instead of Optional)
    name: str | None = Field(default=None)
    developers: list[str] = Field(default_factory=list)
    publishers: list[str] = Field(default_factory=list)
    type: str | None = Field(default=None)
    is_free: bool | None = Field(default=None)
    is_coming_soon: bool | None = Field(default=None)
    recommendations: int | None = Field(default=None)
    discount: float = Field(default=float("nan"), exclude=True)
    price_currency: str | None = Field(default=None)
    price_initial: float = Field(default=float("nan"))
    price_final: float = Field(default=float("nan"))
    metacritic_score: int | None = Field(default=None)
    release_date: datetime | None = Field(default=None)
    days_since_release: int | None = Field(default=None)
    average_playtime_h: float = Field(default=float("nan"), description="in hours", exclude=True)
    average_playtime: int | None = Field(default=None)
    copies_sold: int | None = Field(default=None)
    estimated_revenue: int | None = Field(default=None, description="in USD")
    # TODO: Implement total_revenue field - currently disabled pending data source verification
    # total_revenue: float = Field(default=float("nan"))
    owners: int | None = Field(default=None)
    followers: int | None = Field(
        default=None, description="Steam wishlist/follower count from Gamalytic"
    )
    early_access: bool | None = Field(default=None, description="Whether game is in early access")
    ccu: int | None = Field(default=None)
    active_player_24h: int | None = Field(default=None)
    peak_active_player_all_time: int | None = Field(default=None)
    monthly_active_player: list[dict[str, Any]] = Field(default_factory=list)
    review_score: int | None = Field(default=None)
    review_score_desc: str | None = Field(default=None)
    total_positive: int | None = Field(default=None)
    total_negative: int | None = Field(default=None)
    total_reviews: int | None = Field(default=None)
    achievements_count: int | None = Field(default=None)
    achievements_percentage_average: float = Field(default=float("nan"))
    achievements_list: list[dict[str, Any]] = Field(default_factory=list)
    comp_main: int | None = Field(default=None)
    comp_plus: int | None = Field(default=None)
    comp_100: int | None = Field(default=None)
    comp_all: int | None = Field(default=None)
    comp_main_count: int | None = Field(default=None)
    comp_plus_count: int | None = Field(default=None)
    comp_100_count: int | None = Field(default=None)
    comp_all_count: int | None = Field(default=None)
    invested_co: int | None = Field(default=None)
    invested_mp: int | None = Field(default=None)
    invested_co_count: int | None = Field(default=None)
    invested_mp_count: int | None = Field(default=None)
    count_comp: int | None = Field(default=None)
    count_speed_run: int | None = Field(default=None)
    count_backlog: int | None = Field(default=None)
    count_review: int | None = Field(default=None)
    count_playing: int | None = Field(default=None)
    count_retired: int | None = Field(default=None)
    languages: list[str] = Field(default_factory=list)
    platforms: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    genres: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    content_rating: list[dict[str, Any]] = Field(default_factory=list)

    # ProtonDB fields (Linux/Steam Deck compatibility)
    protondb_tier: str | None = Field(default=None)
    protondb_score: float | None = Field(default=None)
    protondb_trending: str | None = Field(default=None)
    protondb_confidence: str | None = Field(default=None)
    protondb_total: int | None = Field(default=None)

    @field_validator("release_date", mode="before")
    def parse_release_date(cls, v: str | int | float | datetime | None) -> datetime | None:
        """Parse dates in format '%b %d, %Y' (e.g. 'Jun 15, 2023') or ISO 8601 '%Y-%m-%d'"""
        if v is None or isinstance(v, datetime):
            return v
        try:
            if isinstance(v, str):
                # Try ISO 8601 format first (YYYY-MM-DD)
                try:
                    return datetime.strptime(v, "%Y-%m-%d")
                except ValueError:
                    pass
                # Try Steam format (MMM DD, YYYY)
                return datetime.strptime(v, "%b %d, %Y")
            elif isinstance(v, (int, float)):
                return datetime.fromtimestamp(v)
        except (ValueError, TypeError):
            return None

    @field_validator(
        "metacritic_score",
        "copies_sold",
        "estimated_revenue",
        # TODO: Re-enable when total_revenue field is implemented
        # "total_revenue",
        "owners",
        "followers",
        "ccu",
        "active_player_24h",
        "peak_active_player_all_time",
        "review_score",
        "total_positive",
        "total_negative",
        "total_reviews",
        "achievements_count",
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
        "count_playing",
        "count_retired",
        "recommendations",
        "protondb_total",
        mode="before",
    )
    def handle_integers(cls, v: str | int | float | None) -> int | None:
        """convert x types to int"""
        if v is None:
            return None
        try:
            return int(v)
        except (ValueError, TypeError):
            return None

    @field_validator(
        "price_initial",
        "price_final",
        "average_playtime_h",
        "achievements_percentage_average",
        "discount",
        "protondb_score",
        mode="before",
    )
    def handle_float(cls, v: str | int | float | None) -> float:
        """convert x types to float or float("nan")"""
        if v is None:
            return float("nan")
        try:
            return float(v)
        except (ValueError, TypeError):
            return float("nan")

    @field_validator(
        "steam_appid",
        "name",
        "type",
        "protondb_tier",
        "protondb_trending",
        "protondb_confidence",
        mode="before",
    )
    def ensure_string(cls, v: str | None) -> str:
        """convert x types to string"""
        return "" if v is None else str(v)

    @field_validator(
        "developers",
        "publishers",
        "platforms",
        "categories",
        "genres",
        "tags",
        "languages",
        "content_rating",
        "monthly_active_player",
        "achievements_list",
        mode="before",
    )
    def ensure_list(cls, v: list[Any] | str | int | None) -> list[Any]:
        """ensure the fields are always lists (convert single values/none to lists)"""
        if v is None:
            return []
        return v if isinstance(v, list) else [v]

    def get_recap(self) -> dict[str, Any]:
        """Create a reduced model with only recap fields"""
        recap_data = {field: getattr(self, field) for field in self._RECAP_FIELDS}
        return recap_data

    @model_validator(mode="after")
    def preprocess_data(self) -> Self:
        self.compute_average_playtime()
        self.compute_days_since_release()
        return self

    def compute_average_playtime(self) -> None:
        if (
            self.average_playtime_h is not None
            and self.average_playtime_h == self.average_playtime_h
        ):
            self.average_playtime = int(self.average_playtime_h * 3600)

    def compute_days_since_release(self) -> None:
        if self.release_date:
            self.days_since_release = (datetime.now() - self.release_date).days

    _RECAP_FIELDS = {
        "steam_appid",
        "name",
        "developers",
        "publishers",
        "type",
        "release_date",
        "days_since_release",
        "price_currency",
        "price_initial",
        "price_final",
        "copies_sold",
        "estimated_revenue",
        "owners",
        "followers",
        "total_positive",
        "total_negative",
        "total_reviews",
        "comp_main",
        "comp_plus",
        "comp_100",
        "comp_all",
        "invested_co",
        "invested_mp",
        "average_playtime",
        "active_player_24h",
        "peak_active_player_all_time",
        "achievements_count",
        "achievements_percentage_average",
        "categories",
        "genres",
        "tags",
        "is_free",
        # Linux/Steam Deck compatibility
        "protondb_tier",
        # Game state flags
        "early_access",
        # Review scores
        "metacritic_score",
    }
