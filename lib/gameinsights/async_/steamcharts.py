from typing import Any

import aiohttp
from bs4 import BeautifulSoup
from bs4.element import Tag

from gameinsights.async_.base import AsyncBaseSource
from gameinsights.sources._parsers import transform_steamcharts
from gameinsights.sources._schemas import _STEAMCHARTS_LABELS
from gameinsights.sources.base import SourceResult, SuccessResult
from gameinsights.utils.async_ratelimit import async_rate_limited


class AsyncSteamCharts(AsyncBaseSource):
    _valid_labels: tuple[str, ...] = _STEAMCHARTS_LABELS
    _valid_labels_set: frozenset[str] = frozenset(_STEAMCHARTS_LABELS)
    _base_url = "https://steamcharts.com/app"

    def __init__(self, session: aiohttp.ClientSession | None = None) -> None:
        super().__init__(session=session)

    @async_rate_limited(calls=60, period=60)
    async def fetch(
        self,
        steam_appid: str,
        verbose: bool = True,
        selected_labels: list[str] | None = None,
    ) -> SourceResult:
        self.logger.log(
            f"Fetching active player data for appid {steam_appid}.",
            level="info",
            verbose=verbose,
        )
        steam_appid = str(steam_appid)
        response = await self._make_request(endpoint=steam_appid)

        if response.status_code != 200:
            return self._build_error_result(
                f"Failed to fetch data with status code: {response.status_code}", verbose=verbose
            )

        # BS4 parsing is sync/CPU-bound — fast enough to run inline
        soup = BeautifulSoup(response.text, "html.parser")

        game_name_tag = soup.find("h1", id="app-title")
        if not isinstance(game_name_tag, Tag):
            return self._build_error_result(
                "Failed to parse data, game name is not found.", verbose=verbose
            )

        peak_data_result = soup.find_all("div", class_="app-stat")
        peak_data: list[Tag] = [tag for tag in peak_data_result if isinstance(tag, Tag)]
        if len(peak_data) < 3:
            return self._build_error_result(
                "Failed to parse data, expecting atleast 3 'app-stat' divs.", verbose=verbose
            )

        active_player_data_table = soup.find("table", class_="common-table")
        if not isinstance(active_player_data_table, Tag):
            return self._build_error_result(
                "Failed to parse data, active player data table is not found.", verbose=verbose
            )

        player_rows_result = active_player_data_table.find_all("tr")
        player_data_rows = [row for row in player_rows_result if isinstance(row, Tag)][2:]

        if len(player_data_rows) > 0:
            cols = [col.get_text(strip=True) for col in player_data_rows[0].find_all("td")]
            if len(cols) < 5:
                return self._build_error_result(
                    "Failed to parse data, the structure of player data table is incorrect.",
                    verbose=verbose,
                )

        data_packed = {
            "steam_appid": steam_appid,
            **self._transform_data(
                {
                    "game_name": game_name_tag,
                    "peak_data": peak_data,
                    "player_data_rows": player_data_rows,
                },
                verbose=verbose,
            ),
        }

        if selected_labels:
            data_packed = {
                label: data_packed[label]
                for label in self._filter_valid_labels(selected_labels=selected_labels)
            }

        return SuccessResult(success=True, data=data_packed)

    def _transform_data(self, data: dict[str, Any], *, verbose: bool = True) -> dict[str, Any]:
        return transform_steamcharts(
            data,
            log_fn=lambda msg: self.logger.log(msg, level="warning", verbose=verbose),
        )
