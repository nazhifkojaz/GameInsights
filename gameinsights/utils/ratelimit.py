import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import Any

from ratelimit import RateLimitException, limits

logger = logging.getLogger(__name__)


def logged_sleep_and_retry(func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        while True:
            try:
                return func(*args, **kwargs)
            except RateLimitException as e:
                logger.info(
                    f"[RateLimiter] Rate limit exceeded. "
                    f"Sleeping for {e.period_remaining:.2f}s before retrying..."
                )
                time.sleep(e.period_remaining)

    return wrapper


def logged_rate_limited(
    calls: int | None = None, period: int | None = None
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for rate limiting with logging.
    Args:
        calls (int): Max number of calls allowed.
        period (int): Time period in seconds for the rate limit.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        cache_attr = f"__logged_rate_limit_cache_{func.__name__}"

        @wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            actual_calls = calls if calls is not None else getattr(self, "calls", 60)
            actual_period = period if period is not None else getattr(self, "period", 60)

            cache = getattr(self, cache_attr, None)
            if cache is None or cache["calls"] != actual_calls or cache["period"] != actual_period:

                def bound(*call_args: Any, **call_kwargs: Any) -> Any:
                    return func(self, *call_args, **call_kwargs)

                limited: Callable[..., Any] = logged_sleep_and_retry(
                    limits(calls=actual_calls, period=actual_period)(bound)
                )
                cache = {
                    "calls": actual_calls,
                    "period": actual_period,
                    "limited": limited,
                }
                setattr(self, cache_attr, cache)

            limited_execution = cache["limited"]
            return limited_execution(*args, **kwargs)

        return wrapper

    return decorator
