#!/usr/bin/env python3
"""Centralized, configurable logging for LLM Gateway.

This mirrors the configurability of the LinTO Studio API (which uses Winston):
selectable "transports" (console, rotating file, HTTP POST, Google Cloud
Logging / Stackdriver), per-sink levels, and text-or-JSON formatting, all driven
by environment variables.

Two ways to configure, in order of precedence:

1. ``LOGGING_CONFIG_FILE`` - path to a JSON file passed verbatim to
   ``logging.config.dictConfig`` (the Winston ``WINSTON_CONFIG_PATH`` equivalent).
   Full control; the env vars below are ignored when this is set.

2. Environment variables (the common case):
   - ``LOG_LEVEL``        text level, e.g. INFO / DEBUG (DEBUG forced when DEBUG=true)
   - ``LOG_FORMAT``       ``text`` (default) or ``json``
   - ``LOG_NAME``         service label injected into JSON logs (default: llm-gateway)
   - ``LOG_FILE``         path -> enables a rotating file sink
   - ``LOG_HTTP_URL``     URL -> ships every record as JSON via HTTP POST
   - ``LOG_STACKDRIVER_ENABLED`` -> ships to Google Cloud Logging
   See ``app/core/config.py`` and ``.env.example`` for every knob.

The HTTP sink runs behind a background queue so the network round-trip never
blocks the request/worker thread. Logging never raises into application code:
sink errors are swallowed.
"""
from __future__ import annotations

import atexit
import json
import logging
import logging.config
import logging.handlers
import queue
import sys
import urllib.request
from datetime import datetime
from typing import Optional

# python-json-logger moved JsonFormatter between 2.x and 3.x; support both.
try:  # python-json-logger >= 3.0
    from pythonjsonlogger.json import JsonFormatter
except ImportError:  # pragma: no cover - older releases
    from pythonjsonlogger.jsonlogger import JsonFormatter


# Kept identical to the previous hardcoded format for backward compatibility.
DEFAULT_TEXT_FORMAT = "%(asctime)s %(name)s %(levelname)s: %(message)s"
DEFAULT_DATE_FORMAT = "%d/%m/%Y %H:%M:%S"
# JSON logs carry ISO-8601 timestamps with millisecond precision (see ISOJsonFormatter).
JSON_FIELD_FORMAT = "%(asctime)s %(levelname)s %(name)s %(service)s %(message)s"


class ISOJsonFormatter(JsonFormatter):
    """JSON formatter with ISO-8601 timestamps at millisecond precision.

    strftime-based datefmt cannot emit sub-second precision, which matters for
    ordering events in a centralized log store, so formatTime is overridden to
    produce e.g. ``2026-06-16T20:02:43.123+02:00`` (local tz offset included).
    """

    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created).astimezone()
        return dt.isoformat(timespec="milliseconds")

# Module state so reconfiguration (e.g. Celery forks) is idempotent and the
# background HTTP listener thread is not leaked.
_listener: Optional[logging.handlers.QueueListener] = None
_configured = False
_atexit_registered = False


def _safe_stop_listener() -> None:
    """Stop the current HTTP queue listener once, tolerating repeat calls.

    ``QueueListener.stop()`` raises if called twice (it nulls its thread), which
    happens when a reconfigure already stopped it and atexit fires afterwards.
    """
    global _listener
    if _listener is not None and getattr(_listener, "_thread", None) is not None:
        try:
            _listener.stop()
        except Exception:
            pass


class ServiceFilter(logging.Filter):
    """Attach a static ``service`` attribute to every record.

    Handler-level filter (not logger-level) so it also runs for records that
    propagate up from child loggers. Needed because the JSON format references
    ``%(service)s``.
    """

    def __init__(self, service: str):
        super().__init__()
        self.service = service

    def filter(self, record: logging.LogRecord) -> bool:
        record.service = self.service
        return True


class HTTPJSONHandler(logging.Handler):
    """Ship each log record as a JSON document via HTTP POST.

    Meant to sit behind a :class:`~logging.handlers.QueueListener` so the
    network round-trip happens on a background thread. Network/serialization
    errors are routed through ``handleError`` and never propagate to the caller.
    """

    def __init__(self, url: str, method: str = "POST",
                 headers: Optional[dict] = None, timeout: float = 5.0):
        super().__init__()
        self.url = url
        self.method = (method or "POST").upper()
        self.timeout = timeout
        self.headers = {"Content-Type": "application/json"}
        if headers:
            self.headers.update(headers)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            body = self.format(record).encode("utf-8")
            request = urllib.request.Request(
                self.url, data=body, method=self.method, headers=self.headers
            )
            with urllib.request.urlopen(request, timeout=self.timeout):
                pass
        except Exception:  # logging must never crash the app
            self.handleError(record)


def _name_to_level(value, default: int) -> int:
    """Resolve a textual level (``"DEBUG"``) to its int, falling back safely."""
    if not value:
        return default
    level = logging.getLevelName(str(value).upper())
    return level if isinstance(level, int) else default


def _build_formatter(fmt: str) -> logging.Formatter:
    if (fmt or "text").lower() == "json":
        return ISOJsonFormatter(
            JSON_FIELD_FORMAT,
            rename_fields={
                "asctime": "timestamp",
                "levelname": "level",
                "name": "logger",
            },
        )
    return logging.Formatter(DEFAULT_TEXT_FORMAT, datefmt=DEFAULT_DATE_FORMAT)


def _parse_headers(raw: str) -> dict:
    if not raw:
        return {}
    try:
        headers = json.loads(raw)
        if isinstance(headers, dict):
            return headers
    except (ValueError, TypeError):
        pass
    logging.getLogger(__name__).warning(
        "LOG_HTTP_HEADERS is not a valid JSON object; ignoring it."
    )
    return {}


def _build_stackdriver_handler(settings) -> Optional[logging.Handler]:
    """Build a Google Cloud Logging handler if the optional dep is installed."""
    try:
        import google.cloud.logging
        from google.cloud.logging_v2.handlers import CloudLoggingHandler
    except ImportError:
        logging.getLogger(__name__).warning(
            "LOG_STACKDRIVER_ENABLED is set but google-cloud-logging is not "
            "installed; skipping the Stackdriver sink. "
            "Install it with: pip install google-cloud-logging"
        )
        return None
    client_kwargs = {}
    if settings.log_stackdriver_project:
        client_kwargs["project"] = settings.log_stackdriver_project
    client = google.cloud.logging.Client(**client_kwargs)
    return CloudLoggingHandler(client, name=settings.log_name)


def setup_logging(service: Optional[str] = None, force: bool = False) -> None:
    """Configure root logging from settings. Idempotent unless ``force=True``.

    Args:
        service: service label for JSON logs / Stackdriver. Defaults to
            ``LOG_NAME``. Useful to distinguish API vs worker processes.
        force: rebuild handlers even if logging was already configured (used
            after a Celery worker fork, where the listener thread is not
            inherited).
    """
    global _configured, _listener, _atexit_registered

    if _configured and not force:
        return

    # Late import: logging_config must be importable before settings exist.
    from app.core.config import settings

    # Option 1: full external dictConfig override (Winston WINSTON_CONFIG_PATH).
    if settings.logging_config_file:
        with open(settings.logging_config_file, "r", encoding="utf-8") as handle:
            logging.config.dictConfig(json.load(handle))
        _configured = True
        return

    service_name = service or settings.log_name
    root_level = (
        logging.DEBUG if settings.debug
        else _name_to_level(settings.log_level, logging.INFO)
    )
    formatter = _build_formatter(settings.log_format)
    service_filter = ServiceFilter(service_name)

    root = logging.getLogger()

    # Reset so repeated calls / re-imports do not stack duplicate handlers.
    for handler in list(root.handlers):
        root.removeHandler(handler)
    _safe_stop_listener()
    _listener = None

    root.setLevel(root_level)

    direct_handlers: list[logging.Handler] = []

    # --- console (always on, stdout) -------------------------------------
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(root_level)
    direct_handlers.append(console)

    # --- rotating file ---------------------------------------------------
    if settings.log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            settings.log_file,
            maxBytes=settings.log_file_max_bytes,
            backupCount=settings.log_file_backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(_name_to_level(settings.log_file_level, root_level))
        direct_handlers.append(file_handler)

    # --- Google Cloud Logging / Stackdriver ------------------------------
    if settings.log_stackdriver_enabled:
        sd_handler = _build_stackdriver_handler(settings)
        if sd_handler is not None:
            sd_handler.setLevel(
                _name_to_level(settings.log_stackdriver_level, root_level)
            )
            direct_handlers.append(sd_handler)

    for handler in direct_handlers:
        handler.setFormatter(formatter)
        handler.addFilter(service_filter)
        root.addHandler(handler)

    # --- HTTP POST (non-blocking, behind a background queue listener) ----
    if settings.log_http_url:
        http_handler = HTTPJSONHandler(
            settings.log_http_url,
            method=settings.log_http_method,
            headers=_parse_headers(settings.log_http_headers),
            timeout=settings.log_http_timeout,
        )
        # The HTTP sink always ships JSON regardless of the console format.
        http_handler.setFormatter(_build_formatter("json"))
        http_handler.setLevel(_name_to_level(settings.log_http_level, root_level))

        log_queue: queue.SimpleQueue = queue.SimpleQueue()
        queue_handler = logging.handlers.QueueHandler(log_queue)
        queue_handler.addFilter(service_filter)
        root.addHandler(queue_handler)

        _listener = logging.handlers.QueueListener(
            log_queue, http_handler, respect_handler_level=True
        )
        _listener.start()
        if not _atexit_registered:
            # Single handler that flushes whatever listener is current at exit.
            atexit.register(_safe_stop_listener)
            _atexit_registered = True

    _configured = True
