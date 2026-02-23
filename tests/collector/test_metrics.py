"""Tests for Collector metrics emission and observability."""

from unittest.mock import MagicMock, patch

import pytest

from gameinsights.sources import HowLongToBeat


@pytest.fixture(autouse=True)
def _mock_hltb_token(monkeypatch):
    """Centralized mock for HowLongToBeat token to reduce repetition."""
    monkeypatch.setattr(HowLongToBeat, "_get_search_token", lambda *a, **kw: "mock_token")


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

    def test_metrics_emitted_on_success(
        self, collector_with_mocked_metrics, mock_metrics
    ):
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

    def test_metrics_emitted_on_failure(
        self, collector_with_mocked_metrics, mock_metrics
    ):
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

    def test_metrics_with_exception(
        self, collector_with_mocked_metrics, mock_metrics
    ):
        """Test metrics emission when source raises an exception."""
        # Mock a source that raises an exception
        with patch.object(
            collector_with_mocked_metrics.steamstore,
            "fetch",
            side_effect=ConnectionError("Network error"),
        ):
            try:
                collector_with_mocked_metrics._fetch_with_observability(
                    collector_with_mocked_metrics.steamstore,
                    identifier="12345",
                    scope="id",
                    verbose=False,
                )
            except ConnectionError:
                pass  # Exception is re-raised

        # Verify exception metrics were emitted
        assert mock_metrics["counter"].called

    def test_metrics_disabled_when_none(self, monkeypatch):
        """Test that the code works correctly when metrics collector is disabled.

        Note: This test verifies that operations complete without errors
        regardless of the metrics enabled state. The actual emission
        happens inside MetricsCollector._emit which has early-return
        when disabled - that behavior is covered by the metrics module tests.
        """
        from gameinsights import Collector

        collector = Collector()

        # Mock a successful fetch
        with patch.object(
            collector.steamstore,
            "fetch",
            return_value={"success": True, "data": {"steam_appid": "12345", "name": "Test"}},
        ):
            # Should not raise any exceptions regardless of metrics state
            result = collector._fetch_with_observability(
                collector.steamstore, identifier="12345", scope="id", verbose=False
            )

        # Result should still be returned correctly
        assert result["success"] is True
        assert result["data"]["steam_appid"] == "12345"
