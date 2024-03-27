import json
from typing import Union

from nlp.processing.configs.sharedconfig import Config
from nlp.processing.configs.taskconfig import KeywordExtractionConfig

from nlp import logger

class NLPConfig(Config):
    """MainConfig parses and holds request configuration regarding subtasks.
    Expected configuration format is as follows:
    ```json
    {
      "keywordExtractionConfig": object KeywordExtractionConfig (null), #TBR
    }
    ```
    """

    _keys_default = {
        "keywordExtractionConfig": KeywordExtractionConfig(),  # TBR
    }

    def __init__(self, config: Union[str, dict] = {}):
        super().__init__(config)
        self._checkConfig(config)

    @property
    def tasks(self) -> list:
        return [self.keywordExtractionConfig]  # TBR

    def _checkConfig(self, config):
        """Check and update field values"""
        logger.debug("WE'RE in NLP Config")
        logger.debug(str(config))
        if isinstance(self.keywordExtractionConfig, dict):
            self.keywordExtractionConfig = KeywordExtractionConfig(self.keywordExtractionConfig)

    def __eq__(self, other):
        if isinstance(other, NLPConfig):
            for key in self._keys_default.keys():
                if self.__getattribute__(key) != other.__getattribute__(key):
                    return False
            return True
        return False

    def __str__(self) -> str:
        return json.dumps(self.toJson())
