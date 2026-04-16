from __future__ import annotations

import json
import logging
import os
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator


def _is_enabled() -> bool:
    return os.getenv("GAMEINSIGHTS_METRICS", "").lower() in {"1", "true", "yes"}


def _build_logger() -> logging.Logger:
    logger = logging.getLogger("gameinsights.metrics")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


@dataclass
class TimerResult:
    duration: float = 0.0


class MetricsCollector:
    """Lightweight metrics collector that emits structured logs when enabled."""

    def __init__(self) -> None:
        self._enabled = _is_enabled()
        self._lock = threading.Lock()
        self._logger = _build_logger()

    def _emit(self, metric_type: str, name: str, value: float, labels: dict[str, Any]) -> None:
        if not self._enabled:
            return
        payload = {
            "metric": name,
            "type": metric_type,
            "value": value,
            "labels": labels,
            "timestamp": time.time(),
        }
        with self._lock:
            self._logger.info(json.dumps(payload, default=str))

    def counter(self, name: str, value: int = 1, **labels: Any) -> None:
        """Increment a counter metric."""
        self._emit("counter", name, value, labels)

    def observe(self, name: str, value: float, **labels: Any) -> None:
        """Record an observation (histogram/gauge)."""
        self._emit("observation", name, value, labels)

    @contextmanager
    def timer(self, name: str, **labels: Any) -> Iterator[TimerResult]:
        """Context manager to record elapsed seconds for an operation."""
        result = TimerResult()
        start = time.perf_counter()
        try:
            yield result
        finally:
            result.duration = time.perf_counter() - start
            self.observe(name, result.duration, **labels)


metrics = MetricsCollector()


__all__ = ["MetricsCollector", "metrics", "TimerResult"]
