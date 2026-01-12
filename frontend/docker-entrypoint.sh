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

# Configure API URL
if [ -n "$NEXT_PUBLIC_API_URL" ]; then
    echo "Configuring API URL: $NEXT_PUBLIC_API_URL"
    find /app/.next -type f \( -name "*.js" -o -name "*.html" -o -name "*.json" -o -name "*.rsc" -o -name "*.map" \) -exec sed -i "s|${API_URL_PLACEHOLDER}|${NEXT_PUBLIC_API_URL}|g" {} + 2>/dev/null || true
    if [ -f /app/server.js ]; then
        sed -i "s|${API_URL_PLACEHOLDER}|${NEXT_PUBLIC_API_URL}|g" /app/server.js
    fi
else
    echo "No NEXT_PUBLIC_API_URL set, using default http://localhost:8000"
fi

# Configure WebSocket URL
if [ -n "$NEXT_PUBLIC_WS_URL" ]; then
    echo "Configuring WebSocket URL: $NEXT_PUBLIC_WS_URL"
    find /app/.next -type f \( -name "*.js" -o -name "*.html" -o -name "*.json" -o -name "*.rsc" -o -name "*.map" \) -exec sed -i "s|${WS_URL_PLACEHOLDER}|${NEXT_PUBLIC_WS_URL}|g" {} + 2>/dev/null || true
    if [ -f /app/server.js ]; then
        sed -i "s|${WS_URL_PLACEHOLDER}|${NEXT_PUBLIC_WS_URL}|g" /app/server.js
    fi
else
    echo "No NEXT_PUBLIC_WS_URL set, using default ws://localhost:8000"
fi

echo "Configuration complete"

# Execute the main command
exec "$@"
