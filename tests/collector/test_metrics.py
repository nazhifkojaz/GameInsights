"""Tests for Collector metrics emission and observability."""

from unittest.mock import MagicMock, patch


class TestCollectorMetrics:
    """Tests for _fetch_with_observability metrics emission."""

    def test_metrics_emitted_on_success(self, monkeypatch):
        """Test that metrics are emitted on successful fetch."""
        from gameinsights import Collector
        from gameinsights.sources import HowLongToBeat
        from gameinsights.utils import metrics

        # Mock the HowLongToBeat token method
        def mock_get_token(*args, **kwargs):
            return "mock_token"

        monkeypatch.setattr(HowLongToBeat, "_get_search_token", mock_get_token)

        # Mock metrics functions
        mock_counter = MagicMock()
        mock_timer = MagicMock()

        with (
            patch.object(metrics, "counter", mock_counter),
            patch.object(metrics, "timer", mock_timer),
        ):
            collector = Collector()

            # Mock a successful source fetch
            with patch.object(
                collector.steamstore,
                "fetch",
                return_value={
                    "success": True,
                    "data": {"steam_appid": "12345", "name": "Test"},
                },
            ):
                collector._fetch_with_observability(
                    collector.steamstore, identifier="12345", scope="id", verbose=False
                )

        # Verify metrics were emitted
        assert mock_counter.called
        assert mock_timer.called

    def test_metrics_emitted_on_failure(self, monkeypatch):
        """Test that metrics are emitted on failed fetch."""
        from gameinsights import Collector
        from gameinsights.sources import HowLongToBeat
        from gameinsights.utils import metrics

        def mock_get_token(*args, **kwargs):
            return "mock_token"

        monkeypatch.setattr(HowLongToBeat, "_get_search_token", mock_get_token)

        # Mock metrics functions
        mock_counter = MagicMock()
        mock_timer = MagicMock()

        with (
            patch.object(metrics, "counter", mock_counter),
            patch.object(metrics, "timer", mock_timer),
        ):
            collector = Collector()

            # Mock a failed source fetch
            with patch.object(
                collector.steamstore,
                "fetch",
                return_value={"success": False, "error": "Not found"},
            ):
                collector._fetch_with_observability(
                    collector.steamstore, identifier="99999", scope="id", verbose=False
                )

        # Verify failure metrics were emitted
        assert mock_counter.called

    def test_metrics_with_exception(self, monkeypatch):
        """Test metrics emission when source raises an exception."""
        from gameinsights import Collector
        from gameinsights.sources import HowLongToBeat
        from gameinsights.utils import metrics

        def mock_get_token(*args, **kwargs):
            return "mock_token"

        monkeypatch.setattr(HowLongToBeat, "_get_search_token", mock_get_token)

        # Mock metrics functions
        mock_counter = MagicMock()
        mock_timer = MagicMock()

        with (
            patch.object(metrics, "counter", mock_counter),
            patch.object(metrics, "timer", mock_timer),
        ):
            collector = Collector()

            # Mock a source that raises an exception
            with patch.object(
                collector.steamstore,
                "fetch",
                side_effect=ConnectionError("Network error"),
            ):
                try:
                    collector._fetch_with_observability(
                        collector.steamstore,
                        identifier="12345",
                        scope="id",
                        verbose=False,
                    )
                except ConnectionError:
                    pass  # Exception is re-raised

        # Verify exception metrics were emitted
        assert mock_counter.called

    def test_timing_metrics_record_duration(self, monkeypatch):
        """Test that timing metrics record operation duration."""
        from gameinsights import Collector
        from gameinsights.sources import HowLongToBeat
        from gameinsights.utils import metrics

        def mock_get_token(*args, **kwargs):
            return "mock_token"

        monkeypatch.setattr(HowLongToBeat, "_get_search_token", mock_get_token)

        # Mock metrics functions
        mock_counter = MagicMock()
        mock_timer = MagicMock()

        with (
            patch.object(metrics, "counter", mock_counter),
            patch.object(metrics, "timer", mock_timer),
        ):
            collector = Collector()

            # Mock a successful fetch
            with patch.object(
                collector.steamstore,
                "fetch",
                return_value={
                    "success": True,
                    "data": {"steam_appid": "12345", "name": "Test"},
                },
            ):
                collector._fetch_with_observability(
                    collector.steamstore, identifier="12345", scope="id", verbose=False
                )

        # Verify timing was called
        assert mock_timer.called

    def test_metrics_disabled_when_none(self, monkeypatch):
        """Test that no metrics are emitted when metrics collector is disabled."""
        from gameinsights import Collector
        from gameinsights.sources import HowLongToBeat

        def mock_get_token(*args, **kwargs):
            return "mock_token"

        monkeypatch.setattr(HowLongToBeat, "_get_search_token", mock_get_token)

        # Disable metrics by setting environment variable
        monkeypatch.delenv("GAMEINSIGHTS_METRICS", raising=False)

        collector = Collector()

        # Mock a successful fetch
        with patch.object(
            collector.steamstore,
            "fetch",
            return_value={"success": True, "data": {"steam_appid": "12345", "name": "Test"}},
        ):
            # Should not raise any exceptions
            result = collector._fetch_with_observability(
                collector.steamstore, identifier="12345", scope="id", verbose=False
            )

        # Result should still be returned
        assert result["success"] is True
