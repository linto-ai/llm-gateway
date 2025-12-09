#!/usr/bin/env bash
# Healthcheck script for Celery workers
# Verifies the worker is running and can respond to ping

set -e

# Check if celery worker process is running
pgrep -f "celery.*worker" > /dev/null || exit 1

# Ping the worker to verify it's responsive
celery -A app.http_server.celery_app.celery_app inspect ping --timeout 5 2>/dev/null | grep -q "pong" || exit 1

exit 0
