"""Constants for the Discord bot."""

# Steam Store URL template
STEAM_STORE_URL_TEMPLATE = "https://store.steampowered.com/app/{appid}"

# Steam user status mapping
STEAM_STATUS_MAP: dict[int, str] = {
    0: "Offline",
    1: "Online",
    2: "Busy",
    3: "Away",
    4: "Snooze",
    5: "Looking to Trade",
    6: "Looking to Play",
}

# API endpoint URLs
API_ENDPOINTS = {
    "game": "/games/{appid}",
    "game_recap": "/games/{appid}/recap",
    "reviews": "/games/{appid}/reviews",
    "active_players": "/games/{appid}/active-players",
    "user": "/users/{steamid}",
}
