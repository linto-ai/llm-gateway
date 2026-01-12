#!/bin/sh
set -e

# Runtime basePath substitution for Next.js
# Replaces the build-time placeholder with the actual BASE_PATH value

PLACEHOLDER="/__NEXT_BASEPATH_PLACEHOLDER__"

if [ -n "$BASE_PATH" ]; then
    echo "Configuring basePath: $BASE_PATH"

    # Replace placeholder in all relevant files (standalone output)
    find /app/.next -type f \( -name "*.js" -o -name "*.html" -o -name "*.json" -o -name "*.rsc" \) -exec sed -i "s|${PLACEHOLDER}|${BASE_PATH}|g" {} + 2>/dev/null || true

    # Also replace in the server.js
    if [ -f /app/server.js ]; then
        sed -i "s|${PLACEHOLDER}|${BASE_PATH}|g" /app/server.js
    fi

    echo "basePath configured successfully"
else
    echo "No BASE_PATH set, running at root path"

    # Remove placeholder entirely (replace with empty string)
    find /app/.next -type f \( -name "*.js" -o -name "*.html" -o -name "*.json" -o -name "*.rsc" \) -exec sed -i "s|${PLACEHOLDER}||g" {} + 2>/dev/null || true

    if [ -f /app/server.js ]; then
        sed -i "s|${PLACEHOLDER}||g" /app/server.js
    fi
fi

# Execute the main command
exec "$@"
