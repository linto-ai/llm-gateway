""" This module contains the configuration classe for the subtasks"""

from typing import Union

from nlp.processing.configs.sharedconfig import Config
from nlp import logger


class TaskConfig(Config):
    service_type = None
    task_name = None
    serviceName = None
    serviceQueue = None

    def __init__(self, config: Union[str, dict] = {}):
        super().__init__(config)
        self._checkConfig(config)
        self.isEnabled = False  # If the service is necessary for the request
        self.isAvailable = (
            False  # If the service is resolvable (Available or interchangeable)
        )
        self.serviceQueue = None

    def setService(self, serviceName: str, serviceQueue: str) -> None:
        self.isAvailable = True
        self.serviceName = serviceName
        self.serviceQueue = serviceQueue


class KeywordExtractionConfig(TaskConfig):  # TBR
    """KeywordExtractionConfig parses and holds KWE related configuration.
    Expected configuration format is as follows:
    ```json
    {
      "enableKeywordExtraction": boolean (true),
      "serviceName: str (None),
      "method": str ("frequencies"), 
      "methodConfig": 
          {
            ...
          }

    }
    ```
    """

    service_type = "keyword_extraction"
    task_name = "keyword_extraction_task"

    _keys_default = {
        "enableKeywordExtraction": True,
        "serviceName": None,
        "serviceQueue": None,
        "method": "frequencies",
        "methodConfig": 
        {
            "threshold": 1,
        }

    }

    def __init__(self, config: Union[str, dict] = {}):
        super().__init__(config)
        self._checkConfig(config)
        self.isEnabled = (
            self.enableKeywordExtraction
        )  # If the service is necessary for the request


    def _checkConfig(self, config):
        # TBD
        pass