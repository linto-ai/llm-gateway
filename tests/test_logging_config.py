"""Configurable logging - unit tests.

Covers the env-driven sink selection (console / rotating file / HTTP POST),
text-vs-JSON formatting, level resolution, the dictConfig file override, and the
HTTPJSONHandler shipping behaviour. Each test snapshots and restores the root
logger so it does not leak handlers into the rest of the suite.
"""
import json
import logging
import logging.handlers
from unittest.mock import patch, MagicMock

import pytest

from app.core.config import settings
import app.core.logging_config as lc
from app.core.logging_config import (
    setup_logging,
    HTTPJSONHandler,
    ServiceFilter,
    _name_to_level,
    _parse_headers,
)


LOG_ATTRS = (
    "logging_config_file", "log_level", "log_format", "log_name",
    "log_file", "log_file_level", "log_file_max_bytes", "log_file_backup_count",
    "log_http_url", "log_http_method", "log_http_headers", "log_http_level",
    "log_http_timeout", "log_stackdriver_enabled", "log_stackdriver_project",
    "log_stackdriver_level", "debug",
)


@pytest.fixture
def clean_logging():
    """Restore root logger + module state and reset logging defaults around each test."""
    root = logging.getLogger()
    saved_handlers = list(root.handlers)
    saved_level = root.level
    saved_settings = {a: getattr(settings, a) for a in LOG_ATTRS}
    saved_listener = lc._listener
    saved_configured = lc._configured

    # Known baseline for the test body.
    settings.logging_config_file = ""
    settings.log_level = "INFO"
    settings.log_format = "text"
    settings.log_name = "llm-gateway-test"
    settings.log_file = ""
    settings.log_file_level = ""
    settings.log_http_url = ""
    settings.log_http_level = ""
    settings.log_http_method = "POST"
    settings.log_http_headers = ""
    settings.log_http_timeout = 5.0
    settings.log_stackdriver_enabled = False
    settings.debug = False
    lc._listener = None

    yield

    lc._safe_stop_listener()
    lc._listener = saved_listener
    lc._configured = saved_configured
    for a, v in saved_settings.items():
        setattr(settings, a, v)
    for h in list(root.handlers):
        root.removeHandler(h)
    for h in saved_handlers:
        root.addHandler(h)
    root.setLevel(saved_level)


def _capture_console(buf):
    """Point the console StreamHandler at an in-memory buffer."""
    for h in logging.getLogger().handlers:
        if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.handlers.QueueHandler):
            h.stream = buf


# --------------------------------------------------------------------------- #
# Formatting
# --------------------------------------------------------------------------- #

def test_text_format_is_default(clean_logging):
    setup_logging(force=True)
    root = logging.getLogger()
    handlers = [type(h).__name__ for h in root.handlers]
    assert handlers == ["StreamHandler"]
    assert isinstance(root.handlers[0].formatter, logging.Formatter)


def test_json_format_emits_structured_record(clean_logging):
    import io
    settings.log_format = "json"
    setup_logging(service="svc-x", force=True)
    buf = io.StringIO()
    _capture_console(buf)

    logging.getLogger("demo").info("hello", extra={"job_id": "abc"})

    record = json.loads(buf.getvalue().strip())
    assert record["level"] == "INFO"
    assert record["logger"] == "demo"
    assert record["service"] == "svc-x"
    assert record["message"] == "hello"
    assert record["job_id"] == "abc"        # extra fields are preserved
    # asctime renamed to timestamp, ISO-8601 with millisecond precision
    assert "timestamp" in record
    from datetime import datetime
    parsed_ts = datetime.fromisoformat(record["timestamp"])
    assert parsed_ts.tzinfo is not None     # carries a timezone offset
    assert "." in record["timestamp"]       # sub-second precision present


# --------------------------------------------------------------------------- #
# Level resolution
# --------------------------------------------------------------------------- #

def test_log_level_applied(clean_logging):
    settings.log_level = "WARNING"
    setup_logging(force=True)
    assert logging.getLogger().level == logging.WARNING


def test_debug_flag_forces_debug(clean_logging):
    settings.log_level = "WARNING"
    settings.debug = True
    setup_logging(force=True)
    assert logging.getLogger().level == logging.DEBUG


@pytest.mark.parametrize("value,expected", [
    ("DEBUG", logging.DEBUG),
    ("warning", logging.WARNING),
    ("", logging.INFO),       # empty -> default
    ("NOPE", logging.INFO),   # invalid -> default
])
def test_name_to_level(value, expected):
    assert _name_to_level(value, logging.INFO) == expected


# --------------------------------------------------------------------------- #
# Sinks
# --------------------------------------------------------------------------- #

def test_file_sink_enabled(clean_logging, tmp_path):
    settings.log_file = str(tmp_path / "app.log")
    setup_logging(force=True)
    file_handlers = [
        h for h in logging.getLogger().handlers
        if isinstance(h, logging.handlers.RotatingFileHandler)
    ]
    assert len(file_handlers) == 1
    assert file_handlers[0].maxBytes == settings.log_file_max_bytes


def test_http_sink_uses_background_listener(clean_logging):
    settings.log_http_url = "http://collector.local/ingest"
    settings.log_http_level = "ERROR"
    setup_logging(force=True)

    root = logging.getLogger()
    queue_handlers = [h for h in root.handlers if isinstance(h, logging.handlers.QueueHandler)]
    assert len(queue_handlers) == 1
    assert lc._listener is not None
    assert lc._listener._thread.is_alive()

    shipped = lc._listener.handlers[0]
    assert isinstance(shipped, HTTPJSONHandler)
    assert shipped.level == logging.ERROR     # per-sink level honoured
    assert shipped.url == "http://collector.local/ingest"


def test_no_sink_without_trigger(clean_logging):
    setup_logging(force=True)
    root = logging.getLogger()
    assert not any(isinstance(h, logging.handlers.QueueHandler) for h in root.handlers)
    assert not any(isinstance(h, logging.handlers.RotatingFileHandler) for h in root.handlers)


# --------------------------------------------------------------------------- #
# dictConfig override
# --------------------------------------------------------------------------- #

def test_config_file_override_takes_precedence(clean_logging, tmp_path):
    override = {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {"c": {"class": "logging.StreamHandler"}},
        "root": {"handlers": ["c"], "level": "WARNING"},
    }
    cfg_path = tmp_path / "logging.json"
    cfg_path.write_text(json.dumps(override))

    settings.logging_config_file = str(cfg_path)
    settings.log_http_url = "http://should-be-ignored.local"
    setup_logging(force=True)

    # The env-driven HTTP sink must be ignored when a dictConfig file is given.
    assert logging.getLogger().level == logging.WARNING
    assert not any(
        isinstance(h, logging.handlers.QueueHandler)
        for h in logging.getLogger().handlers
    )


# --------------------------------------------------------------------------- #
# HTTPJSONHandler / helpers
# --------------------------------------------------------------------------- #

def test_http_handler_posts_json_with_headers():
    handler = HTTPJSONHandler(
        "http://collector.local/ingest",
        headers={"Authorization": "Bearer t"},
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    record = logging.LogRecord("n", logging.INFO, __file__, 1, "payload", None, None)

    with patch("urllib.request.urlopen") as urlopen:
        urlopen.return_value.__enter__.return_value = MagicMock()
        handler.emit(record)

    request = urlopen.call_args[0][0]
    assert request.full_url == "http://collector.local/ingest"
    assert request.method == "POST"
    assert request.data == b"payload"
    assert request.headers["Content-type"] == "application/json"
    assert request.headers["Authorization"] == "Bearer t"


def test_http_handler_swallows_network_errors():
    handler = HTTPJSONHandler("http://collector.local/ingest")
    handler.setFormatter(logging.Formatter("%(message)s"))
    record = logging.LogRecord("n", logging.INFO, __file__, 1, "x", None, None)
    with patch("urllib.request.urlopen", side_effect=OSError("boom")), \
         patch.object(handler, "handleError") as handle_error:
        handler.emit(record)        # must not raise
        handle_error.assert_called_once()


def test_service_filter_injects_attribute():
    record = logging.LogRecord("n", logging.INFO, __file__, 1, "x", None, None)
    assert ServiceFilter("my-svc").filter(record) is True
    assert record.service == "my-svc"


@pytest.mark.parametrize("raw,expected", [
    ("", {}),
    ('{"A": "B"}', {"A": "B"}),
    ("not-json", {}),
    ('["list", "not", "object"]', {}),
])
def test_parse_headers(raw, expected):
    assert _parse_headers(raw) == expected
