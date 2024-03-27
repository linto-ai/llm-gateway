import os

from celery import Celery

celery = Celery(__name__, include=["nlp.processing.maintask"])
service_name = os.environ.get("SERVICE_NAME")
broker_url = os.environ.get("SERVICES_BROKER", "redis://localhost:6379")
if os.environ.get("BROKER_PASS", False):
    components = broker_url.split("//")
    broker_url = f'{components[0]}//:{os.environ.get("BROKER_PASS")}@{components[1]}'
broker_port = int(os.environ.get("SERVICES_BROKER_PORT", 6379))
celery.conf.broker_url = "{}/0".format(broker_url)
celery.conf.result_backend = "{}/1".format(broker_url)
celery.conf.update(result_expires=3600, task_acks_late=True, task_track_started=True)

# Queues
celery.conf.update(
    {
        "task_routes": {
            "nlp_task": {"queue": "{}_requests".format(service_name)},
        }
    }
)
