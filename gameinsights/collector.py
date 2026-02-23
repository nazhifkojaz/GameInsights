from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, NamedTuple

import requests
from requests.adapters import HTTPAdapter

from gameinsights import sources
from gameinsights.exceptions import (
    DependencyNotInstalledError,
    GameInsightsError,
    GameNotFoundError,
    InvalidRequestError,
    SourceUnavailableError,
)
from gameinsights.model.game_data import GameDataModel
from gameinsights.sources.base import SourceResult
from gameinsights.utils import LoggerWrapper, metrics
from gameinsights.utils.import_optional import import_pandas
from gameinsights.utils.ratelimit import logged_rate_limited

if TYPE_CHECKING:
    import pandas as pd


@dataclass
class FetchResult:
    """Result of fetching data for a single game/user.

    Attributes:
        identifier: The appid or steamid that was fetched
        success: Whether the fetch was successful
        data: The fetched data (if successful)
        error: Error message (if failed)
    """

    identifier: str
    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None


class SourceConfig(NamedTuple):
    source: sources.BaseSource
    fields: list[str]
    is_primary: bool = False


class Collector:
    """Collector for Steam game data from multiple sources.

    Thread Safety:
        Each Collector instance owns a requests.Session that is NOT
        thread-safe for concurrent use. Do NOT share a single Collector
        instance across threads. Instead, create a separate Collector
        per thread. Multiple Collectors are safe because each owns
        an independent session.
    """

    _session: requests.Session
    _closed: bool

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
            region: Region for the API request. Default is "us".
            language: Language for the API request. Default is "english".
            steam_api_key: Optional API key for Steam API.
            gamalytic_api_key: Optional API key for Gamalytic API.
            calls: Max number of API calls allowed per period. Default is 60.
            period: Time period in seconds for the rate limit. Default is 60.
        """
        self._region = region
        self._language = language
        self._steam_api_key = steam_api_key
        self._gamalytic_api_key = gamalytic_api_key
        self.calls = calls
        self.period = period
        self._closed = False

        # Create session before initializing sources
        self._session = self._create_session()

        try:
            self._init_sources()
            self._init_sources_config()
        except Exception:
            # Clean up session if initialization fails
            self._session.close()
            raise

        self._logger = LoggerWrapper(self.__class__.__name__)

    @property
    def logger(self) -> "LoggerWrapper":
        return self._logger

    @staticmethod
    def _create_session() -> requests.Session:
        """Create and configure a requests.Session with connection pooling.

        Returns:
            A configured session with HTTPAdapter mounted for both
            https:// and http:// schemes.

        Note:
            This method is internal and creates sessions for hardcoded
            source URLs only. It must NOT be exposed to user input to
            prevent SSRF (Server-Side Request Forgery) attacks.
        """
        session = requests.Session()
        adapter = HTTPAdapter(
            pool_connections=10,  # Sufficient for 9 sources across ~5 unique domains
            pool_maxsize=20,  # Allows up to 20 concurrent connections per domain
            pool_block=False,  # Don't block when pool is full
        )
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def _init_sources(self) -> None:
        """Initialize the sources with the current settings."""
        self.steamreview = sources.SteamReview(session=self._session)
        self.steamstore = sources.SteamStore(
            region=self.region,
            language=self.language,
            api_key=self.steam_api_key,
            session=self._session,
        )
        self.steamspy = sources.SteamSpy(session=self._session)
        self.gamalytic = sources.Gamalytic(
            api_key=self.gamalytic_api_key,
            session=self._session,
        )
        self.steamcharts = sources.SteamCharts(session=self._session)
        self.howlongtobeat = sources.HowLongToBeat(session=self._session)
        self.steamachievements = sources.SteamAchievements(
            api_key=self.steam_api_key,
            session=self._session,
        )
        self.steamuser = sources.SteamUser(
            api_key=self.steam_api_key,
            session=self._session,
        )
        self.protondb = sources.ProtonDB(session=self._session)

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
                is_primary=True,  # SteamStore is the primary source
            ),
            SourceConfig(
                self.gamalytic,
                [
                    "average_playtime_h",
                    "copies_sold",
                    "estimated_revenue",
                    "owners",
                    "languages",
                    "followers",
                    "early_access",
                ],
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
            SourceConfig(
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
                    "count_speed_run",
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

    @staticmethod
    def _classify_source_error(source_name: str, error_message: str) -> GameInsightsError:
        """Translate an ErrorResult string into a typed exception.

        Single authoritative mapping from raw error strings to exception types.

        Classification logic (first match wins):
          - SteamStore "not available in region" -> GameNotFoundError (primary source)
          - "failed to parse" -> SourceUnavailableError (parse errors)
          - "failed to fetch/obtain" -> SourceUnavailableError (fetch errors)
          - Network/timeout/connection errors -> SourceUnavailableError
          - HTTP error status codes -> SourceUnavailableError
          - "not found" with appid/steamid -> GameNotFoundError (game/user doesn't exist)
          - anything else -> GameInsightsError (base)

        Args:
            source_name: Name of the source that failed (e.g., "SteamStore")
            error_message: The error string from ErrorResult

        Returns:
            Appropriate exception instance based on error classification
        """
        lowered = error_message.lower()

        # Pattern 1: SteamStore-specific "not available in the specified region" message
        # This is the primary source's "game doesn't exist" message.
        # Only match the specific SteamStore phrasing to avoid false positives
        # from transient errors like "service not available".
        if "not available in the specified region" in lowered:
            match = re.search(r"appid\s+(\S+)", lowered)
            identifier_hint = match.group(1).rstrip(".,") if match else "unknown"
            return GameNotFoundError(identifier=identifier_hint, message=error_message)

        # Pattern 2: Parse errors -> SourceUnavailableError
        # Check this BEFORE "not found" because parse errors might contain "not found"
        if "failed to parse" in lowered:
            return SourceUnavailableError(source=source_name, reason=error_message)

        # Pattern 3: Fetch/obtain errors -> SourceUnavailableError
        if "failed to fetch" in lowered or "failed to obtain" in lowered:
            return SourceUnavailableError(source=source_name, reason=error_message)

        # Pattern 4: Network/transport errors -> SourceUnavailableError
        network_keywords = [
            "status code: 599",
            "failed to connect",
            "connection",
            "timeout",
            "ssl",
            "toomanyredirects",
        ]
        if any(keyword in lowered for keyword in network_keywords):
            return SourceUnavailableError(source=source_name, reason=error_message)

        # Pattern 5: HTTP error status codes -> SourceUnavailableError
        # Matches both "status code: 503" and "status 503" formats
        if re.search(r"status(?:\s+code)?:?\s*[45]\d{2}", lowered):
            return SourceUnavailableError(source=source_name, reason=error_message)

        # Pattern 6: Generic "not found" with appid/steamid extraction
        # Only applies if NOT a parse error (already checked above)
        if "not found" in lowered:
            identifier_hint = "unknown"
            for pattern in [r"appid\s+(\S+)", r"steamid\s+(\S+)"]:
                match = re.search(pattern, lowered)
                if match:
                    identifier_hint = match.group(1).rstrip(".,")
                    break
            return GameNotFoundError(identifier=identifier_hint, message=error_message)

        # Fallback: Generic error (not "unexpected" - that's too broad)
        return GameInsightsError(error_message)

    def _raise_for_fetch_failure(
        self,
        source_name: str,
        error_message: str,
        is_primary: bool = False,
    ) -> None:
        """Convert an ErrorResult into a typed exception and raise it.

        The is_primary flag marks SteamStore (and SteamUser for user data) as
        the authoritative existence check. When a supplementary source fails
        with "not found", we raise SourceUnavailableError instead — the game/user
        still exists, that source just lacks data.

        Args:
            source_name: Name of the source that failed
            error_message: The error string from ErrorResult
            is_primary: True if this is the primary source (SteamStore/SteamUser)

        Raises:
            GameNotFoundError: If primary source reports "not found"
            SourceUnavailableError: If supplementary source fails or primary has network error
            GameInsightsError: For other errors
        """
        exc = self._classify_source_error(source_name, error_message)

        # Supplementary sources should never raise GameNotFoundError
        # The game/user exists, just this source has no data
        if not is_primary and isinstance(exc, GameNotFoundError):
            raise SourceUnavailableError(source=source_name, reason=error_message)

        raise exc

    @staticmethod
    def _require_pandas() -> Any:  # Returns pd module
        """Import pandas or raise DependencyNotInstalledError.

        Returns:
            The pandas module

        Raises:
            DependencyNotInstalledError: If pandas is not installed
        """
        try:
            return import_pandas()
        except ImportError as exc:
            raise DependencyNotInstalledError(package="pandas", install_extra="dataframe") from exc

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
            steamids: Either a single or a list of 64bit SteamIDs.
            include_free_games: If True, will include free games when fetching users' owned games list. Default to True.
            return_as: Return format, "list" for list of dicts (works without pandas), "dataframe" for pandas DataFrame (requires pandas). Default to "dataframe".
            verbose: If True, will log the fetching process.

        Returns:
            list[dict[str, Any]] | pd.DataFrame: User data. Returns list if return_as="list", DataFrame if return_as="dataframe".

        Raises:
            DependencyNotInstalledError: If return_as="dataframe" and pandas is not installed. Install with: pip install gameinsights[dataframe]
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
            except Exception as e:
                self.logger.log(
                    f"Error fetching data for steamid {steamid}: {e}", level="error", verbose=True
                )

        if return_as == "dataframe":
            pd = self._require_pandas()
            return pd.DataFrame(results)  # type: ignore[no-any-return]

        return results

    def get_games_data(
        self,
        steam_appids: str | list[str],
        recap: bool = False,
        verbose: bool = True,
        include_failures: bool = False,
        raise_on_error: bool = False,
    ) -> list[dict[str, Any]] | tuple[list[dict[str, Any]], list[FetchResult]]:
        """Fetch game recap data.

        Game recap data includes game appid, name, release date, days since
        released, price and its currency, developer, publisher, genres,
        positive and negative reviews, review ratio, copies sold, estimated
        revenue, active players in the last 24 hours and in all time.

        Args:
            steam_appids: steam_appid of the game(s) to fetch data for.
            recap: If True, will return the recap data (for reference: check _RECAP_LABELS).
            verbose: If True, will log the fetching process.
            include_failures: If True, returns tuple of (successful_data, all_results_with_status).
            raise_on_error: If True, raise exceptions when primary source fails.
                When False (default), errors are silently absorbed into FetchResult.

        Returns:
            List of games recap data (when include_failures=False and raise_on_error=False).
            Tuple of successful data and all results (when include_failures=True and raise_on_error=False).

        Raises:
            GameNotFoundError: If raise_on_error=True and SteamStore reports game doesn't exist
            SourceUnavailableError: If raise_on_error=True and SteamStore is unreachable
            InvalidRequestError: If raise_on_error=True and steam_appids is empty

        Behavior:
            - Returns an empty list if no data could be fetched.
            - Returns complete/partial data if all/any appids succeed.
            - When include_failures=True, tracks which appids failed and why.
            - Input validation (non-empty steam_appids) is only enforced when raise_on_error=True.
              When raise_on_error=False, invalid/empty steam_appids will silently return an empty
              result (or ([], []) when include_failures=True).
            - When raise_on_error=True, exceptions from the primary source are propagated and
              the function does not return a (data, results) tuple even if include_failures=True.
              The raise_on_error parameter takes precedence over include_failures.
        """
        # Add input validation for raise_on_error mode
        if raise_on_error and not steam_appids:
            raise InvalidRequestError("steam_appids must be a non-empty string or list.")

        if isinstance(steam_appids, (str, int)):
            steam_appids = [steam_appids]

        result = []
        all_results: list[FetchResult] = []
        total = len(steam_appids)
        for idx, appid in enumerate(steam_appids, start=1):
            self.logger.log(
                f"Fetching {idx} of {total} game data: steam appid {appid}..",
                level="info",
                verbose=verbose,
            )
            try:
                game_data = self._fetch_raw_data(
                    appid,
                    verbose=verbose,
                    raise_on_primary_failure=raise_on_error,
                )
                payload = game_data.get_recap() if recap else game_data.model_dump(mode="json")
                result.append(payload)
                all_results.append(FetchResult(identifier=str(appid), success=True, data=payload))
            except GameInsightsError as e:
                # Re-raise if raise_on_error is True
                if raise_on_error:
                    raise
                # Otherwise log and continue (existing behavior)
                self.logger.log(
                    f"Error fetching data for game {appid}: {e}",
                    level="error",
                    verbose=True,
                )
                all_results.append(FetchResult(identifier=str(appid), success=False, error=str(e)))
            except Exception as e:
                self.logger.log(
                    f"Error fetching data for game {appid} with {e} error..",
                    level="error",
                    verbose=True,
                )
                all_results.append(FetchResult(identifier=str(appid), success=False, error=str(e)))

        if include_failures:
            return result, all_results
        return result

    def get_games_active_player_data(
        self,
        steam_appids: str | list[str],
        fill_na_as: int = -1,
        verbose: bool = True,
        include_failures: bool = False,
        *,
        return_as: Literal["list", "dataframe"] = "list",
    ) -> (
        list[dict[str, Any]]
        | pd.DataFrame
        | tuple[list[dict[str, Any]], list[FetchResult]]
        | tuple[pd.DataFrame, list[FetchResult]]
    ):
        """Fetch active player data for multiple appids.

        Args:
            steam_appids: List of appids to fetch active player data for.
            fill_na_as: Value to fill missing values with. Default is -1.
            verbose: If True, will log the fetching process.
            include_failures: If True, returns tuple of (data, all_results_with_status).
            return_as: Format to return data in. "list" returns list[dict],
                "dataframe" returns pd.DataFrame. Default is "list".

        Returns:
            list[dict[str, Any]]: List of dicts containing active player data
                (when include_failures=False and return_as="list").
            tuple[list[dict[str, Any]], list[FetchResult]]: Tuple of list and results
                (when include_failures=True and return_as="list").
            pd.DataFrame: DataFrame containing active player data
                (when include_failures=False and return_as="dataframe").
            tuple[pd.DataFrame, list[FetchResult]]: Tuple of DataFrame and results
                (when include_failures=True and return_as="dataframe").

        Raises:
            DependencyNotInstalledError: If return_as="dataframe" and pandas is not installed.
        """

        # Handle empty input - returns appropriate empty type based on return_as and include_failures
        if not steam_appids:
            if return_as == "dataframe":
                pd = self._require_pandas()
                return pd.DataFrame() if not include_failures else (pd.DataFrame(), [])
            return [] if not include_failures else ([], [])
        if isinstance(steam_appids, (str, int)):
            steam_appids = [steam_appids]

        all_months: set[str] = set()
        all_data = []
        total = len(steam_appids)
        all_results: list[FetchResult] = []

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
                    all_results.append(
                        FetchResult(identifier=str(appid), success=True, data=game_record.copy())
                    )
                else:
                    all_results.append(
                        FetchResult(
                            identifier=str(appid),
                            success=False,
                            error=active_player_data.get("error", "Unknown error"),
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

        # Normalize records - fill missing values consistently
        sorted_months = sorted(all_months)
        fixed_columns = ["steam_appid", "name", "peak_active_player_all_time"]
        # Only numeric columns should get fill_na_as; string columns stay as None/empty
        numeric_columns = ["peak_active_player_all_time"] + sorted_months

        normalized_data = []
        for record in all_data:
            normalized_record: dict[str, str | int | None] = {}
            for col in fixed_columns + sorted_months:
                value = record.get(col)
                if col in numeric_columns:
                    # Fill None or missing keys with fill_na_as for numeric columns
                    normalized_record[col] = value if value is not None else fill_na_as
                else:
                    # String columns: keep as None or original value
                    normalized_record[col] = value
            normalized_data.append(normalized_record)

        if return_as == "dataframe":
            pd = self._require_pandas()
            df = pd.DataFrame(normalized_data, columns=fixed_columns + sorted_months)
            # Only fillna for numeric columns, not string columns
            df[numeric_columns] = df[numeric_columns].fillna(fill_na_as)
            return (df, all_results) if include_failures else df

        return (normalized_data, all_results) if include_failures else normalized_data

    def get_game_review(
        self,
        steam_appid: str,
        verbose: bool = True,
        review_only: bool = True,
        *,
        return_as: Literal["list", "dataframe"] = "list",
    ) -> list[dict[str, Any]] | pd.DataFrame:
        """Fetch game reviews from Steam.

        Args:
            steam_appid: The Steam appid of the game.
            verbose: If True, will log the fetching process.
            review_only: If True, returns only reviews. If False, returns full review data.
            return_as: Format to return data in. "list" returns list[dict],
                "dataframe" returns pd.DataFrame. Default is "list".

        Returns:
            list[dict[str, Any]]: List of dicts containing review data
                (when return_as="list").
            pd.DataFrame: DataFrame containing review data (when return_as="dataframe").

        Raises:
            InvalidRequestError: If steam_appid is empty.
            DependencyNotInstalledError: If return_as="dataframe" and pandas is not installed.
        """
        if not steam_appid:
            raise InvalidRequestError("steam_appid must be a non-empty string.")

        self.logger.log(
            f"Fetching reviews for appid {steam_appid}..",
            level="info",
            verbose=verbose,
        )

        records: list[dict[str, Any]] = []
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
                records = (
                    reviews_data["data"]["reviews"] if review_only else [reviews_data["data"]]
                )
        except Exception as e:
            self.logger.log(
                f"Error fetching reviews for appid {steam_appid}: {e}", level="error", verbose=True
            )

        if return_as == "dataframe":
            pd = self._require_pandas()
            return pd.DataFrame(records)  # type: ignore[no-any-return]

        return records

    @logged_rate_limited()
    def _fetch_raw_data(
        self,
        steam_appid: str,
        verbose: bool = True,
        raise_on_primary_failure: bool = False,
    ) -> "GameDataModel":
        """Fetch game data from all sources based on appid.

        Args:
            steam_appid (str): The appid of the game to fetch data for.
            verbose (bool): If True, will log the fetching process
            raise_on_primary_failure (bool): If True, raise exception when
                SteamStore (primary source) fails. Default False.

        Returns:
            GameDataModel: The combined game data from all sources

        Raises:
            GameNotFoundError: If raise_on_primary_failure=True and SteamStore
                reports the game doesn't exist
            SourceUnavailableError: If raise_on_primary_failure=True and
                SteamStore is unreachable
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
            elif raise_on_primary_failure and config.is_primary:
                # Primary source failed - raise appropriate exception
                self._raise_for_fetch_failure(
                    source_name=config.source.__class__.__name__,
                    error_message=source_data["error"],
                    is_primary=True,
                )

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

    def __enter__(self) -> "Collector":
        """Enter the context manager.

        Returns:
            The Collector instance.
        """
        return self

    def __exit__(self, *args: object) -> None:
        """Exit the context manager and close the session.

        Args:
            *args: Exception info from the with block (unused).
        """
        try:
            self.close()
        except Exception as e:
            # Log but don't suppress the original exception from with block
            if hasattr(self, "_logger"):
                self.logger.log(
                    f"Error closing session: {e}",
                    level="error",
                    verbose=True,
                )

    def close(self) -> None:
        """Close the HTTP session and release all pooled connections.

        This method should be called when done making requests to properly
        close HTTP connections and release resources. When using the Collector
        as a context manager, this is called automatically.

        This method is idempotent - calling it multiple times has no effect
        beyond the first call.
        """
        if not self._closed:
            self._session.close()
            self._closed = True
