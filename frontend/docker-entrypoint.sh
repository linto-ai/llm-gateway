#!/bin/sh
set -e

echo "Starting LLM Gateway Frontend"
echo "  basePath: /llm-admin (built-in)"
echo "  API_URL: ${NEXT_PUBLIC_API_URL:-auto-detect from window.location}"
echo "  WS_URL: ${NEXT_PUBLIC_WS_URL:-auto-detect from window.location}"

exec "$@"
