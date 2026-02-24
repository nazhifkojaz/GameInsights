"""Tests for Collector metrics emission and observability."""

from unittest.mock import MagicMock, patch

import pytest

from gameinsights.sources import HowLongToBeat


@pytest.fixture(autouse=True)
def _mock_hltb_token(monkeypatch):
    """Centralized mock for HowLongToBeat token to reduce repetition."""
    monkeypatch.setattr(HowLongToBeat, "_get_search_token", lambda *a, **kw: "mock_token")


@pytest.fixture
def reload_and_restore_metrics(monkeypatch):
    """Reload metrics module with GAMEINSIGHTS_METRICS unset and restore on teardown.

    This fixture ensures test isolation by:
    1. Capturing the original metrics module state and env var value
    2. Unsetting GAMEINSIGHTS_METRICS and reloading the module
    3. Restoring the original env var and module state after the test
    """
    import importlib
    import os
    import sys

    # Capture the original module if it exists
    original_module = sys.modules.get("gameinsights.utils.metrics")

    # Capture the original env var value
    original_env_value = os.environ.get("GAMEINSIGHTS_METRICS")

    # Ensure metrics are disabled by unsetting the environment variable
    monkeypatch.delenv("GAMEINSIGHTS_METRICS", raising=False)

    # Force recreation of metrics module with disabled state
    if "gameinsights.utils.metrics" in sys.modules:
        importlib.reload(sys.modules["gameinsights.utils.metrics"])

    yield

    # Teardown: restore the original env var first, before reloading module
    if original_env_value is not None:
        os.environ["GAMEINSIGHTS_METRICS"] = original_env_value
    else:
        os.environ.pop("GAMEINSIGHTS_METRICS", None)

    # Now restore the original module state with the correct env in place
    if original_module is not None:
        # Restore the original module
        sys.modules["gameinsights.utils.metrics"] = original_module
        # Reload with the original env var value restored
        importlib.reload(original_module)
    else:
        # If there was no original module, remove the reloaded one
        sys.modules.pop("gameinsights.utils.metrics", None)


class TestCollectorMetrics:
    """Tests for _fetch_with_observability metrics emission."""

    @pytest.fixture
    def mock_metrics(self):
        """Create mocked metrics functions for tests."""
        mock_counter = MagicMock()
        mock_timer = MagicMock()
        return {"counter": mock_counter, "timer": mock_timer}

    @pytest.fixture
    def collector_with_mocked_metrics(self, mock_metrics):
        """Create a Collector instance with mocked metrics."""
        from gameinsights import Collector
        from gameinsights.utils import metrics

        with (
            patch.object(metrics, "counter", mock_metrics["counter"]),
            patch.object(metrics, "timer", mock_metrics["timer"]),
        ):
            yield Collector()

    def test_metrics_emitted_on_success(self, collector_with_mocked_metrics, mock_metrics):
        """Test that metrics are emitted on successful fetch."""
        # Mock a successful source fetch
        with patch.object(
            collector_with_mocked_metrics.steamstore,
            "fetch",
            return_value={
                "success": True,
                "data": {"steam_appid": "12345", "name": "Test"},
            },
        ):
            collector_with_mocked_metrics._fetch_with_observability(
                collector_with_mocked_metrics.steamstore,
                identifier="12345",
                scope="id",
                verbose=False,
            )

        # Verify metrics were emitted
        assert mock_metrics["counter"].called
        assert mock_metrics["timer"].called

    def test_metrics_emitted_on_failure(self, collector_with_mocked_metrics, mock_metrics):
        """Test that metrics are emitted on failed fetch."""
        # Mock a failed source fetch
        with patch.object(
            collector_with_mocked_metrics.steamstore,
            "fetch",
            return_value={"success": False, "error": "Not found"},
        ):
            collector_with_mocked_metrics._fetch_with_observability(
                collector_with_mocked_metrics.steamstore,
                identifier="99999",
                scope="id",
                verbose=False,
            )

        # Verify failure metrics were emitted
        assert mock_metrics["counter"].called

    def test_metrics_with_exception(self, collector_with_mocked_metrics, mock_metrics):
        """Test metrics emission when source raises an exception."""
        # Mock a source that raises an exception and verify it's re-raised
        with patch.object(
            collector_with_mocked_metrics.steamstore,
            "fetch",
            side_effect=ConnectionError("Network error"),
        ), pytest.raises(ConnectionError):
            collector_with_mocked_metrics._fetch_with_observability(
                collector_with_mocked_metrics.steamstore,
                identifier="12345",
                scope="id",
                verbose=False,
            )

        # Verify exception metrics were emitted
        assert mock_metrics["counter"].called

    def test_metrics_disabled_when_none(self, caplog, reload_and_restore_metrics):
        """Test that metrics are not emitted when GAMEINSIGHTS_METRICS is not set."""
        import logging

        from gameinsights import Collector

        collector = Collector()

        # Capture logs from the metrics logger
        with caplog.at_level(logging.INFO, logger="gameinsights.metrics"):
            # Mock a successful fetch
            with patch.object(
                collector.steamstore,
                "fetch",
                return_value={"success": True, "data": {"steam_appid": "12345", "name": "Test"}},
            ):
                result = collector._fetch_with_observability(
                    collector.steamstore, identifier="12345", scope="id", verbose=False
                )

        # Result should still be returned correctly
        assert result["success"] is True
        assert result["data"]["steam_appid"] == "12345"

        # No metrics should have been logged
        metric_logs = [r for r in caplog.records if r.name == "gameinsights.metrics"]
        assert len(metric_logs) == 0, "Expected no metrics to be logged when disabled"
