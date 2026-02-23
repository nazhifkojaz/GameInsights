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

        return _TestSource(session=requests.Session())

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

    def test_make_request_post_retries_on_exception(
        self, mock_request_response, base_source_fixture
    ):
        """Test that POST requests retry on connection errors."""
        attempt = [
            requests.exceptions.ConnectionError("fail 1"),
            {"json_data": {"ok": True}},
        ]
        # Mock the session's post method
        mock_post = mock_request_response(
            target_class=base_source_fixture.session, method_name="post", side_effect=attempt
        )

        result = base_source_fixture._make_request(method="POST", json={"test": "data"})

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

    def test_make_request_post_with_data_parameter(
        self, mock_request_response, base_source_fixture
    ):
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
    """Tests for session lifecycle management with per-Collector ownership."""

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

    def test_lazy_session_created_when_not_injected(self, test_source_class):
        """A source with no injected session creates one lazily on first access."""
        source = test_source_class()
        assert source._session is None

        session = source.session  # triggers lazy creation
        assert session is not None
        assert isinstance(session, requests.Session)
        assert source._session is session
        session.close()

    def test_injected_session_returned_directly(self, test_source_class):
        """An injected session is returned without creating a new one."""
        shared = requests.Session()
        source = test_source_class(session=shared)
        assert source.session is shared
        shared.close()

    def test_injected_session_shared_across_sources(self, test_source_class):
        """Two sources sharing an injected session return the same object."""
        shared = requests.Session()
        source1 = test_source_class(session=shared)
        source2 = test_source_class(session=shared)
        assert source1.session is source2.session
        shared.close()

    def test_standalone_sources_get_independent_sessions(self, test_source_class):
        """Two standalone sources (no injection) get different sessions."""
        source1 = test_source_class()
        source2 = test_source_class()
        assert source1.session is not source2.session
        source1.session.close()
        source2.session.close()

    def test_session_has_connection_pooling_configured(self, test_source_class):
        """A lazily-created session has the correct pool settings."""
        source = test_source_class()
        session = source.session

        https_adapter = session.get_adapter("https://example.com")
        http_adapter = session.get_adapter("http://example.com")

        from requests.adapters import HTTPAdapter

        assert isinstance(https_adapter, HTTPAdapter)
        assert isinstance(http_adapter, HTTPAdapter)
        assert https_adapter._pool_connections == 10
        assert https_adapter._pool_maxsize == 20
        session.close()

    def test_close_session_classmethod_is_deprecated_noop(self):
        """BaseSource.close_session() emits DeprecationWarning and does nothing."""
        import warnings

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            BaseSource.close_session()

        assert len(caught) == 1
        assert issubclass(caught[0].category, DeprecationWarning)
        assert "close_session" in str(caught[0].message)

    def test_two_collectors_have_independent_sessions(self):
        """Each Collector gets its own session — no shared singleton."""
        from gameinsights import Collector

        c1 = Collector()
        c2 = Collector()
        try:
            assert c1._session is not c2._session
            assert c1.steamstore._session is c1._session
            assert c2.steamstore._session is c2._session
        finally:
            c1.close()
            c2.close()

    def test_collector_context_manager_closes_session(self):
        """Collector.__exit__ closes the owned session."""
        from gameinsights import Collector

        with Collector() as collector:
            session = collector._session
            assert isinstance(session, requests.Session)
        # close() is idempotent
        collector._session.close()

    def test_collector_close_is_idempotent(self):
        """Calling close() twice does not raise."""
        from gameinsights import Collector

        collector = Collector()
        collector.close()
        collector.close()  # must not raise

    def test_create_session_configures_pool(self):
        """Collector._create_session() returns a session with correct adapters."""
        from requests.adapters import HTTPAdapter

        from gameinsights import Collector

        session = Collector._create_session()
        adapter = session.get_adapter("https://example.com")
        assert isinstance(adapter, HTTPAdapter)
        assert adapter._pool_connections == 10
        assert adapter._pool_maxsize == 20
        session.close()
