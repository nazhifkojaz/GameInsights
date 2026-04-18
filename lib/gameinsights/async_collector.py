from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import aiohttp

from gameinsights._collector_utils import (
    FetchResult,
    _SourceConfig,
    classify_source_error,
    normalize_active_player_rows,
    post_process_raw_data,
    raise_for_fetch_failure,
    record_fetch_exception,
    record_fetch_outcome,
)
from gameinsights._types import ReturnFormat, Scope
from gameinsights.async_.base import AsyncBaseSource
from gameinsights.async_.howlongtobeat import AsyncHowLongToBeat
from gameinsights.async_.protondb import AsyncProtonDB
from gameinsights.async_.steamachievements import AsyncSteamAchievements
from gameinsights.async_.steamcharts import AsyncSteamCharts
from gameinsights.async_.steamreview import AsyncSteamReview
from gameinsights.async_.steamspy import AsyncSteamSpy
from gameinsights.async_.steamstore import AsyncSteamStore
from gameinsights.async_.steamuser import AsyncSteamUser
from gameinsights.exceptions import (
    DependencyNotInstalledError,
    GameInsightsError,
    InvalidRequestError,
)
from gameinsights.model.game_data import GameDataModel
from gameinsights.sources.base import SourceResult
from gameinsights.utils import LoggerWrapper, metrics
from gameinsights.utils.async_ratelimit import async_rate_limited
from gameinsights.utils.import_optional import import_pandas

if TYPE_CHECKING:
    import pandas as pd

AsyncSourceConfig = _SourceConfig[AsyncBaseSource]


class AsyncCollector:
    """Async collector for Steam game data from multiple sources.

    Usage:
        # As async context manager (recommended):
        async with AsyncCollector() as collector:
            data = await collector.get_games_data(["570"])

        # Or manually:
        collector = AsyncCollector()
        await collector._ensure_initialized()
        data = await collector.get_games_data(["570"])
        await collector.close()
    """

    _session: aiohttp.ClientSession | None
    _initialized: bool

    def __init__(
        self,
        region: str = "us",
        language: str = "english",
        steam_api_key: str | None = None,
        boxleiter_multiplier: int = 30,
        calls: int = 60,
        period: int = 60,
    ) -> None:
        self._region = region
        self._language = language
        self._steam_api_key = steam_api_key
        self._boxleiter_multiplier = boxleiter_multiplier
        self.calls = calls
        self.period = period
        self._session = None
        self._initialized = False
        self._logger = LoggerWrapper(self.__class__.__name__)

    @property
    def logger(self) -> LoggerWrapper:
        return self._logger

    async def _ensure_initialized(self) -> None:
        """Create aiohttp session and all async source instances on first use."""
        if self._initialized:
            return

        self._session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit=20, limit_per_host=10)
        )
        self._init_sources()
        self._init_sources_config()
        self._initialized = True

    def _init_sources(self) -> None:
        self.steamreview = AsyncSteamReview(session=self._session)
        self.steamstore = AsyncSteamStore(
            region=self._region,
            language=self._language,
            api_key=self._steam_api_key,
            session=self._session,
        )
        self.steamspy = AsyncSteamSpy(session=self._session)
        self.steamcharts = AsyncSteamCharts(session=self._session)
        self.howlongtobeat = AsyncHowLongToBeat(session=self._session)
        self.steamachievements = AsyncSteamAchievements(
            api_key=self._steam_api_key,
            session=self._session,
        )
        self.steamuser = AsyncSteamUser(
            api_key=self._steam_api_key,
            session=self._session,
        )
        self.protondb = AsyncProtonDB(session=self._session)

    def _init_sources_config(self) -> None:
        self._id_based_sources: list[AsyncSourceConfig] = [
            AsyncSourceConfig(
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
                is_primary=True,
            ),
            AsyncSourceConfig(
                self.steamspy,
                ["ccu", "tags", "discount", "average_playtime_min", "languages"],
            ),
            AsyncSourceConfig(
                self.steamcharts,
                ["active_player_24h", "peak_active_player_all_time", "monthly_active_player"],
            ),
            AsyncSourceConfig(
                self.steamreview,
                [
                    "review_score",
                    "review_score_desc",
                    "total_positive",
                    "total_negative",
                    "total_reviews",
                ],
            ),
            AsyncSourceConfig(
                self.steamachievements,
                [
                    "achievements_count",
                    "achievements_percentage_average",
                    "achievements_list",
                ],
            ),
            AsyncSourceConfig(
                self.protondb,
                [
                    "protondb_tier",
                    "protondb_score",
                    "protondb_trending",
                    "protondb_confidence",
                    "protondb_total",
                ],
            ),
        ]

        self._name_based_sources: list[AsyncSourceConfig] = [
            AsyncSourceConfig(
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
                    "count_speed_run",
                    "count_backlog",
                    "count_review",
                    "review_score",
                    "count_playing",
                    "count_retired",
                ],
            ),
        ]

    @async_rate_limited()
    async def _fetch_raw_data(
        self,
        steam_appid: str,
        verbose: bool = True,
        raise_on_primary_failure: bool = False,
    ) -> GameDataModel:
        identifier = str(steam_appid)
        raw_data: dict[str, Any] = {"steam_appid": identifier}

        # Fire all ID-based sources in parallel
        results = await asyncio.gather(
            *[
                self._fetch_with_observability(
                    config.source,
                    identifier=identifier,
                    scope="id",
                    verbose=verbose,
                )
                for config in self._id_based_sources
            ],
            return_exceptions=True,
        )

        for config, source_data in zip(self._id_based_sources, results):
            if isinstance(source_data, BaseException):
                if raise_on_primary_failure and config.is_primary:
                    raise source_data
                continue
            if source_data["success"]:
                raw_data.update({key: source_data["data"][key] for key in config.fields})
            elif raise_on_primary_failure and config.is_primary:
                raise_for_fetch_failure(
                    source_name=config.source.__class__.__name__,
                    error_message=source_data["error"],
                    is_primary=True,
                )

        # Name-based sources run sequentially after the ID phase — they need `name`
        game_name = raw_data.get("name")
        if game_name:
            for config in self._name_based_sources:
                source_data = await self._fetch_with_observability(
                    config.source,
                    identifier=game_name,
                    scope="name",
                    verbose=verbose,
                )
                if source_data["success"]:
                    raw_data.update({key: source_data["data"][key] for key in config.fields})

        post_process_raw_data(raw_data, self._boxleiter_multiplier)

        return GameDataModel(**raw_data)

    async def _fetch_with_observability(
        self,
        source: AsyncBaseSource,
        identifier: str,
        scope: Scope,
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
                result = await source.fetch(identifier, verbose=verbose)
        except Exception as exc:
            record_fetch_exception(source_name, scope, source.logger, identifier, str(exc))
            raise

        record_fetch_outcome(
            source_name,
            scope,
            source.logger,
            identifier,
            verbose,
            timing,
            result["success"],
        )

        return result

    async def get_games_data(
        self,
        steam_appids: str | list[str],
        recap: bool = False,
        verbose: bool = True,
        include_failures: bool = False,
        raise_on_error: bool = False,
    ) -> list[dict[str, Any]] | tuple[list[dict[str, Any]], list[FetchResult]]:
        """Fetch game data for one or more appids.

        Parallelism is per-source within a game (via asyncio.gather in _fetch_raw_data).
        Games are processed sequentially to avoid over-calling sources.
        """
        await self._ensure_initialized()

        if raise_on_error and not steam_appids:
            raise InvalidRequestError("steam_appids must be a non-empty string or list.")

        if isinstance(steam_appids, (str, int)):
            steam_appids = [steam_appids]

        result: list[dict[str, Any]] = []
        all_results: list[FetchResult] = []
        total = len(steam_appids)

        for idx, appid in enumerate(steam_appids, start=1):
            self.logger.log(
                f"Fetching {idx} of {total} game data: steam appid {appid}..",
                level="info",
                verbose=verbose,
            )
            try:
                game_data = await self._fetch_raw_data(
                    appid,
                    verbose=verbose,
                    raise_on_primary_failure=raise_on_error,
                )
                payload = game_data.get_recap() if recap else game_data.model_dump(mode="json")
                result.append(payload)
                all_results.append(FetchResult(identifier=str(appid), success=True, data=payload))
            except GameInsightsError as e:
                if raise_on_error:
                    raise
                self.logger.log(
                    f"Error fetching data for game {appid}: {e}", level="error", verbose=True
                )
                all_results.append(FetchResult(identifier=str(appid), success=False, error=str(e)))

        if include_failures:
            return result, all_results
        return result

    async def get_games_active_player_data(
        self,
        steam_appids: str | list[str],
        fill_na_as: int = -1,
        verbose: bool = True,
        include_failures: bool = False,
        *,
        return_as: ReturnFormat = "list",
    ) -> (
        list[dict[str, Any]]
        | "pd.DataFrame"
        | tuple[list[dict[str, Any]], list[FetchResult]]
        | tuple["pd.DataFrame", list[FetchResult]]
    ):
        """Fetch active player data for multiple appids."""
        await self._ensure_initialized()

        if not steam_appids:
            if return_as == "dataframe":
                pd = self._require_pandas()
                return pd.DataFrame() if not include_failures else (pd.DataFrame(), [])
            return [] if not include_failures else ([], [])

        if isinstance(steam_appids, (str, int)):
            steam_appids = [steam_appids]

        all_months: set[str] = set()
        all_data: list[dict[str, Any]] = []
        all_results: list[FetchResult] = []
        total = len(steam_appids)

        for idx, appid in enumerate(steam_appids, start=1):
            self.logger.log(
                f"Fetching {idx} of {total}: active player data for appid {appid}..",
                level="info",
                verbose=verbose,
            )
            game_record: dict[str, Any] = {"steam_appid": appid}

            try:
                active_player_data = await self.steamcharts.fetch(
                    appid,
                    verbose=verbose,
                    selected_labels=[
                        "name",
                        "peak_active_player_all_time",
                        "monthly_active_player",
                    ],
                )

                if active_player_data["success"]:
                    src_data = active_player_data["data"]
                    monthly_data = {
                        month["month"]: month["average_players"]
                        for month in src_data.get("monthly_active_player", [])
                    }
                    game_record.update(monthly_data)
                    game_record.update(
                        {
                            "name": src_data.get("name"),
                            "peak_active_player_all_time": src_data.get(
                                "peak_active_player_all_time"
                            ),
                        }
                    )
                    all_months.update(monthly_data.keys())
                    all_results.append(
                        FetchResult(identifier=str(appid), success=True, data=game_record.copy())
                    )
                else:
                    all_results.append(
                        FetchResult(
                            identifier=str(appid),
                            success=False,
                            error=active_player_data["error"],
                        )
                    )
            except Exception as e:
                self.logger.log(
                    f"Error fetching active player data for appid {appid}: {e}",
                    level="error",
                    verbose=True,
                )
                all_results.append(FetchResult(identifier=str(appid), success=False, error=str(e)))
            all_data.append(game_record)

        normalized_data, sorted_months, fixed_columns, numeric_columns = (
            normalize_active_player_rows(all_data, all_months, fill_na_as)
        )

        if return_as == "dataframe":
            pd = self._require_pandas()
            df = pd.DataFrame(normalized_data, columns=fixed_columns + sorted_months)
            df[numeric_columns] = df[numeric_columns].fillna(fill_na_as)
            return (df, all_results) if include_failures else df

        return (normalized_data, all_results) if include_failures else normalized_data

    async def get_game_review(
        self,
        steam_appid: str,
        verbose: bool = True,
        review_only: bool = True,
        *,
        return_as: ReturnFormat = "list",
    ) -> list[dict[str, Any]] | "pd.DataFrame":
        """Fetch all reviews for a game."""
        await self._ensure_initialized()

        if not steam_appid:
            raise InvalidRequestError("steam_appid must be a non-empty string.")

        self.logger.log(
            f"Fetching reviews for appid {steam_appid}..",
            level="info",
            verbose=verbose,
        )

        records: list[dict[str, Any]] = []
        reviews_data = await self.steamreview.fetch(
            steam_appid=steam_appid,
            verbose=verbose,
            filter="recent",
            language="all",
            review_type="all",
            purchase_type="all",
            mode="review",
        )
        if reviews_data["success"]:
            records = reviews_data["data"]["reviews"] if review_only else [reviews_data["data"]]

        if return_as == "dataframe":
            pd = self._require_pandas()
            return pd.DataFrame(records)  # type: ignore[no-any-return]

        return records

    async def get_user_data(
        self,
        steamids: str | list[str],
        include_free_games: bool = True,
        return_as: ReturnFormat = "dataframe",
        verbose: bool = True,
    ) -> list[dict[str, Any]] | "pd.DataFrame":
        """Fetch user data for one or more Steam IDs."""
        await self._ensure_initialized()

        steamid_list = [steamids] if isinstance(steamids, (str, int)) else steamids

        results: list[dict[str, Any]] = []
        total = len(steamid_list)

        for idx, steamid in enumerate(steamid_list, start=1):
            self.logger.log(
                f"Fetching {idx} of {total}: user with steamid {steamid}",
                level="info",
                verbose=verbose,
            )
            fetch_result = await self.steamuser.fetch(
                steamid=steamid, include_free_games=include_free_games, verbose=verbose
            )
            user_data = fetch_result["data"] if fetch_result["success"] else {"steamid": steamid}
            results.append(user_data)

        if return_as == "dataframe":
            pd = self._require_pandas()
            return pd.DataFrame(results)  # type: ignore[no-any-return]

        return results

    @staticmethod
    def _require_pandas() -> Any:
        try:
            return import_pandas()
        except ImportError as exc:
            raise DependencyNotInstalledError(package="pandas", install_extra="dataframe") from exc

    @staticmethod
    def _classify_source_error(source_name: str, error_message: str) -> GameInsightsError:
        return classify_source_error(source_name, error_message)

    async def __aenter__(self) -> "AsyncCollector":
        await self._ensure_initialized()
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the aiohttp session and release all connections."""
        if self._session is not None and not self._session.closed:
            await self._session.close()
            self._session = None
            self._initialized = False
