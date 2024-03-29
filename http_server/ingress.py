#!/usr/bin/env python3


# General dependencies

import json
import os
import logging

from confparser import createParser
from flask import Flask, json, request
from serving import GunicornServing
from swagger import setupSwaggerUI
import pkgutil


service_type = os.getenv("SERVICE_TYPE")

# Dependencies for each service type
match service_type:
    case "keyword_extraction":
        app = Flask("__keyword_extraction_worker__")
        from keyword_extraction import logger
        # Logic
        from collections import OrderedDict
        from keyword_extraction.frekeybert import get_frekeybert_keywords
        from keyword_extraction.utils import get_keybert_keywords, get_word_frequencies, get_textrank_topwords, get_topicrank_topwords
    case "named_entity_recognition":
        app = Flask("__named_entity_recognition_worker__")
        app.config["JSON_AS_ASCII"] = False
        app.config["JSON_SORT_KEYS"] = False
        from named_entity_recognition import logger
        # Logic
        from named_entity_recognition.utils import get_named_entities
    case "topic_modeling":
        app = Flask("__topic_modeling_worker__")
        app.config["JSON_AS_ASCII"] = False
        app.config["JSON_SORT_KEYS"] = False
        from topic_modeling import logger
        # Logic
        from topic_modeling.utils import get_topics
    case "extractive_summarization":
        app = Flask("__extractive_summarization_worker__")
        app.config["JSON_AS_ASCII"] = False
        app.config["JSON_SORT_KEYS"] = False
        from extractive_summarization import logger
        # Logic
        from extractive_summarization.utils import get_summaries
    case "language_modeling":
        app = Flask("__language_modeling_worker__")
        from language_modeling import logger
        # Logic
        from language_modeling.utils import get_triton_generation
    case "llm_gateway":
        app = Flask("__llm_gateway__")
        from summarization import logger
        # Logic
        from summarization.utils import get_generation
    case _:
        from celery_app import logger

# Main logic
match service_type:
    case "keyword_extraction":
        @app.route("/keyword_extraction", methods=["POST"])
        def keyword_extraction_route():
            """Process a batch of documents and return the probability for of being keyword/phrase predicted by the
            given model. Each record in the data should have a key "text".
            """
            try:
                # logger.debug("########### Header: ", str(request.headers.get("accept")))
                logger.info("Keyword Extraction request received")
                # Fetch data/parameters
                logger.debug(request.headers.get("accept").lower())
                request_body = json.loads(request.data)
                documents = request_body.get("documents", "")
                config = request_body.get("config", {})
                method = config.get("method", "")
                logger.debug(method)
                logger.debug(config)
                logger.debug(documents)

                methods_map = {"frequencies": get_word_frequencies,
                               "textrank": get_textrank_topwords,
                               "topicrank": get_topicrank_topwords,
                               "keybert": get_keybert_keywords,
                               "frekeybert": get_frekeybert_keywords}
                results = []

                if method in methods_map:
                    try:
                        extract_keywords = methods_map[method.lower()]
                        for doc in documents:
                            results.append(extract_keywords(doc, config))
                    except Exception as e:
                        raise Exception("Can't extract keywords at keyword_extraction_task: " + str(
                            e) + "; config: " + str(config) + "; doc: " + str(documents))
                else:
                    logger.info(request_body)
                    logger.error("Method {} can't be found".format(method))
                    return results, 500

                results = [OrderedDict(sorted(r.items(), key=lambda x: -x[1]))
                           for r in results]

                # Return result
                return results, 200

            except Exception as e:
                logger.error(request.data)
                return "Missing request parameter: {}".format(e)

    case "named_entity_recognition":
        @app.route("/named_entity_recognition/<lang>", methods=["POST"])
        def named_entity_recognition_route(lang: str):
            """Process a batch of articles and return the entities predicted by the
            given model. Each record in the data should have a key "text".
            """
            try:
                logger.info("Named Entity Recognition request received")

                results = []
                request_body = json.loads(request.data)
                documents = request_body.get("documents", "")
                config = request_body.get("config", {})
                results = get_named_entities(lang, documents, config)

                return results, 200

            except Exception as e:
                logger.error(request.data)
                return "Missing request parameter: {}".format(e)

    case "topic_modeling":
        @app.route("/topic_modeling/<lang>", methods=["POST"])
        def topic_modeling_route(lang: str):
            """Process a batch of articles and return the topics predicted by the
            given model. Each record in the data should have a key "text".
            """
            try:
                logger.info("Topic Modeling request received")

                results = []
                request_body = json.loads(request.data)
                documents = request_body.get("documents", "")
                config = request_body.get("config", {})
                results = get_topics(lang, documents, config)

                return results, 200
            except Exception as e:
                logger.error(request.data)
                return "Missing request parameter: {}".format(e)
    case "extractive_summarization":
        @app.route("/extractive_summarization/<lang>", methods=["POST"])
        def extractive_summarization_route(lang: str):
            """Process a batch of articles and return the extractive summaries predicted by the
            given model. Each record in the data should have a key "text".
            """
            try:
                logger.info("Extractive Summarization request received")

                results = []
                request_body = json.loads(request.data)
                documents = request_body.get("documents", "")
                config = request_body.get("config", {})
                results = get_summaries(lang, documents, config)

                return results, 200
            except Exception as e:
                logger.error(request.data)
                return "Missing request parameter: {}".format(e)
    case "language_modeling":
        @app.route("/language_modeling/", methods=["POST"])
        def language_modeling_route():
            """Process a batch of articles and return the language modeling generation predicted by the
            given model. Each record in the data should have a key "text".
            """
            try:
                logger.info("Language Modeling request received")

                results = []
                request_body = json.loads(request.data)
                documents = request_body.get("documents", "")
                config = request_body.get("config", {})
                #results = get_generation(documents, config)
                results = get_generation(documents, config)

                return results, 200
            except Exception as e:
                logger.error(request.data)
                return "Missing request parameter: {}".format(e)
    case "llm_gateway":
        @app.route("/services/<model_name>/generate", methods=["POST"])
        def summarization_route(model_name: str):
            """Process a batch of articles and return the extractive summaries predicted by the
            given model. Each record in the data should have a key "text".
            """
            try:
                logger.info("Summarization request received")
                results = []
                request_body = json.loads(request.data)
                #print(request_body)
                documents = request_body.get("content", "")
                config = request_body.get("format", {})

                results = get_generation(documents, config)
                return str(results), 200
            except Exception as e:
                logger.error(request.data)
                return "Missing request parameter: {}".format(e)
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
