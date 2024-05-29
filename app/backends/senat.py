from resume.interface import Interface
from .backend import LLMBackend
from typing import List, Tuple
import openai
from openai import OpenAI

class Senat(LLMBackend):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_key = kwargs.get('api_key')
        self.api_base = kwargs.get('api_base')
        self.logger.info(f"API Key: {self.api_key}")
        self.logger.info(f"API Base: {self.api_base}")

    pass

    def publish(self, content: str):
        #On ne va pas s'en servir pour nous interfacer avec
        pass

    def get_generation(self, turns: List[str]):
        pass
    def get_resume(self,transcription, cr_type, model_name):
        """
        Generate a resume from a transcription
        """
        interface = Interface(api_key=self.api_key, api_base=self.api_base, logger=self.logger)
        return reformat_out(interface.generate_resume(cr_type, model_name, reformat(transcription)))


def reformat(transcription):
    """
    Reformat the transcription to the format that the interface can understand
    """
    return transcription

def reformat_out(transcription):
    """
    Reformat the transcription to the format that the interface can understand for output
    """
    return transcription
