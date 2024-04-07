import os
# Prevents tokenizers from using multiple threads
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
from transformers import AutoTokenizer
from transformers import LlamaTokenizerFast
from openai import OpenAI
from typing import List, Tuple
import requests
import json
import asyncio
import math
import re
import logging
logging.basicConfig(
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
)
logger = logging.getLogger("backend")
logger.setLevel(logging.DEBUG)

class LLMBackend:
    def __init__(self):
        pass

    def loadPrompt(self, service_name: str):
        logger.info(f"Loading prompt for service: {service_name}")
        txt_filepath = f'services/{service_name}.txt'
        with open(txt_filepath, 'r') as f:
            self.prompt = f.read()
            
    def setup(self, params: json):
        logger.info(f"Setting up backend with params: {params}")
        try:
            for attr in ['totalContextLength', 'maxGenerationLength', 'createNewTurnAfter', 'modelName', 'summaryTurns', 'maxNewTurns']:
                setattr(self, attr, params[attr])
            # @TODO: Shall use the tokenizer from the model name / tokenizerclass
            # seems fine so far as it yields the same token count as the tokenizer from the mixed model
            self.tokenizer =  LlamaTokenizerFast.from_pretrained("hf-internal-testing/llama-tokenizer")
            self.promptTokenCount = len(self.tokenizer(self.prompt)['input_ids'])
            logger.info(f"Prompt token count: {self.promptTokenCount}")
            return True
        except Exception as e:
            logger.error(f"Error setting up backend: {e}")
            raise e

    def get_splits(self, content: str):
        lines = content.splitlines()
        speaker = "(?) : "
        newTurns = []
        # - Only matches once, at the beggining of the string
        # - any characters or numbers of words followed by " : " or ": " or " :"
        pattern = r"^[A-Za-z0-9\s\-éèêëàâäôöùûüçïîÿæœñ]+ ?: ?"
        #sentence_endings = r"(?:\. |\.\.\. |\? |! |\.\.\.|\?\"|!\"|\?'|!'|¿ |¡ |« |» |· )"
        sentence_endings = r"(?:\. |\.\.\. |\? |! |\.\.\.|\?\"|!\"|\?'|!'|¿ |¡ |« |» |· )(?=[A-Z])" #followed by capital letter ?
        # This loop ensures all new lines are related to the last speaker
        for line in lines:
            if line.strip() == "":
                continue  # Skip empty lines
            tokenCount = 0 
            match = re.match(pattern, line, re.I)
            if match:
                speaker = match.group(0)
            else:
                if speaker:
                    line = speaker + line
                else:
                    line = "(?) : " + line

            tokens = self.tokenizer(line)['input_ids']
            tokenCount += len(tokens)
            if tokenCount > self.createNewTurnAfter:
                # Split the line at the next sentence and create a new line
                sentences = re.split(sentence_endings, line)
                for i, sentence in enumerate(sentences):
                    if sentence.strip() == "":
                        continue
                    if i == 0:
                        newTurns.append(sentence)
                    else:
                        newTurns.append(speaker + sentence)
                tokenCount = 0  # Reset token count for the new line
            else:
                if line.strip() != "":
                    newTurns.append(line)
        return newTurns

    def get_dialogs(self, chunks: List[Tuple[str, str]], max_new_speeches: int = -1) -> List[str]:
        # implementation here
        pass

    def get_result(self, prompt, model_name, temperature=1, top_p=0.95, generation_max_tokens=1028):
        # implementation here
        pass

    def get_generation(self, content, params):
        # implementation here
        pass