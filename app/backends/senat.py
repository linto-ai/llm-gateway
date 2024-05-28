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
        Interface()


