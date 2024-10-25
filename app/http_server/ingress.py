#!/usr/bin/env python3
import json
import os
import re
import logging
import uuid
import threading

from fastapi import FastAPI, HTTPException, UploadFile, Form, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from multiprocessing import  Manager
from threading import Lock
from app.model import Database
from ..confparser import createParser
from . import FileChangeHandler
from watchdog.observers import Observer
from conf import cfg_instance
from omegaconf import OmegaConf
from asyncio import Queue
import asyncio

# Configuration
cfg = cfg_instance(cfg_name="config")
parser = createParser()
args = parser.parse_args()

# Logging Setup
logging.basicConfig(
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
)
logger = logging.getLogger("http_server")
logger.setLevel(logging.DEBUG)

# FastAPI App Setup
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
tasks = Queue()
lock = Lock()
db = Database(args.db_path)

from app.backends.vLLM import VLLM

# Backends
vLLM = VLLM(api_key=args.api_key, api_base=args.api_base)
backends = {"vLLM": vLLM}



def handle_generation(service_name: str):
    async def generate(file: UploadFile = None, flavor: str = Form(...), temperature: float = Form(None), top_p: float = Form(None)):
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

            task_id = str(uuid.uuid4())
            with lock:
                await tasks.put({"backend": service['backend'], "type": service['name'], "task_id": task_id, "backendParams": backend_params, "fields": service['fields'], "content": content})
                logger.info(f"Task {task_id} queued")
            db.put(task_id, "Processing 0%")

            return JSONResponse(status_code=200, content={"message": "Request successfully queued", "jobId": task_id})
        except Exception as e:
            logger.error(f"Error in generate: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))

    return generate

# Fetch the latest `services` config on startup
@app.on_event("startup")
async def startup_event():
    global services, manager
    manager = Manager()
    services = manager.list()

    # Setup file change handler for service reloading
    event_handler = FileChangeHandler('.yaml', reload_services)
    observer = Observer()
    observer.schedule(event_handler, path='../.hydra-conf/services/', recursive=False)
    observer.start()
    reload_services()
    
    # Start worker thread
    asyncio.create_task(worker()) 


@app.get("/results/{result_id}")
async def get_result(result_id: str):
    try:
        logger.info("Got get_result request: " + str(result_id))
        result = db.get(result_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"{result_id} does not exist")

        match = re.match(r'^Processing ([0-9]*\.[0-9]*)%$', result)
        if match:
            processing_percentage = float(match.group(1))
            if processing_percentage == 0:
                return JSONResponse(status_code=202, content={"status": "queued", "message": result})
            else:
                return JSONResponse(status_code=202, content={"status": "processing", "message": processing_percentage})
        elif result == "Processing 0%":
            return JSONResponse(status_code=202, content={"status": "queued", "message": result})
        else:
            return JSONResponse(status_code=200, content={"status": "complete", "message": "success", "summarization": result.strip()})
    except Exception as e:
        logger.error("An error occurred: " + str(e))
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/healthcheck")
async def healthcheck():
    return "1"

# Worker function for processing tasks
async def worker():
    logger.info("Starting task queue worker thread")
    while True:
        try:
            task = await tasks.get()
            if task is None:
                break
            logger.info(f"Task {task['task_id']} processing started")

            if task["backend"] == "vLLM":
                backend = backends["vLLM"]

            backend.loadPrompt(task["type"], task["fields"])
            backend.setup(task["backendParams"], task["task_id"])
            chunked_content = backend.get_splits(task["content"])
            summary = await backend.get_generation(chunked_content)
            summary_string = "\n".join(summary)
            db.put(task["task_id"], summary_string)
            logger.info(f"Task {task['task_id']} processing END")
        except Exception as e:
            logger.error("An error occurred in processing tasks : " + str(e))

def reload_services(file_name=None):
    global services
    cfg = cfg_instance(cfg_name="config")
    services[:] = []
    if file_name:
        logger.info(f"Reloading service routes: {file_name} has been modified")
    services = cfg.reload_services(
        app=app, 
        services=services, 
        handle_generation=handle_generation,
        base_path = '/services', 
        logger = logger
        )


def start():
    import uvicorn
    uvicorn.run("app.http_server.ingress:app", host="0.0.0.0", port=args.service_port, workers=args.workers) 

if __name__ == "__main__":
    start()