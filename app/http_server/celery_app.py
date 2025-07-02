from celery import Celery
from celery.result import AsyncResult
from urllib.parse import urlparse
import logging
from celery.app import trace
from conf import cfg_instance
from app.backends.llm_inference import LLMInferenceEngine
import redis
from celery.signals import after_task_publish
import time

# Edit the celery logs format
trace.LOG_SUCCESS = """\
Task %(name)s[%(id)s] succeeded in %(runtime)ss\
"""

# Get configuration
cfg = cfg_instance(cfg_name="config")

# Logging Setup
logging.basicConfig(
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
)
logger = logging.getLogger("celery_worker")
logger.setLevel(logging.DEBUG if cfg.debug else logging.INFO)

# Celery App Setup
celery_app = Celery("tasks")

# Configure the broker and backend from environment variables with defaults
services_broker = cfg.services_broker.url
broker_pass = cfg.services_broker.password
parsed_url = urlparse(services_broker)
broker_url = f"{parsed_url.scheme}://:{broker_pass}@{parsed_url.hostname}:{parsed_url.port}"
celery_app.conf.broker_url = f"{broker_url}/0"
celery_app.conf.result_backend = f"{broker_url}/1"

redis_client = redis.Redis(host=parsed_url.hostname,port= parsed_url.port, password=broker_pass)

# Define the task
@celery_app.task(bind=True)
def process_task(self, task_data):
    logger.info(f"Starting celery task : {self.request.id}")
    self.update_state(state='STARTED')
    task_data['task_id'] = self.request.id

    # Add the task ID to the list of task IDs
    add_task_id(self.request.id)

    # Run the task
    try:
        # Initialize backend
        engine = LLMInferenceEngine(task_data=task_data, celery_task=self)

        # Run summarization
        summary = engine.run()
        
        return summary
    
    except Exception as e:
        logger.error(f"An error occurred in processing tasks : {str(e)}")
        raise

# Set publish tasked status to QUEUED
@after_task_publish.connect
def update_sent_state(sender=None, headers=None, **kwargs):
    # the task may not exist if sent using `send_task` which
    # sends tasks by name, so fall back to the default result backend
    # if that is the case.
    task = celery_app.tasks.get(sender)
    backend = task.backend if task else celery_app.backend
    backend.store_result(headers['id'], None, "QUEUED")

def get_task_ids(cutoff_seconds=cfg.api_params.task_cutoff_seconds):
    now = int(time.time())
    min_score = now - cutoff_seconds
    return [task.decode('utf-8') for task in redis_client.zrangebyscore("task_ids", min_score, now)]

def get_task_status(task_id):
    # First, check if the task ID is valid and exists in the backend
    result = AsyncResult(task_id)

    # If the result is None, it means it doesn't exist
    if result.result is None and result.status == 'PENDING':
        return "UNKNOWN", None, None

    # Get progress metadata if task is in progress
    progress = None
    if result.status == 'PROGRESS':
        progress = f"{round(100 * (result.info['completed_turns'] / result.info['total_turns']))}"
    return result.status, result.result, progress

def add_task_id(task_id):
    timestamp = int(time.time())
    redis_client.zadd("task_ids", {task_id: timestamp})

def clean_old_task_ids(older_than_seconds=cfg.services_broker.task_expiration):
    now = int(time.time())
    cutoff = now - older_than_seconds
    removed = redis_client.zremrangebyscore("task_ids", 0, cutoff)
    logger.info(f"🧹 Cleaned up {removed} old task_ids")
