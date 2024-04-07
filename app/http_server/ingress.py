#!/usr/bin/env python3
import json
import threading
import os
import re
import time
import logging
from multiprocessing import Queue
from threading import Lock
import uuid
from flask import Flask, json, request, jsonify
from .confparser import createParser
from .serving import GunicornServing
from .swagger import setupSwaggerUI
from app.model import Database
from app.backends.vLLM import VLLM

logging.basicConfig(
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
)
logger = logging.getLogger("http_server")
logger.setLevel(logging.DEBUG)

# App Setup
flaskApp = Flask(__name__)
tasks = Queue()
lock = Lock()
db = Database()

# Instantiate backend threadSafe singletons for every supported backends
vLLM = VLLM()
backends = {"vLLM": vLLM}
services = []

# Loads defined services from JSON manifests and creates a flask route for each service
def handleGeneration(service_name):
    def flaskHandler():
        try:
            file = request.files.get('file')
            content = file.read().decode('utf-8') if file else ""
            flavor = request.form.get('flavor')
            # check parameters
            if not content:
                raise Exception("content")
            if not flavor:
                raise Exception("flavor")
            service = next((s for s in services if s['name'] == service_name), None)
            if service is None:
                return jsonify({"message":"Service not found"}), 404
            backendParams = next((f for f in service['flavor'] if f['name'] == flavor), None)
            if backendParams is None:
                return jsonify({"message":"Flavor not found"}), 404
            task_id = str(uuid.uuid4())
            # create task
            with lock:
                tasks.put({"backend": service['backend'], "type": service['name'], "task_id": task_id, "backendParams":backendParams, "content": content})
                logger.info(f"Task {task_id} queued")
                db.put(task_id, "Processing 0%")
            return jsonify({"message":"request successfulty queued", "jobId":task_id}), 200
        except Exception as e:
            return  jsonify({"message": "Missing request parameter: {}".format(e)}), 400
    return flaskHandler

# Single threaded fifo task queue, fed by Guicorn workers
def worker():
    while True:
        try:
            task = tasks.get()
            logger.info(f"Task {task['task_id']} processing started")
            # setup backend to process task
            # @TODO: Implement other backends
            if task["backend"] == "vLLM":
                backend = backends["vLLM"]
            backend.loadPrompt(task["type"])
            backend.setup(task["backendParams"])
            chunked_content = backend.get_splits(task["content"])
            logger.info(chunked_content)
            #@TODO: Implement final step : calling the LLM ... but nice engough for now.. it's week end and i'm on vacation... hard life of mine
            logger.info(f"Task {task['task_id']} processing END")
            if task is None:
                break
            # check task parameters
        except Exception as e:
            logger.error("An error occurred in processing tasks : " + str(e))
            break
                
# Routes
# Load services from JSON manifests
for service in os.listdir("services"):
    if service.endswith(".json"):
        try:
            with open(f"services/{service}", "r") as f:
                service_info = json.load(f)
                services.append(service_info)
                # create a flask route for each service
                flaskApp.add_url_rule(f"/services/{service_info['name']}/generate",
                                    endpoint=service_info['name'], 
                                    view_func=handleGeneration(service_info['name']), 
                                    methods=["POST"])
        except Exception as e:
            logger.error(f"Service not loaded: {e}")
            continue

@flaskApp.route("/services", methods=["GET"])
def summarization_info_route():
    return jsonify(services), 200


@flaskApp.route("/results/<resultId>", methods=["GET"])
def get_result(resultId):
    try:
        logger.info("Got get_result request: " + str(resultId))
        with lock:
            db = plyvel.DB('/tmp/testdb/', create_if_missing=True)
            result = db.get(str(resultId).encode('utf-8'))
            db.close()
            if result is None:
                return jsonify({"status":"nojob", "message":f"{resultId} does not exist"}), 404  
            elif re.match(r'^Processing \d+%', result.decode('utf-8')):
                return jsonify({"status":"processing", "message":result.decode('utf-8')}), 202
            else:
                return jsonify({"status":"complete", "message":"success", 
                                "summarization":result.decode('utf-8')}), 200
    except Exception as e:
        logger.error("An error occurred: " + str(e))
        return jsonify({"status":"error", "message":str(e)}), 400 
    

# Default routes
@flaskApp.route("/healthcheck", methods=["GET"])
def healthcheck():
    return "1", 200

# Rejected request handlers
@flaskApp.errorhandler(405)
def method_not_allowed(_):
    return "The method is not allowed for the requested URL\n", 405


@flaskApp.errorhandler(404)
def page_not_found(_):
    return "The requested URL was not found\n", 404


@flaskApp.errorhandler(500)
def server_error(error):
    logger.error(error)
    return "Server Error\n", 500


def start():
    parser = createParser()
    args = parser.parse_args()
    logger.setLevel(logging.DEBUG if args.debug else logging.INFO)
    try:
        # Setup SwaggerUI
        if args.swagger_path is not None:
            setupSwaggerUI(flaskApp, args)
            logger.debug("Swagger UI set.")
    except Exception as e:
        logger.warning("Could not setup swagger: {}".format(str(e)))

    serving = GunicornServing(
        flaskApp,
        {
            "preload_app": True,
            "bind": f"0.0.0.0:{args.service_port}",
            "workers": args.workers,
            "timeout": args.timeout,
        },
    )
    
    try:
        logger.info("Starting task queue worker thread")
        worker_thread = threading.Thread(target=worker)
        worker_thread.daemon = True
        worker_thread.start()
        serving.run()
        
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
    except Exception as e:
        logger.error(str(e))
        logger.critical("Service is shut down (Error)")
        exit(e)


if __name__ == "__main__":
    start()
    
