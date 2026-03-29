from enum import Enum


class Endpoint(str, Enum):
    """API endpoint identifiers for caching and routing."""

    GAME = "game"
    GAME_RECAP = "game_recap"
    GAME_REVIEWS = "game_reviews"
    GAME_PLAYERS = "game_players"
    USER = "user"


# TTL values in seconds
ENDPOINT_TTL: dict[Endpoint, int] = {
    Endpoint.GAME: 21600,
    Endpoint.GAME_RECAP: 21600,
    Endpoint.GAME_REVIEWS: 43200,
    Endpoint.GAME_PLAYERS: 3600,
    Endpoint.USER: 86400,
}
