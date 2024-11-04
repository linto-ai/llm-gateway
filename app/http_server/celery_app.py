from celery import Celery
from celery.result import AsyncResult
import os
import logging
from asgiref.sync import async_to_sync
from celery.app import trace
from conf import cfg_instance
from app.backends.vLLM import VLLM

trace.LOG_SUCCESS = """\
Task %(name)s[%(id)s] succeeded in %(runtime)ss\
"""
# Get configuration
cfg = cfg_instance(cfg_name="config")
# Backends
vLLM = VLLM(api_key=cfg.api_key, api_base=cfg.api_base)
backends = {"vLLM": vLLM}


# Logging Setup
logging.basicConfig(
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
)
logger = logging.getLogger("celery_worker")
logger.setLevel(logging.DEBUG)



celery_app = Celery("tasks")

# Configure the broker and backend from environment variables with defaults
celery_app.conf.broker_url = cfg.services_broker
celery_app.conf.result_backend = cfg.services_broker

async def worker(task, task_id):
    logger.info("Starting celery worker")

    try:
        backend = backends[task["backend"]]
        backend.loadPrompt(task["type"], task["fields"])
        backend.setup(task["backendParams"], task_id)
        chunked_content = backend.get_splits(task["content"])
        summary = await backend.get_generation(chunked_content)
        summary_string = "\n".join(summary)
    except Exception as e:
        logger.error(f"An error occurred in processing tasks : {str(e)}")
    return summary_string
# Worker function for processing tasks
@celery_app.task(bind=True)
def process_task(self, task):
    task_id = self.request.id
    result = async_to_sync(worker)(task, task_id)
    return result

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
            
    return result.status, result.result