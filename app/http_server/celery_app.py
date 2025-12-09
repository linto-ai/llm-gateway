from celery import Celery
from celery.result import AsyncResult
from urllib.parse import urlparse
import logging
from celery.app import trace
from app.core.config import settings
from app.backends.llm_inference import LLMInferenceEngine
import redis
from celery.signals import after_task_publish, task_prerun, task_postrun, task_failure
import time
import asyncio
from datetime import datetime

# Edit the celery logs format
trace.LOG_SUCCESS = """\
Task %(name)s[%(id)s] succeeded in %(runtime)ss\
"""

# Logging Setup
logging.basicConfig(
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
)
logger = logging.getLogger("celery_worker")
logger.setLevel(logging.DEBUG if settings.debug else logging.INFO)

# Celery App Setup
celery_app = Celery("tasks")

# Configure the broker and backend from environment variables with defaults
parsed_url = urlparse(settings.services_broker)
broker_pass = settings.services_broker_password
broker_url = f"{parsed_url.scheme}://:{broker_pass}@{parsed_url.hostname}:{parsed_url.port}"
celery_app.conf.broker_url = f"{broker_url}/0"
celery_app.conf.result_backend = f"{broker_url}/1"

# Priority queue configuration for Redis broker
# Lower priority values are processed first (0=urgent, 5=normal, 9=background)
celery_app.conf.broker_transport_options = {
    'priority_steps': list(range(10)),  # 0-9 priority levels
    'sep': ':',
    'queue_order_strategy': 'priority',
}
celery_app.conf.task_default_priority = 5  # Normal priority by default
celery_app.conf.worker_prefetch_multiplier = 1  # Fetch one task at a time for priority ordering

redis_client = redis.Redis(host=parsed_url.hostname,port= parsed_url.port, password=broker_pass)

# Define the task
@celery_app.task(bind=True)
def process_task(self, task_data):
    logger.info(f"Starting celery task : {self.request.id}")
    self.update_state(state='STARTED')
    task_data['task_id'] = self.request.id

    # Add the task ID to the list of task IDs
    add_task_id(self.request.id)

    # Run the task with failover support
    return _run_with_failover(self, task_data, failover_depth=0)


def _run_with_failover(celery_task, task_data, failover_depth: int):
    """
    Execute task with automatic failover on specific errors.

    If the current flavor has failover configured and enabled for the error type,
    the task will automatically retry with the failover flavor while preserving
    the same job ID (for WebSocket continuity).

    Args:
        celery_task: The Celery task instance
        task_data: Task configuration including flavor settings
        failover_depth: Current depth in the failover chain (prevents infinite loops)
    """

    # Get failover config from task_data
    failover_config = task_data.get("failoverConfig", {})
    max_depth = failover_config.get("max_failover_depth", 3)

    try:
        # Initialize backend
        engine = LLMInferenceEngine(task_data=task_data, celery_task=celery_task)

        # Run summarization - returns dict with 'output' and 'token_metrics'
        result = engine.run()

        # Add failover tracking info to result
        if failover_depth > 0:
            result['failover_applied'] = True
            result['failover_depth'] = failover_depth
            result['final_flavor_id'] = task_data.get('flavor_id')

        return result

    except Exception as e:
        # Convert OpenAI/generic errors to FailoverableError types
        failoverable_error = _classify_error(e)

        if failoverable_error is None:
            # Not a failoverable error - propagate original
            logger.error(f"Non-failoverable error in task: {str(e)}")
            raise

        # Check if failover is enabled and configured for this error type
        if not _should_failover(failover_config, failoverable_error, failover_depth, max_depth):
            logger.error(f"Failoverable error but no failover available: {str(e)}")
            raise failoverable_error from e

        # Attempt failover
        failover_flavor_id = failover_config.get("failover_flavor_id")
        logger.warning(
            f"Failover triggered: {failoverable_error.failover_reason} at depth {failover_depth}. "
            f"Switching to flavor {failover_flavor_id}"
        )

        # Update Celery state to indicate failover
        celery_task.update_state(
            state='PROGRESS',
            meta={
                'phase': 'failover',
                'failover_reason': failoverable_error.failover_reason,
                'failover_depth': failover_depth + 1,
                'error_message': str(e)[:200],
            }
        )

        # Get new task_data for the failover flavor
        new_task_data = _get_failover_task_data(task_data, failover_flavor_id)
        if new_task_data is None:
            logger.error(f"Failed to get task data for failover flavor {failover_flavor_id}")
            raise failoverable_error from e

        # Recursively run with failover flavor
        return _run_with_failover(celery_task, new_task_data, failover_depth + 1)


def _classify_error(e: Exception):
    """
    Convert generic exceptions to FailoverableError types.

    Returns None if the error is not failoverable.
    """
    from app.core.exceptions import (
        FailoverableError, TimeoutFailoverError, RateLimitFailoverError,
        ModelFailoverError, ContentFilterFailoverError
    )
    from openai import RateLimitError, APITimeoutError, APIError, BadRequestError

    # Already a FailoverableError
    if isinstance(e, FailoverableError):
        return e

    # BadRequestError is NOT failoverable (bad input, won't work with other flavors either)
    if isinstance(e, BadRequestError):
        return None

    # OpenAI-specific errors
    if isinstance(e, APITimeoutError):
        return TimeoutFailoverError(str(e), original_error=e)

    if isinstance(e, RateLimitError):
        return RateLimitFailoverError(str(e), original_error=e)

    if isinstance(e, APIError):
        # Check for content filter
        error_str = str(e).lower()
        if 'content_filter' in error_str or 'content filter' in error_str or 'policy' in error_str:
            return ContentFilterFailoverError(str(e), original_error=e)
        # Other API errors (503, 500, etc.) are model errors
        return ModelFailoverError(str(e), original_error=e)

    # Generic timeout errors
    error_str = str(e).lower()
    if 'timeout' in error_str:
        return TimeoutFailoverError(str(e), original_error=e)
    if 'rate limit' in error_str or 'ratelimit' in error_str:
        return RateLimitFailoverError(str(e), original_error=e)

    # Not a recognized failoverable error
    return None


def _should_failover(failover_config: dict, error, failover_depth: int, max_depth: int) -> bool:
    """
    Check if failover should be attempted for this error.
    """
    from app.core.exceptions import (
        TimeoutFailoverError, RateLimitFailoverError,
        ModelFailoverError, ContentFilterFailoverError
    )

    # Check depth limit
    if failover_depth >= max_depth:
        logger.warning(f"Max failover depth {max_depth} reached, not retrying")
        return False

    # Check if failover is enabled
    if not failover_config.get("failover_enabled", False):
        return False

    # Check if failover flavor is configured
    if not failover_config.get("failover_flavor_id"):
        return False

    # Check if this error type triggers failover
    if isinstance(error, TimeoutFailoverError):
        return failover_config.get("failover_on_timeout", True)
    if isinstance(error, RateLimitFailoverError):
        return failover_config.get("failover_on_rate_limit", True)
    if isinstance(error, ModelFailoverError):
        return failover_config.get("failover_on_model_error", True)
    if isinstance(error, ContentFilterFailoverError):
        return failover_config.get("failover_on_content_filter", False)

    return False


def _get_failover_task_data(original_task_data: dict, failover_flavor_id: str) -> dict:
    """
    Build new task_data for the failover flavor.

    This retrieves the failover flavor from the database and rebuilds
    the task_data with the new flavor's configuration while preserving
    the original content and context.
    """
    try:
        session = _get_sync_db_session()
        try:
            from app.models.service_flavor import ServiceFlavor
            from sqlalchemy.orm import joinedload
            from uuid import UUID

            # Get the failover flavor with relationships
            flavor = session.query(ServiceFlavor).options(
                joinedload(ServiceFlavor.model),
                joinedload(ServiceFlavor.provider)
            ).filter(ServiceFlavor.id == UUID(failover_flavor_id)).first()

            if not flavor:
                logger.error(f"Failover flavor {failover_flavor_id} not found")
                return None

            if not flavor.is_active:
                logger.error(f"Failover flavor {failover_flavor_id} is inactive")
                return None

            # Build new task_data preserving content but using new flavor config
            new_task_data = original_task_data.copy()
            new_task_data['flavor_id'] = str(flavor.id)

            # Update backend params
            new_task_data['backendParams'] = {
                **original_task_data.get('backendParams', {}),
                'modelName': flavor.model.model_name if flavor.model else original_task_data['backendParams'].get('modelName'),
                'temperature': flavor.temperature,
                'top_p': flavor.top_p,
                'maxGenerationLength': flavor.model.max_output_tokens if flavor.model else original_task_data['backendParams'].get('maxGenerationLength'),
                'totalContextLength': flavor.model.max_context_length if flavor.model else original_task_data['backendParams'].get('totalContextLength'),
                'processing_mode': flavor.processing_mode,
                'estimated_cost_per_1k_tokens': flavor.estimated_cost_per_1k_tokens,
            }

            # Update provider config if the failover flavor has a different provider
            if flavor.provider:
                new_task_data['providerConfig'] = {
                    'api_key': flavor.provider.api_key,
                    'api_url': flavor.provider.api_url,
                    'provider_type': flavor.provider.provider_type,
                }

            # Update prompts if the failover flavor has its own
            if flavor.prompt_system_content:
                new_task_data['prompt_system_content'] = flavor.prompt_system_content
            if flavor.prompt_user_content:
                new_task_data['prompt_user_content'] = flavor.prompt_user_content
            if flavor.prompt_reduce_content:
                new_task_data['prompt_reduce_content'] = flavor.prompt_reduce_content

            # Update failover config for potential deeper failover
            new_task_data['failoverConfig'] = {
                'failover_enabled': flavor.failover_enabled,
                'failover_flavor_id': str(flavor.failover_flavor_id) if flavor.failover_flavor_id else None,
                'failover_on_timeout': flavor.failover_on_timeout,
                'failover_on_rate_limit': flavor.failover_on_rate_limit,
                'failover_on_model_error': flavor.failover_on_model_error,
                'failover_on_content_filter': flavor.failover_on_content_filter,
                'max_failover_depth': flavor.max_failover_depth,
            }

            logger.info(f"Built failover task_data for flavor {flavor.name} (id={failover_flavor_id})")
            return new_task_data

        finally:
            session.close()

    except Exception as e:
        logger.error(f"Error building failover task_data: {e}")
        return None

# Set publish tasked status to QUEUED
@after_task_publish.connect
def update_sent_state(sender=None, headers=None, **kwargs):
    # the task may not exist if sent using `send_task` which
    # sends tasks by name, so fall back to the default result backend
    # if that is the case.
    task = celery_app.tasks.get(sender)
    backend = task.backend if task else celery_app.backend
    backend.store_result(headers['id'], None, "QUEUED")

def get_task_ids(cutoff_seconds=settings.task_cutoff_seconds):
    now = int(time.time())
    min_score = now - cutoff_seconds
    return [task.decode('utf-8') for task in redis_client.zrangebyscore("task_ids", min_score, now)]

def get_task_status(task_id):
    """Get task status from Celery/Redis (synchronous - use get_task_status_async for async contexts)."""
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


async def get_task_status_async(task_id):
    """Async wrapper for get_task_status - runs in thread pool to avoid blocking event loop."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, get_task_status, task_id)

def add_task_id(task_id):
    timestamp = int(time.time())
    redis_client.zadd("task_ids", {task_id: timestamp})

def clean_old_task_ids(older_than_seconds=settings.task_expiration):
    now = int(time.time())
    cutoff = now - older_than_seconds
    removed = redis_client.zremrangebyscore("task_ids", 0, cutoff)
    logger.info(f"Cleaned up {removed} old task_ids")


# Database session helper for Celery signals (runs in worker process)
def _get_sync_db_session():
    """Create a synchronous database session for Celery worker context."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    # Convert async URL to sync URL
    db_url = str(settings.database_url)
    if "asyncpg" in db_url:
        db_url = db_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
    elif db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://")

    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    return Session()


def _update_job_status_sync(celery_task_id: str, status: str, result=None, error=None, progress=None):
    """Synchronously update job status in PostgreSQL (for Celery signals)."""
    try:
        session = _get_sync_db_session()
        try:
            from app.models.job import Job

            job = session.query(Job).filter(Job.celery_task_id == celery_task_id).first()
            if job:
                job.status = status

                if status == "started" and not job.started_at:
                    job.started_at = datetime.utcnow()

                if status in ("completed", "failed") and not job.completed_at:
                    job.completed_at = datetime.utcnow()

                if result is not None:
                    job.result = result

                if error is not None:
                    job.error = error

                # Persist progress data (includes token_metrics)
                if progress is not None:
                    job.progress = progress

                session.commit()
                logger.info(f"Updated job status: celery_task_id={celery_task_id}, status={status}")
            else:
                logger.warning(f"Job not found for celery_task_id={celery_task_id}")
        finally:
            session.close()
    except Exception as e:
        logger.error(f"Failed to update job status: {e}")


# Celery signal handlers for job status synchronization
@task_prerun.connect
def task_started_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **other_kwargs):
    """Called before a task is executed - update job status to 'started'."""
    if sender and sender.name == 'app.http_server.celery_app.process_task':
        logger.info(f"Task {task_id} starting execution")
        _update_job_status_sync(task_id, "started")


@task_postrun.connect
def task_completed_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **other_kwargs):
    """Called after a task completes successfully - update job status to 'completed'."""
    if sender and sender.name == 'app.http_server.celery_app.process_task':
        if state == "SUCCESS":
            logger.info(f"Task {task_id} completed successfully")

            # Extract token_metrics, extracted_metadata, and categorization from return value
            # All data is now consolidated into result_data JSONB
            progress_data = None
            result_data = None

            if isinstance(retval, dict):
                # New format: dict with output, token_metrics, and optional extracted_metadata/categorization
                result_data = {"output": retval.get("output", "")}
                token_metrics = retval.get("token_metrics")
                if token_metrics:
                    progress_data = {"token_metrics": token_metrics}
                    passes_count = len(token_metrics.get("passes", []))
                    logger.info(f"Task {task_id} has token_metrics with {passes_count} passes")

                # Include extracted_metadata in result_data (consolidated into result JSONB)
                extracted_metadata = retval.get("extracted_metadata")
                if extracted_metadata:
                    result_data["extracted_metadata"] = extracted_metadata
                    logger.info(f"Task {task_id} has extracted_metadata with {len(extracted_metadata)} fields")

                # Include categorization in result_data
                categorization = retval.get("categorization")
                if categorization:
                    result_data["categorization"] = categorization
                    matched_count = len(categorization.get("matched_tags", []))
                    suggested_count = len(categorization.get("suggested_tags", []))
                    logger.info(f"Task {task_id} has categorization: {matched_count} matched, {suggested_count} suggested tags")
            else:
                # Simple format: string output (wrapped in dict for consistency)
                result_data = {"output": retval} if isinstance(retval, str) else retval

            _update_job_status_sync(task_id, "completed", result=result_data, progress=progress_data)


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, args=None, kwargs=None, traceback=None, einfo=None, **other_kwargs):
    """Called when a task fails - update job status to 'failed' with error message."""
    if sender and sender.name == 'app.http_server.celery_app.process_task':
        # Extract meaningful error message
        error_message = _extract_error_message(exception)
        logger.error(f"Task {task_id} failed: {error_message}")
        _update_job_status_sync(task_id, "failed", error=error_message)


def _extract_error_message(exception) -> str:
    """Extract a meaningful error message from an exception."""
    if exception is None:
        return "Unknown error"

    error_str = str(exception)

    # Try to extract more meaningful error from OpenAI/API errors
    if hasattr(exception, 'response'):
        try:
            response = exception.response
            if hasattr(response, 'json'):
                error_data = response.json()
                if 'error' in error_data:
                    error_obj = error_data['error']
                    if isinstance(error_obj, dict):
                        return error_obj.get('message', error_str)
                    return str(error_obj)
        except Exception:
            pass

    # Try to get message from common exception attributes
    if hasattr(exception, 'message'):
        return exception.message

    # For OpenAI BadRequestError and similar
    if hasattr(exception, 'body') and exception.body:
        try:
            if isinstance(exception.body, dict):
                if 'error' in exception.body:
                    error_obj = exception.body['error']
                    if isinstance(error_obj, dict):
                        return error_obj.get('message', error_str)
                return exception.body.get('message', error_str)
        except Exception:
            pass

    # Clean up common error type prefixes for readability
    error_str = error_str.replace("BadRequestError: ", "").replace("APIError: ", "")

    return error_str if error_str else "Task execution failed"
