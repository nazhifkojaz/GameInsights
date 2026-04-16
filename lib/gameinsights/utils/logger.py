from __future__ import annotations

import json
import logging
import os
from typing import Any


class LoggerWrapper:
    def __init__(self, name: str) -> None:
        self._logger = logging.getLogger(name)
        self._json_mode = os.getenv("GAMEINSIGHTS_LOG_JSON", "").lower() in {"1", "true", "yes"}
        self._configure_logger()

    def _configure_logger(self) -> None:
        self._logger.propagate = False
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(levelname)s - %(name)s: %(message)s"))
            self._logger.addHandler(handler)
            self._logger.setLevel(logging.INFO)

    def log(
        self, message: str, level: str = "info", verbose: bool = False, **context: Any
    ) -> None:
        """Log the message at the specified level.
        Args:
            message (str): The message to log.
            level (str): The logging level ('debug', 'info', 'warning', 'error', etc.).
            verbose (bool): If False, will not log the message
        """
        if not verbose:
            return

        formatted = self._format_message(message, context)
        getattr(self._logger, level.lower())(formatted)

    def log_event(
        self, event: str, level: str = "info", verbose: bool = False, **context: Any
    ) -> None:
        """Emit a structured log event with optional context."""
        payload = dict(context)
        payload.setdefault("event", event)
        message = payload.pop("message", event)
        self.log(message, level=level, verbose=verbose, **payload)

    def _format_message(self, message: str, context: dict[str, Any]) -> str:
        if not context:
            return message

        if self._json_mode:
            payload = {"message": message, "logger": self._logger.name, **context}
            try:
                return json.dumps(payload, default=str)
            except TypeError:
                safe_payload = {key: self._stringify(value) for key, value in payload.items()}
                return json.dumps(safe_payload)

        kv_pairs = " ".join(
            f"{key}={self._stringify(value)}" for key, value in sorted(context.items())
        )
        return f"{message} | {kv_pairs}"

    @staticmethod
    def _stringify(value: Any) -> str:
        if isinstance(value, (str, int, float, bool)) or value is None:
            return str(value)
        return repr(value)
