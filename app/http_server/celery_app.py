from celery import Celery
from celery.result import AsyncResult
import os
from urllib.parse import urlparse
import logging
from asgiref.sync import async_to_sync
from celery.app import trace
from conf import cfg_instance
from app.backends.llm_inference import LLMInferenceEngine

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

# Define the task
@celery_app.task(bind=True)
def process_task(self, task_data):
    logger.info(f"Starting celery task : {self.request.id}")
    self.update_state(state='STARTED')
    task_data['task_id'] = self.request.id
    try:
        # Initialize backend
        engine = LLMInferenceEngine(task_data=task_data, celery_task=self)

        # Run summarization
        summary = engine.run()
        
        return summary
    
    except Exception as e:
        logger.error(f"An error occurred in processing tasks : {str(e)}")
    

def get_task_status(task_id):
    # First, check if the task ID is valid and exists in the backend
    result = AsyncResult(task_id)

    # If the result is None, it means it doesn't exist
    if result.result is None and result.status == 'PENDING':
        # Check if the task ID is known to any worker
        i = celery_app.control.inspect()
        active_tasks = i.active()  # Gets the active tasks
        
        # Flatten the list of active task IDs
        active_task_ids = [task['id'] for worker_tasks in active_tasks.values() for task in worker_tasks]
        
        if task_id not in active_task_ids:
            # If the task_id is not found in active tasks, it likely doesn't exist
        
            return "UNKNOWN", None
        
    # Get progress metadata if task is in progress
    progress = None
    if result.status == 'PROGRESS':
        progress = f"{round(100 * (result.info['completed_turns'] / result.info['total_turns']))} %"    
    return result.status, result.result, progress