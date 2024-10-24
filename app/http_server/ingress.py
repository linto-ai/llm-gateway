#!/usr/bin/env python3
import json
import threading
import os
import signal
import re
import logging
from multiprocessing import Queue, Manager
from threading import Lock
import uuid
from flask import Flask, json, request, jsonify
from ..confparser import createParser
from .serving import GunicornServing
from .swagger import setupSwaggerUI
from app.model import Database
from . import FileChangeHandler
from watchdog.observers import Observer
from conf import cfg_instance

cfg = cfg_instance(cfg_name="config")

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
parser = createParser()
args = parser.parse_args()
db = Database(args.db_path)
# uses db and lock from ingress.py
from app.backends.vLLM import VLLM

# Instantiate backend threadSafe singletons for every supported backends inside guicorn workers
vLLM = VLLM(api_key=args.api_key, api_base=args.api_base)
backends = {"vLLM": vLLM}
# Loads defined services from JSON manifests and creates a flask route for each service
def handleGeneration(service_name):
    def flaskHandler():
        try:
            file = request.files.get('file')
            content = file.read().decode('utf-8') if file else ""
            flavor = request.form.get('flavor')
            temperature = request.form.get('temperature')
            top_p = request.form.get('top_p')
            # check parameters
            if not content:
                raise Exception("content")
            if not flavor:
                raise Exception("flavor")
            service = next((s for s in services if s['name'] == service_name), None)
            if service is None:
                return jsonify({"message":"Service not found"}), 404
            backendParams = next((f for f in service['flavor'] if f['name'] == flavor), None)
            # default temperature and top_p in flavor
            if temperature:
                backendParams['temperature'] = float(temperature)
            if top_p:
                # must be between 0 and 1 or failsback to default
                if 0 < float(top_p) <= 1:
                    backendParams['top_p'] = float(top_p)
            if backendParams is None:
                return jsonify({"message":"Flavor not found"}), 404
            task_id = str(uuid.uuid4())
            # create task
            with lock:
                tasks.put({"backend": service['backend'], "type": service['name'], "task_id": task_id, "backendParams":backendParams, "fields":service['fields'], "content": content})
                logger.info(f"Task {task_id} queued")
            db.put(task_id, "Processing 0%")
            return jsonify({"message":"request successfulty queued", "jobId":task_id}), 200
        except Exception as e:
            return  jsonify({"message": "Missing request parameter: {}".format(e)}), 400
    return flaskHandler
                
# Routes

@flaskApp.route("/services", methods=["GET"])
def summarization_info_route():
    services_list = list(services)
    return jsonify(services_list), 200


@flaskApp.route("/results/<resultId>", methods=["GET"])
def get_result(resultId):
    try:
        logger.info("Got get_result request: " + str(resultId))
        result = db.get(resultId)
        if result is None:
            return jsonify({"status":"nojob", "message":f"{resultId} does not exist"}), 404  
        else:
            match = re.match(r'^Processing ([0-9]*\.[0-9]*)%$', result)
            if match:
                processing_percentage = float(match.group(1))
                if processing_percentage == 0:
                    return jsonify({"status":"queued", "message":result}), 202
                else:
                    return jsonify({"status":"processing", "message":processing_percentage}), 202
            elif result == "Processing 0%":
                return jsonify({"status":"queued", "message":result}), 202
            else:
                return jsonify({"status":"complete", "message":"success", 
                                "summarization":result.strip()}), 200
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


# Single threaded fifo task queue, fed by Guicorn workers
def worker():
    logger.info("Starting task queue worker thread")
    while True:
        try:
            task = tasks.get()
            logger.info(f"Task {task['task_id']} processing started")
            # setup backend to process task
            # @TODO: Implement other backends
            if task["backend"] == "vLLM":
                backend = backends["vLLM"]
            backend.loadPrompt(task["type"], task["fields"])
            backend.setup(task["backendParams"], task["task_id"])
            chunked_content = backend.get_splits(task["content"])
            summary = backend.get_generation(chunked_content)
            #@TODO Might compare those
            chunked_content_string = "\n".join(chunked_content)
            summary_string = "\n".join(summary)
            db.put(task["task_id"], summary_string)
            logger.info(f"Task {task['task_id']} processing END")
            if task is None:
                break
            # check task parameters
        except Exception as e:
            logger.error("An error occurred in processing tasks : " + str(e))
            break

def reload_services(fileName=None):
    services[:] = []
    if fileName is None:
        logger.info("Loading service manifests")
    else:
        logger.info(f"Reloading service routes: {fileName} has been modified")
    
    # Clear all services routes
    for rule in list(flaskApp.url_map.iter_rules()):
        if str(rule).startswith('/services/'):
            flaskApp.url_map._rules.remove(rule)
            flaskApp.view_functions.pop(rule.endpoint, None)

    # Iterate over each service in the Hydra config
    for service_name, service_info in cfg.services.items():
        try:
            # Add service info to the services list
            services.append(service_info)

            # Register the service with Flask
            flaskApp.add_url_rule(
                f"/services/{service_info['name']}/generate",
                endpoint=service_info['name'],
                view_func=handleGeneration(service_info['name']), 
                methods=["POST"]
            )

            logger.info(f"Service '{service_info['name']}' loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load service '{service_name}': {e}")
        

def start():
    logger.setLevel(logging.DEBUG if args.debug else logging.INFO)
    try:
        # Setup SwaggerUI
        if args.swagger_path is not None:
            setupSwaggerUI(flaskApp, args)
            logger.debug("Swagger UI set.")
    except Exception as e:
        logger.warning("Could not setup swagger: {}".format(str(e)))


    logger.info(args)
    serving = GunicornServing(
        flaskApp,
        {
            "preload_app": True,
            "bind": f"0.0.0.0:{args.service_port}",
            "workers": args.workers,
            "timeout": args.timeout
        },
    )
    
    try:
        global manager, services
        # Services list in shared memory
        manager = Manager()
        services = manager.list()
        event_handler = FileChangeHandler('.json', reload_services)
        observer = Observer()
        observer.schedule(event_handler, path='../services', recursive=False)
        observer.start()
        reload_services()
        # Queue startup
        worker_thread = threading.Thread(target=worker)
        # Daemonize worker thread to allow for clean shutdown with SIGINT
        worker_thread.daemon = True
        worker_thread.start()
        # Start serving, blocking app here
        serving.run()
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        # observer.stop()
    except Exception as e:
        logger.error(str(e))
        logger.critical("Service is shut down (Error)")
        exit(e)

if __name__ == "__main__":
    start()