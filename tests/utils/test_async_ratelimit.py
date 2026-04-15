"""Tests for async_rate_limited decorator."""

import pytest

from gameinsights.utils.async_ratelimit import async_rate_limited


class _FakeSource:
    """Minimal stand-in for an async source with rate-limit attributes."""

    calls = 10
    period = 1

    def __init__(self) -> None:
        self.invocation_count = 0

    @async_rate_limited(calls=5, period=1)
    async def fetch_explicit(self) -> str:
        self.invocation_count += 1
        return "ok"

    @async_rate_limited()
    async def fetch_from_instance(self) -> str:
        self.invocation_count += 1
        return "ok"


class TestAsyncRateLimited:
    async def test_async_rate_limited_allows_calls_within_budget(self) -> None:
        src = _FakeSource()
        results = [await src.fetch_explicit() for _ in range(3)]
        assert all(r == "ok" for r in results)
        assert src.invocation_count == 3

    async def test_async_rate_limited_reads_instance_attributes(self) -> None:
        src = _FakeSource()
        result = await src.fetch_from_instance()
        assert result == "ok"
        # Cache should reflect instance's calls/period values
        cache = getattr(src, "__async_rl_cache_fetch_from_instance")
        assert cache["calls"] == 10
        assert cache["period"] == 1

    async def test_async_rate_limited_caches_per_instance(self) -> None:
        src1 = _FakeSource()
        src2 = _FakeSource()
        await src1.fetch_explicit()
        await src2.fetch_explicit()
        # Each instance has its own cache attribute
        cache1 = getattr(src1, "__async_rl_cache_fetch_explicit")
        cache2 = getattr(src2, "__async_rl_cache_fetch_explicit")
        assert cache1 is not cache2
        assert cache1["limiter"] is not cache2["limiter"]

    async def test_async_rate_limited_recreates_limiter_on_config_change(self) -> None:
        src = _FakeSource()
        await src.fetch_from_instance()
        old_limiter = getattr(src, "__async_rl_cache_fetch_from_instance")["limiter"]

        # Change the instance's rate-limit settings
        src.calls = 5
        src.period = 30
        await src.fetch_from_instance()
        new_cache = getattr(src, "__async_rl_cache_fetch_from_instance")
        assert new_cache["calls"] == 5
        assert new_cache["period"] == 30
        assert new_cache["limiter"] is not old_limiter

    async def test_async_rate_limited_propagates_exceptions(self) -> None:
        class _Boom:
            calls = 10
            period = 1

            @async_rate_limited(calls=10, period=1)
            async def do_work(self) -> None:
                raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            await _Boom().do_work()
