#!/usr/bin/env python3
import logging
import json
from fastapi import FastAPI, HTTPException, UploadFile, Form, Depends
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from . import FileChangeHandler
from watchdog.observers import Observer
from conf import cfg_instance
from app.http_server.celery_app import process_task, get_task_status
import redis
from conf import cfg_instance
from urllib.parse import urlparse
import asyncio

# Get configuration
cfg = cfg_instance(cfg_name="config")

# Logging Setup
logging.basicConfig(
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
)
logger = logging.getLogger("http_server")
logger.setLevel(logging.DEBUG if cfg.debug else logging.INFO)



# Initialize Redis client
services_broker = cfg.services_broker.url
broker_pass = cfg.services_broker.password
parsed_url = urlparse(services_broker)
redis_client = redis.Redis(host=parsed_url.hostname,port= parsed_url.port, password=broker_pass)

# FastAPI App Setup
app = FastAPI(
    title=cfg.swagger.title,
    description=cfg.swagger.description,
    docs_url=cfg.swagger.url
)
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
        status, task_result, progress = get_task_status(result_id)

        if status == "PENDING":
            return JSONResponse(status_code=202, content={"status": "queued", "message": "Task is in queue"})
        elif status == "STARTED":
            return JSONResponse(status_code=202, content={"status": "started", "message": "Task started"})
        elif status == "PROGRESS":
            return JSONResponse(status_code=202, content={"status": "processing", "message": "Task is in progress", "progress": progress})
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

# 
@app.websocket("/ws/results/{result_id}")
async def websocket_result(websocket: WebSocket, result_id: str):
    await websocket.accept()
    try:
        # Check initial task status
        status, task_result, progress = get_task_status(result_id)
        
        # Send initial status
        if status == "PENDING":
            await websocket.send_json({"status": "queued", "message": "Task is in queue"})
        elif status == "STARTED":
            await websocket.send_json({"status": "started", "message": "Task started"})
        elif status == "PROGRESS":
            await websocket.send_json({"status": "processing", "message": "Task is in progress", "progress": progress})
        elif status == "SUCCESS":
            # Task completed
            await websocket.send_json({"status": "complete", "message": "success", "summarization": task_result.strip()})
        elif status == "FAILURE":
            await websocket.send_json({"status": "error", "message": "Task failed", "details": str(task_result)})

        # Keep checking the status at intervals if task is not yet complete
        while status not in ["SUCCESS", "FAILURE"]:
            print(f"Get task ids: {get_task_ids()}")
            await asyncio.sleep(cfg.api_params.ws_polling_interval)  # Polling interval
            status, task_result, progress = get_task_status(result_id)
            if status == "PENDING":
                await websocket.send_json({"status": "queued", "message": "Task is in queue"})
            elif status == "STARTED":
                await websocket.send_json({"status": "started", "message": "Task started"})
            elif status == "PROGRESS":
                await websocket.send_json({"status": "processing", "message": "Task is in progress", "progress": progress})
            elif status == "SUCCESS":
                await websocket.send_json({"status": "complete", "message": "success", "summarization": task_result.strip()})
            elif status == "FAILURE":
                await websocket.send_json({"status": "error", "message": "Task failed", "details": str(task_result)})

    except WebSocketDisconnect:
        logger.info(f"Client disconnected from WebSocket for result_id: {result_id}")

from fastapi import WebSocket, WebSocketDisconnect
import asyncio

@app.websocket("/ws/results")
async def websocket_all_results(websocket: WebSocket):
    await websocket.accept()
    try:
        
        # Wait for the client to send a list of task IDs
        initial_task_ids = list(await websocket.receive_json())
        #initial_task_ids = message.get('task_ids', [])

        # Send the initial status of all tasks
        initial_response = []
        task_status = {}
        task_progress = {}

        for task_id in initial_task_ids:
            status, result, progress = get_task_status(task_id)
            # Update the status if it has changed
            if status == "SUCCESS":
                initial_response.append({"task_id": task_id, "status": "complete","message": "success","progress":"100", "summarization": result.strip()})
            elif status == "FAILURE":
                initial_response.append({"task_id": task_id, "status": "error", "message": "Task failed", "details": str(result)})
            elif status == "STARTED":
                initial_response.append({"task_id": task_id, "status": "started","message": "Task started"})
            elif status == "PROGRESS":
                initial_response.append({"task_id": task_id, "status": "processing", "message": "Task is in progress", "progress": progress,})
            elif status == "PENDING":
                initial_response.append({"task_id": task_id, "status": "queued","message": "Task is in queue"})
            elif status == "UNKNOWN":
                initial_response.append({"task_id": task_id, "status": "unknown", "message": "Task does not exist"})
            
            # Update the task status in the dictionary
            task_status[task_id] = status
            task_progress[task_id] = progress
        
        await websocket.send_json(initial_response)

        first_connection = True
        while True:
            # Get all task IDs
            task_ids = get_task_ids()
            for task_id in task_ids:
                status, result, progress = get_task_status(task_id)

                if first_connection and status in ["SUCCESS", "FAILURE", "UNKNOWN"]:
                    task_status[task_id] = status
                    task_progress[task_id] = progress
                    continue
                # Update the status if it has changed
                if (task_status.get(task_id) != status) or (task_progress.get(task_id) != progress):
                    if status == "SUCCESS":
                        await websocket.send_json({"task_id": task_id, "status": "complete","message": "success","progress":"100", "summarization": result.strip()})
                    elif status == "FAILURE":
                        await websocket.send_json({"task_id": task_id, "status": "error", "message": "Task failed", "details": str(result)})
                    elif status == "STARTED":
                        await websocket.send_json({"task_id": task_id, "status": "started","message": "Task started"})
                    elif status == "PROGRESS":
                        await websocket.send_json({"task_id": task_id, "status": "processing", "message": "Task is in progress", "progress": progress,})
                    elif status == "PENDING":
                        await websocket.send_json({"task_id": task_id, "status": "queued","message": "Task is in queue"})
                    elif status == "UNKNOWN":
                        await websocket.send_json({"task_id": task_id, "status": "unknown", "message": "Task does not exist"})

                    # Update the task status in the dictionary
                    task_status[task_id] = status
                    task_progress[task_id] = progress
            
            first_connection = False
            
            # Sleep for the polling interval
            await asyncio.sleep(cfg.api_params.ws_polling_interval)

    except WebSocketDisconnect:
        logger.info("Client disconnected from WebSocket")


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

def get_task_ids():
    task_ids = redis_client.lrange('task_ids', 0, -1) or []
    return [task.decode('utf-8') for task in task_ids]


def start():
    logger.info("Starting FastAPI application...")
    import uvicorn
    uvicorn.run("app.http_server.ingress:app", host="0.0.0.0", port=cfg.api_params.service_port, workers=cfg.api_params.workers) 

if __name__ == "__main__":
    start()