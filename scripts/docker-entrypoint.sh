#!/bin/bash
# Start FastAPI
python -m app &
# Start Celery
celery -A app.http_server.celery_app.celery_app worker --loglevel=info -c ${CONCURRENCY:-1}
wait