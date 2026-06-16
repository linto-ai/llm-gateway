# Logging Guide

LLM Gateway uses a single, configurable logging setup driven by environment
variables. It can write human readable text to stdout (the default) or
structured JSON, and ship logs to one or more destinations at the same time:
console, a rotating file, an HTTP collector, or Google Cloud Logging
(Stackdriver).

Logging is configured once at process startup (API server, Celery workers and
seed scripts) by `app/core/logging_config.py`. You do not call it yourself.

## Quick Start

The defaults work out of the box (text logs on stdout at `INFO`). To customize,
set variables in your `.env`:

```bash
# .env
LOG_LEVEL=INFO        # DEBUG / INFO / WARNING / ERROR
LOG_FORMAT=text       # text (default) or json
```

Set `LOG_FORMAT=json` as soon as you collect logs with an aggregator (Loki, ELK,
Cloud Logging) that scrapes container stdout. JSON keeps the fields structured.

## Configuration Modes

There are two ways to configure logging, in order of precedence:

1. **`LOGGING_CONFIG_FILE`** points to a JSON file passed verbatim to Python's
   [`logging.config.dictConfig`](https://docs.python.org/3/library/logging.config.html#logging-config-dictschema).
   This gives full control over formatters, handlers and loggers. When set, all
   the `LOG_*` variables below are ignored. This is the equivalent of the LinTO
   Studio API `WINSTON_CONFIG_PATH`.

2. **Environment variables** (the common case), documented below.

## Environment Variables

### General

| Variable             | Description                                              | Default        |
|----------------------|----------------------------------------------------------|----------------|
| `LOG_LEVEL`          | Root level: `DEBUG` / `INFO` / `WARNING` / `ERROR`       | `INFO`         |
| `LOG_FORMAT`         | `text` or `json`                                         | `text`         |
| `LOG_NAME`           | Service label added to JSON / Stackdriver entries        | `llm-gateway`  |
| `DEBUG`              | When `true`, forces `LOG_LEVEL` to `DEBUG`               | `false`        |
| `LOGGING_CONFIG_FILE`| Path to a `dictConfig` JSON file (full override)         | (unset)        |

Each sink below is **disabled until its trigger variable is set**. The console
sink (stdout) is always on. Every sink has an optional dedicated level that
falls back to `LOG_LEVEL` when left empty, so you can, for example, keep `INFO`
on the console while only shipping `ERROR` over HTTP.

### Rotating File

Trigger: `LOG_FILE`.

| Variable                | Description                          | Default        |
|-------------------------|--------------------------------------|----------------|
| `LOG_FILE`              | Path to the log file (enables sink)  | (unset)        |
| `LOG_FILE_LEVEL`        | Level for this sink                  | `LOG_LEVEL`    |
| `LOG_FILE_MAX_BYTES`    | Rotate after this size               | `10485760` (10 MiB) |
| `LOG_FILE_BACKUP_COUNT` | Number of rotated files to keep      | `5`            |

### HTTP POST

Trigger: `LOG_HTTP_URL`. Each record is shipped as a JSON document via HTTP POST
to a centralized collector (Logstash HTTP input, Loki, Datadog, a custom
endpoint, etc.). The POST runs on a background queue, so it never blocks the
request or worker thread, and network errors are swallowed so logging cannot
crash the app. Records are always sent as JSON regardless of `LOG_FORMAT`.

| Variable           | Description                                          | Default     |
|--------------------|------------------------------------------------------|-------------|
| `LOG_HTTP_URL`     | Collector URL (enables sink)                         | (unset)     |
| `LOG_HTTP_METHOD`  | HTTP method                                          | `POST`      |
| `LOG_HTTP_HEADERS` | Extra headers as a JSON object (e.g. auth token)     | `{}`        |
| `LOG_HTTP_LEVEL`   | Level for this sink                                  | `LOG_LEVEL` |
| `LOG_HTTP_TIMEOUT` | Per-request timeout in seconds                       | `5.0`       |

### Google Cloud Logging (Stackdriver)

Trigger: `LOG_STACKDRIVER_ENABLED`. Requires the optional `google-cloud-logging`
package (commented in `requirements.txt`; uncomment to install). If the package
is missing, the sink is skipped with a warning rather than failing startup.

| Variable                    | Description                                  | Default     |
|-----------------------------|----------------------------------------------|-------------|
| `LOG_STACKDRIVER_ENABLED`   | Enable the sink                              | `false`     |
| `LOG_STACKDRIVER_PROJECT`   | GCP project id (auto-detected when empty)    | (auto)      |
| `LOG_STACKDRIVER_LEVEL`     | Level for this sink                          | `LOG_LEVEL` |

Authentication uses standard Google credentials
([Application Default Credentials](https://cloud.google.com/docs/authentication/application-default-credentials)):
a `GOOGLE_APPLICATION_CREDENTIALS` service account file, or the workload identity
of the GKE pod / GCE instance.

## JSON Output

With `LOG_FORMAT=json`, each line is a JSON object with ISO-8601 timestamps:

```json
{"timestamp": "2026-06-16T20:02:43.123+02:00", "level": "INFO", "logger": "http_server", "service": "llm-gateway-api", "message": "Starting FastAPI application...", "job_id": "abc"}
```

| Field       | Source                                                        |
|-------------|---------------------------------------------------------------|
| `timestamp` | record time, ISO-8601 with milliseconds (renamed from `asctime`) |
| `level`     | log level (renamed from `levelname`)                          |
| `logger`    | logger name (renamed from `name`)                             |
| `service`   | value of `LOG_NAME`, or the per-process label (see below)     |
| `message`   | the log message                                               |
| *extras*    | any keyword passed via `logger.info(msg, extra={...})`        |

The `service` field is set per process so you can tell them apart:
`llm-gateway-api` (HTTP server), `llm-gateway-worker` (Celery), `llm-gateway-seed`
(seed scripts).

## Examples

### Ship JSON to an HTTP collector with an auth token

```bash
# .env
LOG_FORMAT=json
LOG_HTTP_URL=https://logs.example.com/ingest
LOG_HTTP_HEADERS={"Authorization": "Bearer my-token"}
LOG_HTTP_LEVEL=INFO
```

### Console at INFO, errors also to a rotating file

```bash
LOG_LEVEL=INFO
LOG_FILE=/var/log/llm-gateway/app.log
LOG_FILE_LEVEL=ERROR
```

### Google Cloud Logging on GKE

```bash
# requirements.txt: uncomment google-cloud-logging, then rebuild the image
LOG_STACKDRIVER_ENABLED=true
LOG_STACKDRIVER_PROJECT=my-gcp-project
```

### Full control via a dictConfig file

```bash
LOGGING_CONFIG_FILE=/app/config/logging.json
```

```json
{
  "version": 1,
  "disable_existing_loggers": false,
  "formatters": {
    "json": {
      "()": "pythonjsonlogger.json.JsonFormatter",
      "format": "%(asctime)s %(levelname)s %(name)s %(message)s"
    }
  },
  "handlers": {
    "console": { "class": "logging.StreamHandler", "formatter": "json" }
  },
  "root": { "handlers": ["console"], "level": "INFO" }
}
```

The custom HTTP handler is importable for use in a dictConfig file as
`app.core.logging_config.HTTPJSONHandler` (params: `url`, `method`, `headers`,
`timeout`).

## Notes

- **Uvicorn access logs** flow through the same sinks (uvicorn is started with
  `log_config=None` so its loggers propagate to the root logger). `GET /healthcheck`
  requests are filtered out to keep the output clean.
- **Celery workers** are configured via the `setup_logging` and
  `worker_process_init` signals, so the configured sinks apply to task logs in
  every forked worker process.
- **Hot-reload**: the gateway backend runs in Docker, where Python hot-reload may
  not pick up changes reliably. After changing logging env vars, restart the
  `llm-gateway` and `celery-worker` containers.

## Using a Logger in Code

Nothing special is required. Get a module logger and use it; it inherits the
configured sinks, level and format:

```python
import logging

logger = logging.getLogger(__name__)
logger.info("processing job", extra={"job_id": job_id})  # extras become JSON fields
```
