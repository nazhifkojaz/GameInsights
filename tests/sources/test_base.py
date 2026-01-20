import pytest
import requests

from gameinsights.sources import base
from gameinsights.sources.base import BaseSource


class TestBaseSource:
    @pytest.fixture
    def base_source_fixture(self):
        class _TestSource(BaseSource):
            _valid_labels = ("test_label_1", "test_label_2")
            _valid_labels_set = frozenset(_valid_labels)
            _base_url = "https://api.testurl.com/"

            def fetch(self, *args, **kwargs):
                pass

            def _transform_data(self, data):
                pass

        return _TestSource()

    @pytest.mark.parametrize(
        "selected_labels, valid_labels, expected",
        [
            # using default valid_labels (from fixture)
            (["test_label_1"], None, ["test_label_1"]),
            (["test_label_1", "invalid"], None, ["test_label_1"]),
            (["invalid"], None, []),
            # using custom valid_labels parameter
            (["custom_1"], ["custom_1", "custom_2"], ["custom_1"]),
            (["custom_1", "invalid"], ["custom_1", "custom_2"], ["custom_1"]),
            (["invalid"], ["custom_1"], []),
            # empty and all
            ([], None, []),
            (["test_label_1", "test_label_2"], None, ["test_label_1", "test_label_2"]),
        ],
    )
    def test_filter_valid_labels(
        self, base_source_fixture, selected_labels, valid_labels, expected
    ):
        """Test label filtering with various combinations"""
        if valid_labels is not None:
            result = base_source_fixture._filter_valid_labels(
                selected_labels=selected_labels, valid_labels=valid_labels
            )
        else:
            result = base_source_fixture._filter_valid_labels(selected_labels=selected_labels)

        assert isinstance(result, list)
        assert result == expected

    @pytest.mark.parametrize(
        "attempt, expected_result",
        [
            (
                [requests.exceptions.ConnectionError("fail 1"), {"json_data": {"ok": True}}],
                {"retries": 2, "status_code": 200},
            ),
            (
                [
                    requests.exceptions.Timeout("timeout 1"),
                    requests.exceptions.Timeout("timeout 2"),
                    {"json_data": {"ok": True}},
                ],
                {"retries": 3, "status_code": 200},
            ),
        ],
        ids=["connection_error_once", "timeout_twice"],
    )
    def test_make_request_retries_on_exception_to_retry(
        self, mock_request_response, base_source_fixture, attempt, expected_result
    ):
        # Mock the session's get method instead of requests.get
        mock_get = mock_request_response(
            target_class=base_source_fixture.session, method_name="get", side_effect=attempt
        )
        result = base_source_fixture._make_request()

        assert result.status_code == expected_result["status_code"]
        assert mock_get.call_count == expected_result["retries"]

    def test_make_request_max_retries(self, mock_request_response, base_source_fixture):
        attempt = [
            requests.exceptions.Timeout("timeout 1"),
            requests.exceptions.Timeout("timeout 2"),
            requests.exceptions.Timeout("timeout 3"),
        ]
        # Mock the session's get method instead of requests.get
        mock_get = mock_request_response(
            target_class=base_source_fixture.session, method_name="get", side_effect=attempt
        )
        result = base_source_fixture._make_request()

        assert mock_get.call_count == 3
        assert result.status_code == base.SYNTHETIC_ERROR_CODE
        assert not result.ok

    def test_make_request_post_success(self, mock_request_response, base_source_fixture):
        """Test that _make_request works with POST method."""
        # Mock the session's post method
        mock_post = mock_request_response(
            target_class=base_source_fixture.session,
            method_name="post",
            json_data={"ok": True},
        )

        result = base_source_fixture._make_request(
            method="POST", json={"test": "data"}, headers={"Content-Type": "application/json"}
        )

        assert result.status_code == 200
        assert mock_post.call_count == 1
        # Verify the post was called with correct arguments
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args.kwargs
        assert "json" in call_kwargs
        assert call_kwargs["json"] == {"test": "data"}

    def test_make_request_post_retries_on_exception(self, mock_request_response, base_source_fixture):
        """Test that POST requests retry on connection errors."""
        attempt = [
            requests.exceptions.ConnectionError("fail 1"),
            {"json_data": {"ok": True}},
        ]
        # Mock the session's post method
        mock_post = mock_request_response(
            target_class=base_source_fixture.session, method_name="post", side_effect=attempt
        )

        result = base_source_fixture._make_request(
            method="POST", json={"test": "data"}
        )

        assert result.status_code == 200
        assert mock_post.call_count == 2

    def test_make_request_post_max_retries(self, mock_request_response, base_source_fixture):
        """Test that POST requests respect max retries."""
        attempt = [
            requests.exceptions.Timeout("timeout 1"),
            requests.exceptions.Timeout("timeout 2"),
            requests.exceptions.Timeout("timeout 3"),
        ]
        # Mock the session's post method
        mock_post = mock_request_response(
            target_class=base_source_fixture.session, method_name="post", side_effect=attempt
        )

        result = base_source_fixture._make_request(method="POST", json={"test": "data"})

        assert mock_post.call_count == 3
        assert result.status_code == base.SYNTHETIC_ERROR_CODE
        assert not result.ok

    def test_make_request_post_with_data_parameter(self, mock_request_response, base_source_fixture):
        """Test that POST requests work with raw data parameter."""
        # Mock the session's post method
        mock_post = mock_request_response(
            target_class=base_source_fixture.session,
            method_name="post",
            json_data={"ok": True},
        )

        result = base_source_fixture._make_request(
            method="POST", data=b"raw bytes", headers={"Content-Type": "application/octet-stream"}
        )

        assert result.status_code == 200
        assert mock_post.call_count == 1
        call_kwargs = mock_post.call_args.kwargs
        assert "data" in call_kwargs
        assert call_kwargs["data"] == b"raw bytes"


class TestConnectionPooling:
    """Tests for session connection pooling functionality."""

    def setup_method(self):
        """Reset session before each test."""
        BaseSource.close_session()

    def teardown_method(self):
        """Clean up session after each test."""
        BaseSource.close_session()

    @pytest.fixture
    def test_source_class(self):
        """Create a test source class for testing."""

        class _TestSource(BaseSource):
            _valid_labels = ("test_label",)
            _valid_labels_set = frozenset(_valid_labels)
            _base_url = "https://api.testurl.com/"

            def fetch(self, *args, **kwargs):
                pass

            def _transform_data(self, data):
                pass

        return _TestSource

    def test_session_created_on_first_access(self, test_source_class):
        """Test that a session is created when first accessed."""
        # Ensure session is None initially
        assert BaseSource._session is None

        source = test_source_class()
        session = source.session

        assert session is not None
        assert isinstance(session, requests.Session)

    def test_session_reused_across_sources(self, test_source_class):
        """Test that the same session is reused across different source instances."""
        source1 = test_source_class()
        source2 = test_source_class()

        session1 = source1.session
        session2 = source2.session

        assert session1 is session2
        assert id(session1) == id(session2)

    def test_session_has_connection_pooling_configured(self, test_source_class):
        """Test that the session is configured with connection pooling."""
        source = test_source_class()
        session = source.session

        # Check that HTTPAdapter is mounted for both http and https
        https_adapter = session.get_adapter("https://example.com")
        http_adapter = session.get_adapter("http://example.com")

        assert https_adapter is not None
        assert http_adapter is not None

        from requests.adapters import HTTPAdapter

        assert isinstance(https_adapter, HTTPAdapter)
        assert isinstance(http_adapter, HTTPAdapter)

        # Verify pool configuration
        assert https_adapter._pool_connections == 10
        assert https_adapter._pool_maxsize == 20

    def test_close_session_closes_and_resets_session(self, test_source_class):
        """Test that close_session properly closes and resets the session."""
        source = test_source_class()
        session1 = source.session

        # Close the session
        BaseSource.close_session()

        # Verify session is reset
        assert BaseSource._session is None

        # New source should create a new session
        session2 = source.session
        assert session1 is not session2

    def test_collector_context_manager(self):
        """Test that Collector works as a context manager."""
        from gameinsights import Collector

        # Ensure clean state
        BaseSource.close_session()

        with Collector() as collector:
            assert collector is not None
            # Session is created lazily when first accessed via a source
            _ = collector.steamstore.session
            assert BaseSource._session is not None

        # Session should be closed after exiting context
        assert BaseSource._session is None

    def test_collector_close_method(self):
        """Test that Collector.close() properly closes the session."""
        from gameinsights import Collector

        # Ensure clean state
        BaseSource.close_session()

        collector = Collector()
        # Session is created lazily when first accessed via a source
        _ = collector.steamstore.session
        assert BaseSource._session is not None

        collector.close()
        assert BaseSource._session is None
