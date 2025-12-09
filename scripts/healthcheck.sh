#!/usr/bin/env bash
set -e
curl --fail --silent http://localhost:${HTTP_PORT:-8000}/healthcheck || exit 1
