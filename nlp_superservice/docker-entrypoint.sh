#!/bin/bash
set -e
echo "RUNNING : NLP service"
env 

./wait-for-it.sh $(echo $SERVICES_BROKER | cut -d'/' -f 3) --timeout=20 --strict -- echo " $REDIS_BROKER (Service Broker) is up"
./wait-for-it.sh $MONGO_HOST:$MONGO_PORT --timeout=20 --strict -- echo " $MONGO_HOST:$MONGO_PORT  (MONGO DB) is up"

supervisord -c supervisor/supervisor.conf
supervisorctl -c supervisor/supervisor.conf tail -f ingress stderr
