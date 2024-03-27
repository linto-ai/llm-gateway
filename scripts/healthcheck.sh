#!/usr/bin/env bash

set -eax

if [ "$SERVICE_MODE" = "http" ]
then
    curl --fail http://localhost:80/healthcheck || exit 1
else
    # Update last alive
    python -c "from celery_app.register import register; register(is_heartbeat=True)"
    
    # Ping worker
    celery --app=celery_app.celeryapp inspect ping -d keyword_extraction_$SERVICE_NAME@$HOSTNAME || exit 1  # TBR name?
fi
