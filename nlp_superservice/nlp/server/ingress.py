#!/usr/bin/env python3

import hashlib
import logging
import os

from celery.result import AsyncResult
from celery.result import states as task_states
from celery import current_app
from celery.signals import after_task_publish

from flask import Flask, json, request

from nlp import logger
from nlp.broker.discovery import list_available_services
from nlp.processing.maintask import nlp_task
from nlp.server.confparser import createParser
from nlp.server.mongodb.db_client import DBClient
from nlp.server.serving import GunicornServing
from nlp.server.swagger import setupSwaggerUI
from nlp.processing.configs.mainconfig import NLPConfig

SUPPORTED_HEADER_FORMAT = ["text/plain", "application/json", "text/vtt", "text/srt", 'multipart/form-data'] 

app = Flask("__services_manager__")
app.config["JSON_AS_ASCII"] = False
app.config["JSON_SORT_KEYS"] = False


@app.route("/healthcheck", methods=["GET"])
def healthcheck():
    """Server healthcheck"""
    return "1", 200


@app.route("/list-services", methods=["GET"])
def list_subservices():
    return list_available_services(as_json=True, ensure_alive=True), 200


@app.route("/job/<jobid>", methods=["GET"])
def jobstatus(jobid):
    try:
        task = AsyncResult(jobid)
    except Exception as error:
        return ({"state": "failed", "reason": error.message}, 500)
    state = task.status

    if state == "SENT": # See below
        return json.dumps({"state": "pending"}), 202
    elif state == task_states.STARTED:
        return (
            json.dumps({"state": "started", "steps": task.info.get("steps", {})}),
            202,
        )
    elif state == task_states.SUCCESS:
        result_id = task.get()
        return json.dumps({"state": "done", "result_id": result_id}), 201
    elif state == task_states.PENDING:
        return json.dumps({"state": "failed", "reason": f"Unknown jobid {jobid}"}), 404
    elif state == task_states.FAILURE:
        return json.dumps({"state": "failed", "reason": str(task.result)}), 500
    else:
        return "Task returned an unknown state", 400


# This is to distinguish between a pending state meaning that the task is unknown,
# and a pending state meaning that the task is waiting for a worker to start.
# see https://stackoverflow.com/questions/9824172/find-out-whether-celery-task-exists
@after_task_publish.connect
def update_sent_state(sender=None, headers=None, **kwargs):
    # the task may not exist if sent using `send_task` which
    # sends tasks by name, so fall back to the default result backend
    # if that is the case.
    task = current_app.tasks.get(sender)
    backend = task.backend if task else current_app.backend
    backend.store_result(headers['id'], None, "SENT")


@app.route("/results/<result_id>", methods=["GET"])
def results(result_id):
    # Expected format
    expected_format = request.headers.get("accept")
    if not expected_format in SUPPORTED_HEADER_FORMAT:
        return (
            "Accept format {} not supported. Supported MIME types are :{}".format(
                expected_format, " ".join(SUPPORTED_HEADER_FORMAT)
            ),
            400,
        )

    # Result
    result = db_client.fetch_result(result_id)
    if result is None:
        return f"No result associated with id {result_id}", 404
    logger.debug(f"Returning result fo result_id {result_id}")

    return result, 200


@app.route("/nlp", methods=["POST"])
def nlp_route():
    # Header check
    expected_format = request.headers.get("accept")
    if not expected_format in SUPPORTED_HEADER_FORMAT:
        return (
            "Accept format {} not supported. Supported MIME types are :{}".format(
                expected_format, " ".join(SUPPORTED_HEADER_FORMAT)
            ),
            400,
        )
    logger.debug("Request type:" + request.headers.get("accept"))

    # Parse config
    try:
        if request.form.get("documents", []) and request.form.get("nlpConfig", {}):
            documents = json.loads(request.form.get("documents"))
            request_config = NLPConfig(json.loads(request.form.get("nlpConfig")))
        else:
            documents = request.get_json(force=True)["documents"]
            request_config = NLPConfig(request.get_json(force=True)["nlpConfig"])

    except Exception as e:
        return "Failed to interpret config: " + str(e), 400

    logger.debug("Create an NLP task with config: " + str(request_config))

    task_info = {
        "main_config": request_config.toJson(),
        "service_name": config.service_name,
    }

    try:
        task = nlp_task.apply_async(
            queue=config.service_name + "_requests", args=[documents, task_info]
        )
        logger.debug(f"Create task with id {task.id}")
        
        return (
            json.dumps({"jobid": task.id})
            if expected_format == "application/json"
            else task.id
        ), 201
    
    except Exception as e:
        logger.debug("Failed to send request: " + str(e))
        return (json.dumps({}), 400)


@app.route("/revoke/<jobid>", methods=["GET"])
def revoke(jobid):
    AsyncResult(jobid).revoke()
    return "done", 200


@app.route("/job-log/<jobid>", methods=["GET"])
def getlogs(jobid):
    if os.path.exists(f"/usr/src/app/logs/{jobid}.txt"):
        with open(f"/usr/src/app/logs/{jobid}.txt", "r") as logfile:
            return "\n".join(logfile.readlines()), 200
    else:
        return f"No log found for jobid {jobid}", 400


@app.errorhandler(405)
def method_not_allowed(error):
    return "The method is not allowed for the requested URL", 405


@app.errorhandler(404)
def page_not_found(error):
    return "The requested URL was not found", 404


@app.errorhandler(500)
def server_error(error):
    logger.error(error)
    return "Server Error", 500


if __name__ == "__main__":
    parser = createParser()  # Parser definition at server/utils/confparser.py

    config = parser.parse_args()
    logger.setLevel(logging.DEBUG if config.debug else logging.INFO)

    try:
        # Setup SwaggerUI
        if config.swagger_path is not None:
            setupSwaggerUI(app, config)
            logger.debug("Swagger UI set.")
    except Exception as e:
        logger.warning("Could not setup swagger: {}".format(str(e)))

    # Results database info
    db_info = {
        "db_host": config.mongo_uri,
        "db_port": config.mongo_port,
        "service_name": config.service_name,
        "db_name": "nlpdb",
    }

    db_client = DBClient(db_info)

    logger.info("Starting ingress")
    logger.debug(config)
    serving = GunicornServing(
        app,
        {
            "bind": "{}:{}".format("0.0.0.0", 80),
            "workers": config.concurrency + 1,
            "timeout": 3600,
        },
    )

    try:
        serving.run()
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
    finally:
        db_client.close()
