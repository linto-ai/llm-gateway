#!/bin/bash

echo "RUNNING service"

export VERSION=$(awk -v RS='' '/#/ {print; exit}' RELEASE.md | head -1 | sed 's/#//' | sed 's/ //')

if [ -z "$SERVICE_MODE" ]
then
    echo "ERROR: Must specify a serving mode: [ http | task ]"
    exit -1
else
    if [ "$SERVICE_MODE" = "http" ]
    then
        echo "Running http server"
        # HTTP API
        
        python http_server/ingress.py --debug
    elif [ "$SERVICE_MODE" == "task" ]
    then
        echo "Running celery worker" 
        /usr/src/app/wait-for-it.sh $(echo $SERVICES_BROKER | cut -d'/' -f 3) --timeout=20 --strict -- echo " $SERVICES_BROKER (Service Broker) is up"
        # MICRO SERVICE
        ## QUEUE NAME
        QUEUE=$(python -c "from celery_app.register import queue; exit(queue())" 2>&1)
        echo "Service set to $QUEUE"

        ## REGISTRATION
        python -c "from celery_app.register import register; register()"
        echo "Service registered"

        ## WORKER
        # what to put after -n ?
        celery --app=celery_app.celeryapp worker -n keyword_extraction_$SERVICE_NAME@%h --queues=$QUEUE -c $CONCURRENCY
        ## UNREGISTERING
        python -c "from celery_app.register import unregister; unregister()"
        echo "Service unregistered"
    else
        echo "ERROR: Wrong serving command: $SERVICE_MODE"
        exit -1
    fi
fi
