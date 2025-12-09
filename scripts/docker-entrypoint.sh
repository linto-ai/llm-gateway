#!/bin/bash
set -e

# Simple entrypoint - no user creation needed (handled at build time)
# Container already runs as appuser due to USER directive in Dockerfile

# Extract host:port from a URL (postgresql://user:pass@host:port/db or redis://...)
parse_url() {
    local url="$1"
    local default_port="$2"

    # Remove scheme (everything before ://)
    local without_scheme="${url#*://}"
    # Remove credentials (everything before @)
    local without_creds="${without_scheme#*@}"
    # Remove path (everything after /)
    local host_port="${without_creds%%/*}"

    # Split host and port
    if [[ "$host_port" == *:* ]]; then
        echo "${host_port%:*}" "${host_port##*:}"
    else
        echo "$host_port" "$default_port"
    fi
}

# Wait for PostgreSQL
if [ -n "$DATABASE_URL" ]; then
    read -r DB_HOST DB_PORT <<< "$(parse_url "$DATABASE_URL" 5432)"
    echo "Waiting for PostgreSQL at $DB_HOST:$DB_PORT..."
    ./scripts/wait-for-it.sh "$DB_HOST:$DB_PORT" -t 60 -q
fi

# Wait for Redis
if [ -n "$CELERY_BROKER_URL" ]; then
    read -r REDIS_HOST REDIS_PORT <<< "$(parse_url "$CELERY_BROKER_URL" 6379)"
    echo "Waiting for Redis at $REDIS_HOST:$REDIS_PORT..."
    ./scripts/wait-for-it.sh "$REDIS_HOST:$REDIS_PORT" -t 60 -q
fi

# Run database migrations (only for API server, not celery workers)
if [[ "$1" != "celery" && "$1" != *"celery"* ]]; then
    echo "Running database migrations..."
    alembic upgrade head
fi

# Execute command passed as argument
exec "$@"
