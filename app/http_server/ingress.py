#!/usr/bin/env python3
import logging
import json
from fastapi import FastAPI, HTTPException, UploadFile, Form, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from . import FileChangeHandler
from watchdog.observers import Observer
from conf import cfg_instance
from app.http_server.celery_app import process_task, get_task_status
import redis
from conf import cfg_instance
from urllib.parse import urlparse

# Logging Setup
logging.basicConfig(
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
)
logger = logging.getLogger("http_server")
logger.setLevel(logging.DEBUG)

# Get configuration
cfg = cfg_instance(cfg_name="config")

# Initialize Redis client
services_broker = cfg.services_broker
broker_pass = cfg.broker_pass
parsed_url = urlparse(services_broker)
hostname = parsed_url.hostname
redis_client = redis.StrictRedis(host=hostname, password=broker_pass)

# FastAPI App Setup
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Request handler for generating summaries
def handle_generation(service_name: str):
    async def generate(file: UploadFile = None, flavor: str = Form(...), temperature: float = Form(None), top_p: float = Form(None),services: dict = Depends(get_services)):
        try:
            content = await file.read() if file else b""
            content = content.decode('utf-8') if content else ""

            if not content:
                raise HTTPException(status_code=400, detail="Missing content")
            if not flavor:
                raise HTTPException(status_code=400, detail="Missing flavor")

            service = next((s for s in services if s['name'] == service_name), None)
            if service is None:
                raise HTTPException(status_code=404, detail="Service not found")

            backend_params = next((f for f in service['flavor'] if f['name'] == flavor), None)
            if backend_params is None:
                raise HTTPException(status_code=404, detail="Flavor not found")

            # Set temperature and top_p
            if temperature is not None:
                backend_params['temperature'] = float(temperature)
            if top_p is not None and (0 < float(top_p) <= 1):
                backend_params['top_p'] = float(top_p)

            task_data = {
                "backend": service['backend'],
                "type": service['name'],
                "backendParams": backend_params,
                "fields": service['fields'],
                "content": content
            }
            result = process_task.delay(task_data)  # Schedule the task with Celery

            return JSONResponse(status_code=200, content={"message": "Request successfully queued", "jobId": result.id})
        except Exception as e:
            logger.error(f"Error in generate: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))

    return generate

# Fetch the latest `services` config on startup
@app.on_event("startup")
async def startup_event():
    # Setup file change handler for service reloading
    event_handler = FileChangeHandler('.yaml', reload_services)
    observer = Observer()
    observer.schedule(event_handler, path='../.hydra-conf/services/', recursive=False)
    observer.start()
    reload_services()

@app.get("/services")
def summarization_info_route():
    services_list = get_services()
    if not services_list:
        raise HTTPException(status_code=404, detail="No services available")
    return JSONResponse(content=services_list)


@app.get("/results/{result_id}")
async def get_result(result_id: str):
    try:
        logger.info("Got get_result request: " + str(result_id))

        # Check task status in Celery
        status, task_result = get_task_status(result_id)

        if status == "PENDING":
            return JSONResponse(status_code=202, content={"status": "queued", "message": "Task is in queue"})
        elif status == "STARTED":
            return JSONResponse(status_code=202, content={"status": "processing", "message": "Task is in progress"})
        elif status == "SUCCESS":
            # Task completed; return result from Celery or SQLite if Celery result not found
            #summary = task_result.result.get('summary', None)
            return JSONResponse(status_code=200, content={"status": "complete", "message": "success", "summarization": task_result.strip()})
        elif status == "FAILURE":
            return JSONResponse(status_code=500, content={"status": "error", "message": "Task failed", "details": str(task_result)})

        # Fall back in case status is not recognized
        raise HTTPException(status_code=404, detail="Unknown task status")
    except HTTPException as http_exc:
        logger.error(f"HTTP Exception occurred: {http_exc.detail}")
        raise
    except Exception as e:
        logger.error("An error occurred: " + str(e))
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/healthcheck")
async def healthcheck():
    return "1"


def reload_services(file_name=None):
    if file_name:
        logger.info(f"Reloading service routes: {file_name} has been modified")
    cfg = cfg_instance(cfg_name="config")
    services = cfg.reload_services(
        app=app, 
        handle_generation=handle_generation,
        base_path = '/services', 
        logger = logger
        )    
    redis_client.set("services_config", json.dumps(services))

# Retrieve services from Redis for each request
def get_services():
    services_json = redis_client.get("services_config")
    if services_json is None:
        reload_services()  # Ensures services are loaded on startup if not found
        services_json = redis_client.get("services_config")
    return json.loads(services_json)



def start():
    logger.info("Starting FastAPI application...")
    import uvicorn
    uvicorn.run("app.http_server.ingress:app", host="0.0.0.0", port=cfg.service_port, workers=cfg.workers) 

if __name__ == "__main__":
    start()