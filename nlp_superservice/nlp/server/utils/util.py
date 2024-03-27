import hashlib
import os
import subprocess
from typing import Dict, List

from nlp.processing.configs.mainconfig import NLPConfig

__all__ = ["fileHash", "requestlog", "read_timestamps"]


def fileHash(f):
    """Returns md5 hash hexdigest"""
    return hashlib.md5(f).hexdigest()


def requestlog(logger, origin: str, config: NLPConfig):
    """Displays request parameters as log INFO"""
    logger.info(
        """Request received:\n
                Origin: {}\n 
                Param: {}\n
                """.format(
            origin, str(config)
        )
    )
