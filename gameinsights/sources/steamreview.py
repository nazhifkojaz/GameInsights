import time
from typing import Any, Literal, TypedDict, cast

import requests

from gameinsights.sources.base import BaseSource, SourceResult, SuccessResult
from gameinsights.utils.ratelimit import logged_rate_limited

_STEAMREVIEW_SUMMARY_LABELS = (
    "review_score",
    "review_score_desc",
    "total_positive",
    "total_negative",
    "total_reviews",
)

_STEAMREVIEW_REVIEW_LABELS = (
    "recommendation_id",
    "author_steamid",
    "author_num_games_owned",
    "author_num_reviews",
    "author_playtime_forever",
    "author_playtime_last_two_weeks",
    "author_playtime_at_review",
    "author_last_played",
    "language",
    "review",
    "timestamp_created",
    "timestamp_updated",
    "voted_up",
    "votes_up",
    "votes_funny",
    "weighted_vote_score",
    "comment_count",
    "steam_purchase",
    "received_for_free",
    "written_during_early_access",
    "primarily_steam_deck",
)


class SteamReviewResponse(TypedDict):
    success: bool
    cursor: str | None
    reviews: list[dict[str, Any]]
    query_summary: dict[str, Any]


class SteamReview(BaseSource):
    _valid_labels: tuple[str, ...] = _STEAMREVIEW_SUMMARY_LABELS
    _valid_labels_set: frozenset[str] = frozenset(_STEAMREVIEW_SUMMARY_LABELS)
    _base_url = "https://store.steampowered.com/appreviews"

    def __init__(self, session: requests.Session | None = None) -> None:
        """Initialize SteamReview source.

        Args:
            session: Optional requests.Session for connection pooling.
        """
        super().__init__(session=session)

    def fetch(
        self,
        steam_appid: str,
        verbose: bool = True,
        selected_labels: list[str] | None = None,
        mode: Literal["summary", "review"] = "summary",
        filter: Literal["recent", "updated", "all"] = "recent",
        language: str = "all",  # refer to list of languages here -> https://partner.steamgames.com/doc/store/localization/languages
        review_type: Literal["all", "positive", "negative"] = "all",
        purchase_type: Literal["all", "non_steam_purchase", "steam"] = "all",
        cursor: str = "*",
    ) -> SourceResult:
        """Fetch review data from Steamworks API based on steam_appid.
        Args:
            steam_appid (str): The steam appid of the game to fetch data for.
            verbose (bool): If True, will log the fetching process.
            selected_labels (list[str] | None): A list of labels to filter the data. If None, all labels will be used.
            mode (str): Fetching mode, will return reviews if mdoe is "review", and return review numbers summary if "summary".
            params : parameters for the api call to Steamworks API.

        Returns:
            SourceResult: A dictionary containing the status, data, or any error message if applicable.

        Behavior:
            This function will probably be refactored for better readibility but this function have 2 behavior, to fetch only review summary, or review summary + reviews list.
            1. "summary" mode:
                - this function will return review summary, data will consists of _STEAMREVIEW_SUMMARY_LABELS labels, and the selected_labels will be used to filter based on _STEAMREVIEW_SUMMARY_LABELS.
            2. "review" mode:
                - this function will return reviiew summary and reviews list, data will consists of _STEAMREVIEW_SUMMARY_LABELS + "reviews" labels, and the selected_labels will be used to filter reviews' data (based on _STEAMREVIEW_REVIEW_LABELS).
        """

        self.logger.log(
            f"Fetching review data for appid {steam_appid}.", level="info", verbose=verbose
        )

        # ensure steam_appid is string
        steam_appid = str(steam_appid)

        # prepare default params
        params = {
            "filter": filter,
            "language": language,
            "review_type": review_type,
            "purchase_type": purchase_type,
            "num_per_page": 100,
            "cursor": cursor,
            "json": 1,
        }

        page_data = self._fetch_page(steam_appid=steam_appid, params=params)
        if page_data["success"] != 1:
            return self._build_error_result(
                f"API request failed for game with appid {steam_appid}.",
                verbose=verbose,
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
            return SuccessResult(
                success=True,
                data=summary_data,
            )

        reviews_data: list[dict[str, Any]] = []
        while True:
            # log the total reviews
            if params["cursor"] == "*":
                total_review = page_data["query_summary"].get("total_reviews", 0)
                self.logger.log(
                    f"Found {total_review} reviews for {steam_appid}. If fetch_all is True, the reviews fetching process might take a while.",
                    verbose=verbose,
                )

            # reviews_data.extend(self._transform_data(r, "review") for r in page_data["reviews"])

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

            # add internal sleep
            time.sleep(0.5)

            if params["cursor"] == page_data["cursor"]:
                break

            params["cursor"] = page_data["cursor"]
            page_data = self._fetch_page(steam_appid=steam_appid, params=params)

        return SuccessResult(
            success=True,
            data={
                **summary_data,
                "reviews": reviews_data,
            },
        )

    @logged_rate_limited(calls=100000, period=24 * 60 * 60)
    def _fetch_page(self, steam_appid: str, params: dict[str, Any]) -> SteamReviewResponse:
        response = self._make_request(endpoint=steam_appid, params=params)
        return cast(SteamReviewResponse, response.json())

    def _transform_data(
        self,
        data: dict[str, Any],
        data_type: Literal["summary", "review"] = "summary",
    ) -> dict[str, Any]:
        if data_type == "summary":
            return {
                "review_score": data.get("review_score", None),
                "review_score_desc": data.get("review_score_desc", None),
                "total_positive": data.get("total_positive", None),
                "total_negative": data.get("total_negative", None),
                "total_reviews": data.get("total_reviews", None),
            }
        else:
            author = data.get("author", {})
            return {
                "recommendation_id": data.get("recommendationid", None),
                "author_steamid": author.get("steamid", None),
                "author_num_games_owned": author.get("num_games_owned", None),
                "author_num_reviews": author.get("num_reviews", None),
                "author_playtime_forever": author.get("playtime_forever", None),
                "author_playtime_last_two_weeks": author.get("playtime_last_two_weeks", None),
                "author_playtime_at_review": author.get("playtime_at_review", None),
                "author_last_played": author.get("last_played", None),
                "language": data.get("language", None),
                "review": data.get("review", None),
                "timestamp_created": data.get("timestamp_created", None),
                "timestamp_updated": data.get("timestamp_updated", None),
                "voted_up": data.get("voted_up", None),
                "votes_up": data.get("votes_up", None),
                "votes_funny": data.get("votes_funny", None),
                "weighted_vote_score": data.get("weighted_vote_score", None),
                "comment_count": data.get("comment_count", None),
                "steam_purchase": data.get("steam_purchase", None),
                "received_for_free": data.get("received_for_free", None),
                "written_during_early_access": data.get("written_during_early_access", None),
                "primarily_steam_deck": data.get("primarily_steam_deck", None),
            }
