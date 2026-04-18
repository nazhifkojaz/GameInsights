from typing import Any, Literal, cast

import aiohttp

from gameinsights.async_.base import AsyncBaseSource, _AsyncResponse
from gameinsights.sources._parsers import transform_steamreview
from gameinsights.sources._schemas import (
    _STEAMREVIEW_REVIEW_LABELS,
    _STEAMREVIEW_SUMMARY_LABELS,
    SteamReviewResponse,
)
from gameinsights.sources.base import SourceResult, SuccessResult
from gameinsights.utils.async_ratelimit import async_rate_limited


class AsyncSteamReview(AsyncBaseSource):
    _valid_labels: tuple[str, ...] = _STEAMREVIEW_SUMMARY_LABELS
    _valid_labels_set: frozenset[str] = frozenset(_STEAMREVIEW_SUMMARY_LABELS)
    _base_url = "https://store.steampowered.com/appreviews"

    def __init__(self, session: aiohttp.ClientSession | None = None) -> None:
        super().__init__(session=session)

    async def fetch(
        self,
        steam_appid: str,
        verbose: bool = True,
        selected_labels: list[str] | None = None,
        mode: Literal["summary", "review"] = "summary",
        filter: Literal["recent", "updated", "all"] = "recent",
        language: str = "all",
        review_type: Literal["all", "positive", "negative"] = "all",
        purchase_type: Literal["all", "non_steam_purchase", "steam"] = "all",
        cursor: str = "*",
    ) -> SourceResult:
        self.logger.log(
            f"Fetching review data for appid {steam_appid}.", level="info", verbose=verbose
        )
        steam_appid = str(steam_appid)

        params: dict[str, Any] = {
            "filter": filter,
            "language": language,
            "review_type": review_type,
            "purchase_type": purchase_type,
            "num_per_page": 100,
            "cursor": cursor,
            "json": 1,
        }

        page_data = await self._fetch_page(steam_appid=steam_appid, params=params)
        if page_data["success"] != 1:
            return self._build_error_result(
                f"API request failed for game with appid {steam_appid}.", verbose=verbose
            )
        if page_data["cursor"] is None:
            return self._build_error_result(
                f"Game with appid {steam_appid} is not found, or error on the request's cursor.",
                verbose=verbose,
            )

        summary_data = self._transform_data(page_data["query_summary"], "summary")

        if mode == "summary":
            if selected_labels:
                summary_data = {
                    label: summary_data[label]
                    for label in self._filter_valid_labels(selected_labels=selected_labels)
                }
            return SuccessResult(success=True, data=summary_data)

        reviews_data: list[dict[str, Any]] = []
        while True:
            if params["cursor"] == "*":
                total_review = page_data["query_summary"].get("total_reviews", 0)
                self.logger.log(
                    f"Found {total_review} reviews for {steam_appid}.",
                    verbose=verbose,
                )

            for review in page_data["reviews"]:
                review_data = self._transform_data(review, "review")
                if selected_labels:
                    review_data = {
                        label: review_data[label]
                        for label in self._filter_valid_labels(
                            valid_labels=_STEAMREVIEW_REVIEW_LABELS,
                            selected_labels=selected_labels,
                        )
                    }
                reviews_data.append(review_data)

            if params["cursor"] == page_data["cursor"]:
                break

            params["cursor"] = page_data["cursor"]
            page_data = await self._fetch_page(steam_appid=steam_appid, params=params)

        return SuccessResult(
            success=True,
            data={**summary_data, "reviews": reviews_data},
        )

    @async_rate_limited(calls=100000, period=24 * 60 * 60)
    async def _fetch_page(self, steam_appid: str, params: dict[str, Any]) -> SteamReviewResponse:
        response: _AsyncResponse = await self._make_request(endpoint=steam_appid, params=params)
        return cast(SteamReviewResponse, response.json())

    def _transform_data(
        self,
        data: dict[str, Any],
        data_type: Literal["summary", "review"] = "summary",
    ) -> dict[str, Any]:
        return transform_steamreview(data, data_type=data_type)
