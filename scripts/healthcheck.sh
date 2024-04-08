#!/usr/bin/env bash
set -eax
curl --fail http://localhost:$HTTP_PORT/healthcheck || exit 1