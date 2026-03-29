from pydantic import BaseModel, ConfigDict, field_validator
from typing import Any


class BatchRequest(BaseModel):
    appids: list[str]
    recap: bool = False

    @field_validator("appids")
    def validate_appids(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("appids must not be empty")
        if len(v) > 10:
            raise ValueError("Maximum 10 appids per batch")
        return v


class GameResponse(BaseModel):
    """Response model for game data."""

    model_config = ConfigDict(extra="allow")

    steam_appid: str
    name: str


class SearchResult(BaseModel):
    """Response model for game search results."""

    appid: str
    name: str
    search_score: float


class ReviewsResponse(BaseModel):
    """Response model for game reviews."""

    model_config = ConfigDict(extra="allow")

    reviews: list[dict[str, Any]]


class PlayersResponse(BaseModel):
    """Response model for player count data."""

    model_config = ConfigDict(extra="allow")

    name: str


class BatchGamesResponse(BaseModel):
    """Response model for batch game requests."""

    games: list[GameResponse]
