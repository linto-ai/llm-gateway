import os
# Prevents tokenizers from using multiple threads
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

from transformers import AutoTokenizer
import logging
from conf import cfg_instance
from .chunking import Chunker

# Configure logging format and level
logging.basicConfig(
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
)

# Load the spaCy model for French NLP processing
cfg = cfg_instance(cfg_name="config")

class LLMBackend:
    """
    Base class for handling LLM-related backend processes such as prompt loading, tokenization, 
    and chunking. It configures parameters, loads defaults, and sets up necessary components.
    """
    def __init__(self, task_data):
        """
        Initializes the backend with task-specific parameters and sets up tokenizer and chunker.
        
        Args:
            task (dict): Task containing parameters like task_id, content, backendParams, and type.

        Raises:
            Exception: If any errors occur during setup.
        """
        self.logger = logging.getLogger("backend")
        self.logger.setLevel(logging.DEBUG if cfg.debug else logging.INFO)
        self.logger.info(f"Setting up backend with params: {task_data['backendParams']} for task: {task_data['task_id']}")
        self.task_id = task_data['task_id']
        self.content = task_data['content']
        try:
            # Load prompt from txt file
            self.loadPrompt(task_data["type"], task_data["fields"])
            
            # Set default values for all attributes
            for key, default_value in cfg.backend_defaults.items():
                if key not in task_data["backendParams"]:
                    self.logger.info(f"Setting default value for attribute '{key}': {default_value}")
                    setattr(self, key, default_value)
            
            # Overwrite default values with the provided parameters        
            for key, value in task_data["backendParams"].items():
                if hasattr(self, key) and (key not in cfg.backend_defaults):
                    self.logger.info(f"Overwriting existing attribute '{key}' with new value: {value}")
                setattr(self, key, value)
            
            # Set up tokenizer and chunker
            self.tokenizer =  AutoTokenizer.from_pretrained(task_data["backendParams"]["tokenizer"])
            
            # Initialize token count for prompt and adding token offset to account for special tokens
            self.prompt_token_count = len(self.tokenizer(self.prompt)["input_ids"]) + task_data["backendParams"]["token_offset"]
            self.chunker = Chunker(self.tokenizer, self.createNewTurnAfter)

            if (task_data["backendParams"]['reduceSummary'] == True) and (task_data["backendParams"]["reduce_prompt"] is not None):
                self.load_reduce_prompt(task_data["type"], task_data["backendParams"]["reduce_prompt"])
            else :
                self.reduce_prompt = None
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error setting up backend: {e}")
            raise e

    def loadPrompt(self, service_name: str, fieldCount: int = 0):
        """
        Loads the prompt from a text file and sets the prompt fields.
        
        Args:
            service_name (str): The name of the service to load the prompt for.
            fieldCount (int, optional): The number of prompt fields. Defaults to 0.
        """
        self.logger.info(f"Loading prompt for service: {service_name}")
        self.promptFields = fieldCount
        self.logger.info(f"Prompt fields: {self.promptFields}")

        # Construct path to the prompt text file
        txt_filepath = os.path.join(cfg.prompt_path,f'{service_name}.txt')
        try:
            with open(txt_filepath, 'r') as f:
                # Prevent file system caching
                os.fsync(f.fileno())
                self.prompt = f.read()
                self.logger.info("Prompt loaded successfully.")
        except Exception as e:
            self.logger.error(f"Error loading prompt from {txt_filepath}: {e}")
            raise e

    def load_reduce_prompt(self, service_name: str, reduce_prompt: str):
        self.logger.info(f"Loading reduce prompt for service: {service_name}")

        # Construct path to the prompt text file
        txt_filepath = os.path.join(cfg.prompt_path,f'{reduce_prompt}.txt')
        try:
            with open(txt_filepath, 'r') as f:
                # Prevent file system caching
                os.fsync(f.fileno())
                self.reduce_prompt = f.read()
                self.logger.info("Reduce Prompt loaded successfully.")
        except Exception as e:
            self.logger.error(f"Error loading prompt from {txt_filepath}: {e}")
            raise e