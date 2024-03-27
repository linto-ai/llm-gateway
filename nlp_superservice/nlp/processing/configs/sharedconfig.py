""" This module contains the base configuration classes."""

import json
from typing import Union

from nlp import logger


class Config:
    """The config classe loads attributes defined in the _keys_default from a dict or a serialized json."""

    _keys_default = {}

    def __init__(self, config: Union[str, dict] = {}):
        if type(config) is str:
            try:
                config = json.loads(config)
            except Exception as e:
                raise Exception("Failed to load config")
        self._loadConfig(config)
        self._checkConfig(config)

    def _loadConfig(self, config: dict):
        for key in self._keys_default.keys():
            self.__setattr__(key, config.get(key, self._keys_default[key]))

    def _checkConfig(self, config):
        """Check incompatible field values"""
        logger.debug("WE'RE IN CONFIG")
        logger.debug(str(config))
        pass

    def toJson(self) -> dict:
        """Returns configuration as a dictionary"""
        config_dict = {}
        for key in self._keys_default.keys():
            config_dict[key] = (
                self.__getattribute__(key)
                if not isinstance(self.__getattribute__(key), Config)
                else self.__getattribute__(key).toJson()
            )
        return config_dict 


    def toJSON(self) -> dict:
        return self.toJson()

    def __eq__(self, other):
        """Compares 2 Config. Returns true if all fields are the same"""
        if isinstance(other, Config):
            for key in self._keys_default.keys():
                try:
                    if self.__getattribute__(key) != other.__getattribute__(key):
                        return False
                except:
                    return False
            return True
        return False

    def __str__(self) -> str:
        return json.dumps(self.toJson())
