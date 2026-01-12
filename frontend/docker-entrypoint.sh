#!/bin/sh
set -e

# Runtime configuration substitution for Next.js
# Replaces build-time placeholders with actual runtime values

BASEPATH_PLACEHOLDER="/__NEXT_BASEPATH_PLACEHOLDER__"
API_URL_PLACEHOLDER="__NEXT_API_URL_PLACEHOLDER__"
WS_URL_PLACEHOLDER="__NEXT_WS_URL_PLACEHOLDER__"

# Configure BASE_PATH
if [ -n "$BASE_PATH" ]; then
    echo "Configuring basePath: $BASE_PATH"
    find /app/.next -type f \( -name "*.js" -o -name "*.html" -o -name "*.json" -o -name "*.rsc" -o -name "*.map" \) -exec sed -i "s|${BASEPATH_PLACEHOLDER}|${BASE_PATH}|g" {} + 2>/dev/null || true
    if [ -f /app/server.js ]; then
        sed -i "s|${BASEPATH_PLACEHOLDER}|${BASE_PATH}|g" /app/server.js
    fi
else
    echo "No BASE_PATH set, running at root path"
    find /app/.next -type f \( -name "*.js" -o -name "*.html" -o -name "*.json" -o -name "*.rsc" -o -name "*.map" \) -exec sed -i "s|${BASEPATH_PLACEHOLDER}||g" {} + 2>/dev/null || true
    if [ -f /app/server.js ]; then
        sed -i "s|${BASEPATH_PLACEHOLDER}||g" /app/server.js
    fi
fi

# Configure API URL (default to localhost:8000 if not set)
API_URL="${NEXT_PUBLIC_API_URL:-http://localhost:8000}"
echo "Configuring API URL: $API_URL"
find /app/.next -type f \( -name "*.js" -o -name "*.html" -o -name "*.json" -o -name "*.rsc" -o -name "*.map" \) -exec sed -i "s|${API_URL_PLACEHOLDER}|${API_URL}|g" {} + 2>/dev/null || true
if [ -f /app/server.js ]; then
    sed -i "s|${API_URL_PLACEHOLDER}|${API_URL}|g" /app/server.js
fi

# Configure WebSocket URL (default to localhost:8000 if not set)
WS_URL="${NEXT_PUBLIC_WS_URL:-ws://localhost:8000}"
echo "Configuring WebSocket URL: $WS_URL"
find /app/.next -type f \( -name "*.js" -o -name "*.html" -o -name "*.json" -o -name "*.rsc" -o -name "*.map" \) -exec sed -i "s|${WS_URL_PLACEHOLDER}|${WS_URL}|g" {} + 2>/dev/null || true
if [ -f /app/server.js ]; then
    sed -i "s|${WS_URL_PLACEHOLDER}|${WS_URL}|g" /app/server.js
fi

echo "Configuration complete"

# Execute the main command
exec "$@"
