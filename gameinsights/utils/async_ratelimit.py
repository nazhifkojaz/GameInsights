import asyncio
import logging
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any, TypeVar

from aiolimiter import AsyncLimiter

logger = logging.getLogger(__name__)

T = TypeVar("T")


def async_rate_limited(
    calls: int | None = None, period: int | None = None
) -> Callable[
    [Callable[..., Coroutine[Any, Any, T]]], Callable[..., Coroutine[Any, Any, T]]
]:
    """Decorator for async rate limiting using aiolimiter.

    Mirrors the sync logged_rate_limited() interface. Reads self.calls / self.period
    from the instance when calls/period are not passed explicitly.

    Args:
        calls: Max number of calls allowed per period. Reads self.calls if None.
        period: Time period in seconds. Reads self.period if None.
    """

    def decorator(
        func: Callable[..., Coroutine[Any, Any, T]]
    ) -> Callable[..., Coroutine[Any, Any, T]]:
        cache_attr = f"__async_rl_cache_{func.__name__}"

        @wraps(func)
        async def wrapper(self: Any, *args: Any, **kwargs: Any) -> T:
            actual_calls = calls if calls is not None else getattr(self, "calls", 60)
            actual_period = period if period is not None else getattr(self, "period", 60)

            cache = getattr(self, cache_attr, None)
            if (
                cache is None
                or cache["calls"] != actual_calls
                or cache["period"] != actual_period
            ):
                new_limiter = AsyncLimiter(max_rate=actual_calls, time_period=actual_period)
                cache = {"calls": actual_calls, "period": actual_period, "limiter": new_limiter}
                setattr(self, cache_attr, cache)

            limiter: AsyncLimiter = cache["limiter"]
            async with limiter:
                if asyncio.iscoroutinefunction(func):
                    return await func(self, *args, **kwargs)
                return func(self, *args, **kwargs)  # type: ignore[return-value]

        return wrapper

    return decorator
