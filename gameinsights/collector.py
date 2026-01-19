import time
from typing import Any, Literal, NamedTuple

import pandas as pd

from gameinsights import sources
from gameinsights.model.game_data import GameDataModel
from gameinsights.sources.base import SourceResult
from gameinsights.utils import LoggerWrapper, metrics
from gameinsights.utils.ratelimit import logged_rate_limited


class SourceConfig(NamedTuple):
    source: sources.BaseSource
    fields: list[str]


class Collector:
    def __init__(
        self,
        region: str = "us",
        language: str = "english",
        steam_api_key: str | None = None,
        gamalytic_api_key: str | None = None,
        calls: int = 60,
        period: int = 60,
    ) -> None:
        """Initialize the collector with an optional API key.
        Args:
            region (str): Region for the API request. Default is "us".
            language (str): Language for the API request. Default is "english".
            steam_api_key (str): Optional API key for Steam API.
            gamalytic_api_key (str): Optional API key for Gamalytic API.
            calls (int): Max number of API calls allowed per period. Default is 60.
            period (int): Time period in seconds for the rate limit. Default is 60.
        """
        self._region = region
        self._language = language
        self._steam_api_key = steam_api_key
        self._gamalytic_api_key = gamalytic_api_key
        self.calls = calls
        self.period = period

        self._init_sources()
        self._init_sources_config()

        self._logger = LoggerWrapper(self.__class__.__name__)

    @property
    def logger(self) -> "LoggerWrapper":
        return self._logger

    def _init_sources(self) -> None:
        """Initialize the sources with the current settings."""
        self.steamreview = sources.SteamReview()
        self.steamstore = sources.SteamStore(
            region=self.region, language=self.language, api_key=self.steam_api_key
        )
        self.steamspy = sources.SteamSpy()
        self.gamalytic = sources.Gamalytic(api_key=self.gamalytic_api_key)
        self.steamcharts = sources.SteamCharts()
        self.howlongtobeat = sources.HowLongToBeat()
        self.steamachievements = sources.SteamAchievements(api_key=self.steam_api_key)
        self.steamuser = sources.SteamUser(api_key=self.steam_api_key)

    def _init_sources_config(self) -> None:
        """Initialize sources config."""
        self._id_based_sources = [
            SourceConfig(
                self.steamstore,
                [
                    "steam_appid",
                    "name",
                    "developers",
                    "publishers",
                    "type",
                    "price_currency",
                    "price_initial",
                    "price_final",
                    "categories",
                    "platforms",
                    "genres",
                    "metacritic_score",
                    "release_date",
                    "content_rating",
                    "is_free",
                    "is_coming_soon",
                    "recommendations",
                ],
            ),
            SourceConfig(
                self.gamalytic,
                ["average_playtime_h", "copies_sold", "estimated_revenue", "owners", "languages"],
            ),
            SourceConfig(self.steamspy, ["ccu", "tags", "discount"]),
            SourceConfig(
                self.steamcharts,
                ["active_player_24h", "peak_active_player_all_time", "monthly_active_player"],
            ),
            SourceConfig(
                self.steamreview,
                [
                    "review_score",
                    "review_score_desc",
                    "total_positive",
                    "total_negative",
                    "total_reviews",
                ],
            ),
            SourceConfig(
                self.steamachievements,
                [
                    "achievements_count",
                    "achievements_percentage_average",
                    "achievements_list",
                ],
            ),
        ]

        self._name_based_sources = [
            SourceConfig(
                self.howlongtobeat,
                [
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
                    "count_speedrun",
                    "count_backlog",
                    "count_review",
                    "review_score",
                    "count_playing",
                    "count_retired",
                ],
            ),
        ]

    @property
    def id_based_sources(self) -> list[SourceConfig]:
        return self._id_based_sources

    @property
    def name_based_sources(self) -> list[SourceConfig]:
        return self._name_based_sources

    @property
    def region(self) -> str:
        return self._region

    @region.setter
    def region(self, value: str) -> None:
        if self._region != value:
            self._region = value
            self.steamstore.region = value

    @property
    def language(self) -> str:
        return self._language

    @language.setter
    def language(self, value: str) -> None:
        if self._language != value:
            self._language = value
            self.steamstore.language = value

    @property
    def steam_api_key(self) -> str | None:
        return self._steam_api_key

    @steam_api_key.setter
    def steam_api_key(self, value: str) -> None:
        if self._steam_api_key != value:
            self._steam_api_key = value
            self.steamstore.api_key = value
            self.steamachievements.api_key = value
            self.steamuser.api_key = value

    @property
    def gamalytic_api_key(self) -> str | None:
        return self._gamalytic_api_key

    @gamalytic_api_key.setter
    def gamalytic_api_key(self, value: str) -> None:
        if self._gamalytic_api_key != value:
            self._gamalytic_api_key = value
            self.gamalytic.api_key = value

    def get_user_data(
        self,
        steamids: str | list[str],
        include_free_games: bool = True,
        return_as: Literal["list", "dataframe"] = "dataframe",
        verbose: bool = True,
    ) -> list[dict[str, Any]] | pd.DataFrame:
        """Fetch user data from provided steamids.
        Args:
            steamids (str | list[str]): Either a single or a list of 64bit SteamIDs
            include_free_games (bool): If True, will include free games when fetching users' owned games list. Default to True.
            return_as (str): Return format, "list" for list of dicts, "dataframe" for pandas DataFrame. Default to "dataframe".
            verbose (bool): If True, will log the fetching process.
        """
        steamid_list = (
            [steamids] if isinstance(steamids, str) or isinstance(steamids, int) else steamids
        )

        results = []
        total = len(steamid_list)

        for idx, steamid in enumerate(steamid_list, start=1):
            self.logger.log(
                f"Fetching {idx} of {total}: user with steamid {steamid}",
                level="info",
                verbose=verbose,
            )

            try:
                fetch_result = self.steamuser.fetch(
                    steamid=steamid, include_free_games=include_free_games, verbose=verbose
                )
                if fetch_result["success"]:
                    user_data = fetch_result["data"]
                    results.append(user_data)
                else:
                    user_data = {"steamid": steamid}
                    results.append(user_data)

                time.sleep(0.25)  # internal sleep to prevent over-calling
            except Exception:
                self.logger.log(
                    f"Error fetching data for steamid {steamid}: e", level="error", verbose=True
                )

        if return_as == "dataframe":
            return pd.DataFrame(results)

        return results

    def get_games_data(
        self, steam_appids: str | list[str], recap: bool = False, verbose: bool = True
    ) -> list[dict[str, Any]]:
        """Fetch game recap data.
        Game recap data includes game appid, name, release date, days since released, price and its currency, developer, publisher, genres, positive and negative reviews, review ratio, copies sold, estimated revenue, active players in the last 24 hours and in all time.
        Args:
            steam_appids (str): steam_appid of the game(s) to fetch data for.
            recap (bool): If True, will return the recap data (for reference: check _RECAP_LABELS).
            verbose (bool): If True, will log the fetching process.

        Returns:
            list[dict[str, Any]]: List of games recap data.

        Behavior:
            - Returns an empty list if no data could be fetched.
            - Returns complete/partial data if all/any appids succeed.
        """

        if not steam_appids:
            return []

        if isinstance(steam_appids, (str, int)):
            steam_appids = [steam_appids]

        result = []
        total = len(steam_appids)
        for idx, appid in enumerate(steam_appids, start=1):
            self.logger.log(
                f"Fetching {idx} of {total} game data: steam appid {appid}..",
                level="info",
                verbose=verbose,
            )
            try:
                game_data = self._fetch_raw_data(appid, verbose=verbose)
                payload = game_data.get_recap() if recap else game_data.model_dump()
                result.append(payload)
            except Exception as e:
                self.logger.log(
                    f"Error fecthing data for game {appid} with {e} error..",
                    level="error",
                    verbose=True,
                )

        return result

    def get_games_active_player_data(
        self, steam_appids: str | list[str], fill_na_as: int = -1, verbose: bool = True
    ) -> pd.DataFrame:
        """Fetch active player data for multiple appids.
        Args:
            appids (list[str]): List of appids to fetch active player data for.
            fill_na_as (int): Value to fill NaN values in the DataFrame. Default is -1.
            verbose (str): If True, will log the fetching process.

        Returns:
            pd.DataFrame: DataFrame containing active player data for all appids.
        """

        if not steam_appids:
            return pd.DataFrame()
        if isinstance(steam_appids, (str, int)):
            steam_appids = [steam_appids]

        all_months: set[str] = set()
        all_data = []
        total = len(steam_appids)

        for idx, appid in enumerate(steam_appids, start=1):
            self.logger.log(
                f"Fetching {idx} of {total}: active player data for appid {appid}..",
                level="info",
                verbose=verbose,
            )
            game_record = {
                "steam_appid": appid,
            }

            try:
                active_player_data = self.steamcharts.fetch(
                    appid,
                    verbose=verbose,
                    selected_labels=[
                        "name",
                        "peak_active_player_all_time",
                        "monthly_active_player",
                    ],
                )

                if active_player_data.get("success"):
                    monthly_data = {
                        month["month"]: month["average_players"]
                        for month in active_player_data["data"].get("monthly_active_player", [])
                    }
                    game_record.update(monthly_data)
                    game_record.update(
                        {
                            "name": active_player_data["data"].get("name"),
                            "peak_active_player_all_time": (
                                active_player_data["data"].get("peak_active_player_all_time")
                            ),
                        }
                    )
                    all_months.update(monthly_data.keys())
            except Exception as e:
                self.logger.log(
                    f"Error fetching active player data for appid {appid}: {e}",
                    level="error",
                    verbose=True,
                )
            all_data.append(game_record)

        # sort the months chronologically
        sorted_months = sorted(all_months)

        # create a dataframe with all months as columns
        df = pd.DataFrame(
            all_data,
            columns=["steam_appid", "name", "peak_active_player_all_time"] + sorted_months,
        )

        # fill NaN values with the specified value
        df.fillna(fill_na_as, inplace=True)

        return df

    def get_game_review(
        self, steam_appid: str, verbose: bool = True, review_only: bool = True
    ) -> pd.DataFrame:
        if not steam_appid:
            raise ValueError("steam_appid must be a non-empty.")

        self.logger.log(
            f"Fetching reviews for appid {steam_appid}..",
            level="info",
            verbose=verbose,
        )

        try:
            reviews_data = self.steamreview.fetch(
                steam_appid=steam_appid,
                verbose=verbose,
                filter="recent",
                language="all",
                review_type="all",
                purchase_type="all",
                mode="review",
            )

            if reviews_data["success"]:
                if review_only:
                    return pd.DataFrame(reviews_data["data"]["reviews"])
                else:
                    return pd.DataFrame([reviews_data["data"]])
        except Exception as e:
            self.logger.log(
                f"Error fetching reviews for appid {steam_appid}: {e}", level="error", verbose=True
            )
        return pd.DataFrame([])

    @logged_rate_limited()
    def _fetch_raw_data(self, steam_appid: str, verbose: bool = True) -> "GameDataModel":
        """Fetch game data from all sources based on appid.
        Args:
            steam_appid (str): The appid of the game to fetch data for.
            verbose (bool: If True, will log the fetching process

        Returns:
            dict: The combined game data from all sources.
        """
        identifier = str(steam_appid)
        raw_data: dict[str, Any] = {"steam_appid": identifier}

        for config in self.id_based_sources:
            source_data = self._fetch_with_observability(
                config.source,
                identifier=identifier,
                scope="id",
                verbose=verbose,
            )
            if source_data["success"]:
                raw_data.update({key: source_data["data"][key] for key in config.fields})

        # if the game name doesn't exist, then the game is not available
        game_name = raw_data.get("name", None)
        if game_name:
            for config in self.name_based_sources:
                source_data = self._fetch_with_observability(
                    config.source,
                    identifier=game_name,
                    scope="name",
                    verbose=verbose,
                )
                if source_data["success"]:
                    raw_data.update({key: source_data["data"][key] for key in config.fields})

        return GameDataModel(**raw_data)

    def _fetch_with_observability(
        self,
        source: sources.BaseSource,
        identifier: str,
        scope: Literal["id", "name"],
        verbose: bool,
    ) -> SourceResult:
        source_name = source.__class__.__name__
        source.logger.log_event(
            "source_fetch_start",
            verbose=verbose,
            scope=scope,
            identifier=identifier,
        )

        try:
            with metrics.timer(
                "source_fetch_duration_seconds",
                source=source_name,
                scope=scope,
            ) as timing:
                result = source.fetch(identifier, verbose=verbose)
        except Exception as exc:
            metrics.counter("source_fetch_exception_total", source=source_name, scope=scope)
            source.logger.log_event(
                "source_fetch_exception",
                level="error",
                verbose=True,
                scope=scope,
                identifier=identifier,
                error=str(exc),
            )
            raise

        duration_ms = round(timing.duration * 1000, 2)
        metrics.counter("source_fetch_total", source=source_name, scope=scope)
        if result["success"]:
            metrics.counter("source_fetch_success_total", source=source_name, scope=scope)
        else:
            metrics.counter("source_fetch_error_total", source=source_name, scope=scope)

        source.logger.log_event(
            "source_fetch_complete",
            verbose=verbose,
            scope=scope,
            identifier=identifier,
            success=result["success"],
            duration_ms=duration_ms,
        )

        return result
