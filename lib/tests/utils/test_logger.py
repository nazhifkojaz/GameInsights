from __future__ import annotations

import json
import logging

import pytest

from gameinsights.utils.logger import LoggerWrapper
from gameinsights.utils.metrics import MetricsCollector


def test_logger_wrapper_structured_logging(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GAMEINSIGHTS_LOG_JSON", raising=False)
    logger = LoggerWrapper("StructuredLogger")

    messages: list[str] = []

    class CaptureHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            messages.append(record.getMessage())

    logger._logger.handlers = [CaptureHandler()]
    logger._logger.setLevel(logging.INFO)

    logger.log("fetch complete", verbose=True, source="steamstore", duration_ms=123)

    assert messages  # ensure something was logged
    output = messages[-1]
    assert "fetch complete" in output
    assert "source=steamstore" in output
    assert "duration_ms=123" in output


def test_logger_wrapper_json_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GAMEINSIGHTS_LOG_JSON", "1")
    logger = LoggerWrapper("JsonLogger")

    messages: list[str] = []

    class CaptureHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            messages.append(record.getMessage())

    logger._logger.handlers = [CaptureHandler()]
    logger._logger.setLevel(logging.INFO)

    logger.log("fetch start", verbose=True, source="steamspy")

    assert messages
    payload = json.loads(messages[-1])
    assert payload["message"] == "fetch start"
    assert payload["source"] == "steamspy"
    assert payload["logger"] == "JsonLogger"


def test_metrics_collector_emits_when_enabled(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GAMEINSIGHTS_METRICS", "1")
    collector = MetricsCollector()

    with caplog.at_level(logging.INFO, logger="gameinsights.metrics"):
        collector.counter("test_counter", source="steamstore")
        with collector.timer("test_timer_seconds", source="steamstore"):
            pass

    counter_record = next(
        rec for rec in caplog.records if '"metric": "test_counter"' in rec.message
    )
    counter_payload = json.loads(counter_record.message)
    assert counter_payload["type"] == "counter"
    assert counter_payload["labels"]["source"] == "steamstore"

    timer_record = next(
        rec for rec in caplog.records if '"metric": "test_timer_seconds"' in rec.message
    )
    timer_payload = json.loads(timer_record.message)
    assert timer_payload["type"] == "observation"
    assert timer_payload["labels"]["source"] == "steamstore"
    assert timer_payload["value"] >= 0.0
