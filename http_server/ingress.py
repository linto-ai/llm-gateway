#!/usr/bin/env python3


# General dependencies

import json
import os
import logging
import asyncio
from asyncio import Semaphore


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
    case _:
        from celery_app import logger

# Main logic
match service_type:
    case "llm_gateway":
        semaphore = Semaphore(1) 

        @app.route("/services/<model_name>/generate", methods=["POST"])
        async def summarization_route(model_name: str):
            """Process a batch of articles and return the extractive summaries predicted by the
            given model. Each record in the data should have a key "text".
            """
            try:
                logger.info("Summarization request received")
                results = []
                print(request.data)
                file = request.files.get('file')
                
                
                params = json.loads(request.form['format'])
                content = file.read().decode('utf-8') if file else ""
                #print(content)
                #print(params)
                logger.info("Processing started")
                async with semaphore:
                    results = await get_generation(content, params, MODELS[model_name])
                logger.info("Processing finished")
                ret_val = {"summarization": results}
                return jsonify(ret_val), 200
            except Exception as e:
                #logger.error(request.data)
                return "Missing request parameter: {}".format(e)
            
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
