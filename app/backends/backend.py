import os
# Prevents tokenizers from using multiple threads
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
from transformers import LlamaTokenizerFast
from typing import List, Tuple
import json
import re
import logging
import spacy
from app.http_server.ingress import db, lock
logging.basicConfig(
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
)
nlp = spacy.load("fr_core_news_sm")

class LLMBackend:
    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger("backend")
        self.logger.setLevel(logging.DEBUG)

    def loadPrompt(self, service_name: str, fieldCount: int = 0):
        self.logger.info(f"Loading prompt for service: {service_name}")
        self.promptFields = fieldCount
        self.logger.info(f"Prompt fields: {self.promptFields}")
        txt_filepath = f'../services/{service_name}.txt'
        with open(txt_filepath, 'r') as f:
            # prevent caching
            os.fsync(f.fileno())
            self.prompt = f.read()
            
    def setup(self, params: json, task_id: str):
        self.logger.info(f"Setting up backend with params: {params} for task: {task_id}")
        self.task_id = task_id
        try:
            for attr in ['totalContextLength', 'maxGenerationLength', 'createNewTurnAfter', 'modelName', 'summaryTurns', 'maxNewTurns', 'top_p', 'temperature','reduceSummary','consolidateSummary']:
                setattr(self, attr, params[attr])
            # @TODO: Shall use the tokenizer from the model name / tokenizerclass
            # seems fine so far as it yields the same token count as the tokenizer from the mixed model
            self.tokenizer =  LlamaTokenizerFast.from_pretrained("hf-internal-testing/llama-tokenizer")
            self.promptTokenCount = len(self.tokenizer(self.prompt)['input_ids'])
            return True
        except Exception as e:
            self.logger.error(f"Error setting up backend: {e}")
            raise e

    def get_speaker(self, line: str, speaker:str=None ):
        pattern = r"^[A-Za-z0-9\s\-éèêëàâäôöùûüçïîÿæœñ]+ ?: ?"
        match = re.match(pattern, line)
        if match:
            return line, match.group(0)
        else:
            if speaker:
                line = speaker + line
            else:
                line = "(?) : " + line
            return line, speaker

    def get_splits(self, content: str):
        lines = [ line for line in content.splitlines() if line.strip() != ""]
        speaker = "(?)"
        newTurns = []
        tokenCount = 0  # Initialize token counter

        for line in lines:
            tokenCount = 0
            # Get speaker name
            line, speaker = self.get_speaker(line, speaker)
            tokens = self.tokenizer(line)['input_ids']
            tokenCount = len(tokens)

            if tokenCount > self.createNewTurnAfter:
                doc = nlp(line[len(speaker):].strip())  # Process the remaining line with spaCy (without speaker)
                # initialize new turn and token count
                currentTurn = speaker
                speaker_tokens = self.tokenizer(currentTurn)['input_ids']
                tokenCount = len(speaker_tokens)
                # Segment the line into sentences using spaCy
                for i,sentence in enumerate(doc.sents):
                    sentence_text = sentence.text.strip()
                    if sentence_text.strip() == "":
                        continue
                    # Tokenize the sentence to count tokens                   
                    tokens = self.tokenizer(sentence_text)['input_ids']   

                    if tokenCount + len(tokens) > self.createNewTurnAfter:
                        # If token count exceeds the limit, add the sentence and reset token count
                        newTurns.append(currentTurn)
                        currentTurn = speaker + sentence_text
                        tokenCount = len(speaker_tokens)  # Reset token count after adding a new turn
                    else:
                        currentTurn += sentence_text
                        tokenCount += len(tokens)
                # Add the last turn
                newTurns.append(currentTurn)
            else:
                newTurns.append(line)
        
        return newTurns
    
    def updateTask(self, task_id: str, progress: int):
        self.logger.info(f"Task {task_id} progress : {progress}%")
        db.put(task_id, f"Processing {progress}%")

    def get_dialogs(self, chunks: List[Tuple[str, str]], max_new_speeches: int = -1) -> List[str]:
        # implementation here
        pass

    def get_result(self, prompt, model_name, temperature=1, top_p=0.95, generation_max_tokens=1028):
        # implementation here
        pass

    def get_generation(self, turns: List[str]):
        pass