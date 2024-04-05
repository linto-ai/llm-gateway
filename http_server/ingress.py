#!/usr/bin/env python3


# General dependencies

import json
import os
import logging
import asyncio
from queue import Queue
from threading import Thread, Lock
from concurrent.futures import ThreadPoolExecutor

import time


from confparser import createParser
from flask import Flask, json, request, jsonify
from serving import GunicornServing
from swagger import setupSwaggerUI


service_type = os.getenv("SERVICE_TYPE")

# Dependencies for each service type
match service_type:
    case "llm_gateway":
        app = Flask("__llm_gateway__")
        from summarization import logger
        # Logic
        from summarization.utils import get_generation, get_models_dict
        MODELS = get_models_dict()
        task_lock = Lock()
        task_queue = set()
        results = {}
        lock = Lock()
        
        executor = ThreadPoolExecutor(max_workers=10)

    case _:
        from celery_app import logger

# Main logic
match service_type:
    case "llm_gateway":
        def worker(content, params, model_name):
            task_id = params['resultId']
            logger.info(f"Task {task_id} started")
            result = get_generation(content, params, MODELS[model_name])
            logger.info(f"Results for {task_id} recieved")
            try:
                with lock:
                    results[str(task_id)] = result
                with task_lock:
                    task_queue.remove(str(task_id))
                    logger.info(f"Task {task_id} finished")
            except Exception as e:
                logger.info(e)
            else:
                logger.info("Dict: " + str(results))
                

        @app.route("/ping", methods=["GET"])
        def ping_route():
            logger.info("Ping_Task_queue: " + str(task_queue))
            logger.info("Ping_Dict: " + str(results))
            return [], 200

        @app.route("/services/<model_name>/generate", methods=["POST"])
        def summarization_route(model_name: str):
            """Process a batch of articles and return the extractive summaries predicted by the
            given model. Each record in the data should have a key "text".
            """
            try:
                logger.info("Summarization request received")
                file = request.files.get('file')
                params = json.loads(request.form['format'])
                content = file.read().decode('utf-8') if file else ""
                logger.info("Processing started")
                task_id =  params['resultId']

                #Thread(target=work, args=(content, params, model_name, task_id)).start()
                # Submit the task to the thread pool
                with task_lock:
                    task_queue.add(str(task_id))
                executor.submit(worker, content, params, model_name)

                # Return the resultId to the client
                return jsonify({"message":"request successfulty queued", "jobId":params['resultId']}), 200
            except Exception as e:
                return  jsonify({"message": "Missing request parameter: {}".format(e)}), 400

        @app.route("/results/<resultId>", methods=["GET"])
        def get_result(resultId):
            """Return the result of a task, if it's ready."""
            try:
                if not str(resultId) in task_queue:
                    with lock:
                        result = results.get(str(resultId))
                        #logger.info("Dict: " + str(results))
                        logger.info("Result" + result)
                        if result is not None:
                            return jsonify({"status":"complete", "message":"success", 
                                            "summarization":str(result)}), 200
                        else:
                            return jsonify({"status":"nojob", "message":f"{resultId} does not exist"}), 404      
                else:        
                    return jsonify({"status":"processing", "message":"still processing"}), 202
            except Exception as e:
                logger.error("An error occurred: " + str(e))
                return jsonify({"status":"error", "message":str(e)}), 400 
               
        @app.route("/services", methods=["GET"])
        def summarization_info_route():
            with open('http_server/summarization_info.json', 'r') as f:
                system_info = json.load(f)
            return jsonify(system_info), 200
    case _:
        logger.error(
            "Please, provide the correct SERVICE_TYPE system variable")

# Default routes
@app.route("/healthcheck", methods=["GET"])
def healthcheck():
    return json.dumps({"healthcheck": "OK"}), 200


@app.route("/oas_docs", methods=["GET"])
def oas_docs():
    return "Not Implemented\n", 501


# Rejected request handlers
@app.errorhandler(405)
def method_not_allowed(_):
    return "The method is not allowed for the requested URL\n", 405


@app.errorhandler(404)
def page_not_found(_):
    return "The requested URL was not found\n", 404


@app.errorhandler(500)
def server_error(error):
    logger.error(error)
    return "Server Error\n", 500


if __name__ == "__main__":
    logger.info("Startup...")

    parser = createParser()
    args = parser.parse_args()
    logger.setLevel(logging.DEBUG if args.debug else logging.INFO)
    try:
        # Setup SwaggerUI
        if args.swagger_path is not None:
            setupSwaggerUI(app, args)
            logger.debug("Swagger UI set.")
    except Exception as e:
        logger.warning("Could not setup swagger: {}".format(str(e)))

    serving = GunicornServing(
        app,
        {
            "bind": f"0.0.0.0:{args.service_port}",
            "workers": args.workers,
            "timeout": args.timeout,
        },
    )
    logger.info(args)
    
    try:
        serving.run()
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
    except Exception as e:
        logger.error(str(e))
        logger.critical("Service is shut down (Error)")
        exit(e)
