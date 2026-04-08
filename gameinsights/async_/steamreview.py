import asyncio
from typing import Any, Literal, cast

import aiohttp

from gameinsights.async_.base import AsyncBaseSource, _AsyncResponse
from gameinsights.sources.base import SourceResult, SuccessResult
from gameinsights.sources.steamreview import (
    _STEAMREVIEW_REVIEW_LABELS,
    _STEAMREVIEW_SUMMARY_LABELS,
    SteamReviewResponse,
)
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

            await asyncio.sleep(0.5)

            if params["cursor"] == page_data["cursor"]:
                break

            params["cursor"] = page_data["cursor"]
            page_data = await self._fetch_page(steam_appid=steam_appid, params=params)

        return SuccessResult(
            success=True,
            data={**summary_data, "reviews": reviews_data},
        )

    @async_rate_limited(calls=100000, period=24 * 60 * 60)
    async def _fetch_page(
        self, steam_appid: str, params: dict[str, Any]
    ) -> SteamReviewResponse:
        response: _AsyncResponse = await self._make_request(
            endpoint=steam_appid, params=params
        )
        return cast(SteamReviewResponse, response.json())

    def _transform_data(
        self,
        data: dict[str, Any],
        data_type: Literal["summary", "review"] = "summary",
    ) -> dict[str, Any]:
        if data_type == "summary":
            return {
                "review_score": data.get("review_score"),
                "review_score_desc": data.get("review_score_desc"),
                "total_positive": data.get("total_positive"),
                "total_negative": data.get("total_negative"),
                "total_reviews": data.get("total_reviews"),
            }
        else:
            author = data.get("author", {})
            return {
                "recommendation_id": data.get("recommendationid"),
                "author_steamid": author.get("steamid"),
                "author_num_games_owned": author.get("num_games_owned"),
                "author_num_reviews": author.get("num_reviews"),
                "author_playtime_forever": author.get("playtime_forever"),
                "author_playtime_last_two_weeks": author.get("playtime_last_two_weeks"),
                "author_playtime_at_review": author.get("playtime_at_review"),
                "author_last_played": author.get("last_played"),
                "language": data.get("language"),
                "review": data.get("review"),
                "timestamp_created": data.get("timestamp_created"),
                "timestamp_updated": data.get("timestamp_updated"),
                "voted_up": data.get("voted_up"),
                "votes_up": data.get("votes_up"),
                "votes_funny": data.get("votes_funny"),
                "weighted_vote_score": data.get("weighted_vote_score"),
                "comment_count": data.get("comment_count"),
                "steam_purchase": data.get("steam_purchase"),
                "received_for_free": data.get("received_for_free"),
                "written_during_early_access": data.get("written_during_early_access"),
                "primarily_steam_deck": data.get("primarily_steam_deck"),
            }
