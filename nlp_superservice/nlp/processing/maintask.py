""" The maintask module implements task steps to be processed by the request celery workers."""
import logging
import os
import time

from nlp import logger

from nlp.broker.celeryapp import celery
from nlp.processing.configs.mainconfig import NLPConfig
from nlp.processing.utils.serviceresolve import (ResolveException, ServiceResolver)
from nlp.processing.utils.taskprogression import (StepState, TaskProgression)
from nlp.server.mongodb.db_client import DBClient

__all__ = ["nlp_task"]

# Create shared mongoclient
db_info = {
    "db_host": os.environ.get("MONGO_HOST", None),
    "db_port": int(os.environ.get("MONGO_PORT", None)),
    "service_name": os.environ.get("SERVICE_NAME", None),
    "db_name": "nlpdb",
}

language = os.environ.get("LANGUAGE", None)

db_client = DBClient(db_info)


@celery.task(name="nlp_task", bind=True)
def nlp_task(self, documents, task_info: dict):
    """nlp task processes an NLP request.

    task_info contains the following field:
    - "main_config" : Task parameters configuration
    - "result_db" : Connexion info to the result database
    - "service": Name of the service
    - TBR: Additionnal parameters / values
    """

    # Logging task
    logging.basicConfig(
        filename=f"/usr/src/app/logs/{self.request.id}.txt",
        filemode="a",
        format="%(asctime)s,%(levelname)s %(message)s",
        datefmt="%H:%M:%S",
        level=logging.DEBUG,
        force=True,
    )

    print(f"Running task {self.request.id}")
    print(f"## DEBUG ## config {str(task_info)}")
    print(f"## DEBUG ## config {str(documents)}")

    self.update_state(state="STARTED", meta={"steps": {}})

    config = NLPConfig(task_info["main_config"])

    # Resolve required task queues
    resolver = ServiceResolver()
    for task in config.tasks:
        try:
            resolver.resolve_task(task)
            logging.info(
                f"Task {task} successfuly resolved -> {task.serviceName}:{task.serviceQueue} (Policy={resolver.service_policy})"
            )
        except ResolveException as error:
            logging.error(str(error))
            raise ResolveException(f"Failed to resolve: {str(error)}")

    # Task progression
    # Defines required steps
    progress = TaskProgression(
        [
            ("keyword_extraction", config.keywordExtractionConfig.isEnabled),
            ("language_modeling", config.languageModelingConfig.isEnabled),
            ("postprocessing", config.keywordExtractionConfig.isEnabled),
        ]
    )

    # Preprocessing
    # progress.steps["preprocessing"].state = StepState.STARTED
    # self.update_state(state="STARTED", meta=progress.toDict())
    # progress.steps["preprocessing"].state = StepState.DONE
    # self.update_state(state="STARTED", meta=progress.toDict())


    ## Fetch Keyword Extraction worker
    if config.keywordExtractionConfig.isEnabled:
        result_keyword_extraction = {}

        logging.info(f"Processing keyword_extraction task on {config.keywordExtractionConfig.serviceQueue}...")
        progress.steps["keyword_extraction"].state = StepState.STARTED
        try:
            keyword_extraction_config = config.keywordExtractionConfig;
        except Exception as e:
            raise Exception("Error parsing keyword extraction config: {}".format(str(config.keywordExtractionConfig)) + '   ' + str(e))


        try:
            ##################################
            logger.debug("#### SENDING THE TASK TO CELERY WORKER WITH CONFIG" + str(config))
            keywordExtractionJobId = celery.send_task(
                name=config.keywordExtractionConfig.task_name,
                queue=config.keywordExtractionConfig.serviceQueue,
                kwargs={'documents':documents, 
                        'method': keyword_extraction_config.toJSON()['method'],
                        'config': keyword_extraction_config.toJSON()['methodConfig']},
            )
            self.update_state(state="STARTED", meta=progress.toDict())
        except Exception as e:
            raise Exception("Failing to send task: {}".format(str(documents) + str(keyword_extraction_config)) + '   ' + str(e))

        # If task are parallelizable launch others task before waiting for results# TBR
        # Wait for tasks results
        
        result_keyword_extraction = {"keyword_extraction": keywordExtractionJobId.get(disable_sync_subtasks=False)}
        progress.steps["keyword_extraction"].state = StepState.DONE
        self.update_state(state="STARTED", meta=progress.toDict())
        if keywordExtractionJobId.status == "FAILURE":
            raise Exception("Keyword Extraction failed: {}".format(keywordExtractionJobId.result))

    # Write result in database
    progress.steps["postprocessing"].state = StepState.STARTED
    self.update_state(state="STARTED", meta=progress.toDict())
    if config.keywordExtractionConfig.isEnabled:
        try:
            result_id = db_client.push_result(
                job_id=self.request.id,
                origin="origin",
                service_name=task_info["service_name"],
                config=config,
                result=result_keyword_extraction,
            )
        except Exception as e:
            raise Exception("Failed to process result: " + str(result_keyword_extraction) + str(e))

    # Free ressource if necessary
    progress.steps["postprocessing"].state = StepState.DONE
    return result_id
