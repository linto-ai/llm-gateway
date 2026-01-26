#!/bin/sh
set -e

BASEPATH_PLACEHOLDER="/__NEXT_BASEPATH_PLACEHOLDER__"
BASEPATH_PLACEHOLDER_ESCAPED="\\\\\\\\/__NEXT_BASEPATH_PLACEHOLDER__"
API_URL_PLACEHOLDER="__NEXT_API_URL_PLACEHOLDER__"
WS_URL_PLACEHOLDER="__NEXT_WS_URL_PLACEHOLDER__"

if [ -n "$BASE_PATH" ]; then
    echo "Configuring basePath: $BASE_PATH"
    ESCAPED_BASE_PATH=$(echo "$BASE_PATH" | sed 's|/|\\/|g')
    sed -i "s|${BASEPATH_PLACEHOLDER}|${BASE_PATH}|g" /app/server.js 2>/dev/null || true
    sed -i "s|${BASEPATH_PLACEHOLDER}|${BASE_PATH}|g" /app/.next/routes-manifest.json 2>/dev/null || true
    # Escaped version first (for regex patterns in JSON)
    find /app/.next/static -type f -name "*.json" -exec sed -i "s|${BASEPATH_PLACEHOLDER_ESCAPED}|${ESCAPED_BASE_PATH}|g" {} + 2>/dev/null || true
    find /app/.next/static -type f \( -name "*.js" -o -name "*.json" \) -exec sed -i "s|${BASEPATH_PLACEHOLDER}|${BASE_PATH}|g" {} + 2>/dev/null || true
    find /app/.next/server -type f \( -name "*.html" -o -name "*.rsc" -o -name "*.meta" -o -name "*.body" \) -exec sed -i "s|${BASEPATH_PLACEHOLDER}|${BASE_PATH}|g" {} + 2>/dev/null || true
    find /app/.next/server -type f -name "*client-reference-manifest.js" -exec sed -i "s|${BASEPATH_PLACEHOLDER}|${BASE_PATH}|g" {} + 2>/dev/null || true
    # Also handle prerender manifests and action manifests
    find /app/.next -type f -name "*.json" -exec sed -i "s|${BASEPATH_PLACEHOLDER}|${BASE_PATH}|g" {} + 2>/dev/null || true
else
    echo "No BASE_PATH set, running at root path"

    # Simple placeholder replacement - remove all occurrences
    sed -i "s|${BASEPATH_PLACEHOLDER}||g" /app/server.js 2>/dev/null || true
    find /app/.next -type f -name "*.json" -exec sed -i "s|${BASEPATH_PLACEHOLDER}||g" {} + 2>/dev/null || true
    find /app/.next/static -type f -name "*.js" -exec sed -i "s|${BASEPATH_PLACEHOLDER}||g" {} + 2>/dev/null || true
    find /app/.next/server -type f \( -name "*.html" -o -name "*.rsc" -o -name "*.meta" -o -name "*.body" \) -exec sed -i "s|${BASEPATH_PLACEHOLDER}||g" {} + 2>/dev/null || true
    find /app/.next/server -type f -name "*client-reference-manifest.js" -exec sed -i "s|${BASEPATH_PLACEHOLDER}||g" {} + 2>/dev/null || true
fi

API_URL="${NEXT_PUBLIC_API_URL:-http://localhost:8000}"
echo "Configuring API URL: $API_URL"
find /app/.next/static -type f -name "*.js" -exec sed -i "s|${API_URL_PLACEHOLDER}|${API_URL}|g" {} + 2>/dev/null || true

WS_URL="${NEXT_PUBLIC_WS_URL:-ws://localhost:8000}"
echo "Configuring WebSocket URL: $WS_URL"
find /app/.next/static -type f -name "*.js" -exec sed -i "s|${WS_URL_PLACEHOLDER}|${WS_URL}|g" {} + 2>/dev/null || true

echo "Configuration complete"
exec "$@"
