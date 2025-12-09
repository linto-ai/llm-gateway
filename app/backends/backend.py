import os
# Prevents tokenizers from using multiple threads
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

import logging
from app.core.config import settings
from .chunking import Chunker

# Configure logging format and level
logging.basicConfig(
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
)

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
        self.logger.setLevel(logging.DEBUG if settings.debug else logging.INFO)
        self.logger.info(f"Setting up backend with params: {task_data['backendParams']} for task: {task_data['task_id']}")

        # Store task_data reference for prompt loading
        self.task_data = task_data

        self.task_id = task_data['task_id']
        self.content = task_data['content']
        self.name = task_data['name']
        self.task_type = task_data['type']
        self.promptFields = task_data['fields']
        try:
            # Load prompt from task_data (database)
            self.loadPrompt()

            # Set all backend parameters from task_data (populated from flavor/model in DB)
            for key, value in task_data["backendParams"].items():
                setattr(self, key, value)
            
            # Set up tokenizer using TokenizerManager
            self.tokenizer = self._load_tokenizer(task_data["backendParams"]["tokenizer"])
            
            # Initialize token count for prompt and adding token offset to account for special tokens
            self.prompt_token_count = len(self.tokenizer(self.prompt)["input_ids"])
            self.chunker = Chunker(self.tokenizer, self.createNewTurnAfter)

            if task_data["backendParams"]['reduceSummary'] and task_data["backendParams"]["reduce_prompt"] is not None:
                self.load_reduce_prompt()
            else:
                self.reduce_prompt = None
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error setting up backend: {e}")
            raise e

    def loadPrompt(self):
        """
        Load prompt from task_data (database).

        Priority 1: prompt_user_content (main prompt for user-facing services)
        Priority 2: prompt_system_content (system prompt if user prompt not set)

        No filesystem fallback - all prompts must be in database.
        """
        # Priority 1: User prompt content from database (most common case)
        if self.task_data.get("prompt_user_content"):
            self.prompt = self.task_data["prompt_user_content"]
            self.logger.info("Loaded prompt from database (prompt_user_content)")
            return

        # Priority 2: System prompt content from database
        if self.task_data.get("prompt_system_content"):
            self.prompt = self.task_data["prompt_system_content"]
            self.logger.info("Loaded prompt from database (prompt_system_content)")
            return

        # No prompt found - this is an error
        raise ValueError(f"No prompt content found in database for service '{self.name}'. "
                        f"Ensure the flavor has prompt_user_content or prompt_system_content set.")

    def load_reduce_prompt(self):
        """Load reduce prompt from task_data (database)."""
        if self.task_data.get("prompt_reduce_content"):
            self.reduce_prompt = self.task_data["prompt_reduce_content"]
            self.logger.info("Loaded reduce prompt from database (prompt_reduce_content)")
            return

        # No reduce prompt found - this is an error if reduce_summary is enabled
        raise ValueError(f"No reduce prompt content found in database for service '{self.name}'. "
                        f"Ensure the flavor has prompt_reduce_content set when reduce_summary=true.")

    def _load_tokenizer(self, tokenizer_name: str):
        """
        Load tokenizer using TokenizerManager or fallback to direct loading.

        Uses TokenizerManager for tiktoken and persisted HuggingFace tokenizers.
        Falls back to direct AutoTokenizer loading if TokenizerManager fails.

        Args:
            tokenizer_name: Tokenizer identifier (tiktoken encoding or HuggingFace repo)

        Returns:
            Tokenizer wrapper with encode/decode methods
        """

        # Check if this is a tiktoken encoding name
        tiktoken_encodings = {"cl100k_base", "o200k_base", "p50k_base", "r50k_base"}
        if tokenizer_name in tiktoken_encodings:
            try:
                import tiktoken
                from app.services.tokenizer_manager import TiktokenWrapper
                encoding = tiktoken.get_encoding(tokenizer_name)
                self.logger.info(f"Loaded tiktoken encoding: {tokenizer_name}")
                return TiktokenWrapper(encoding, tokenizer_name)
            except Exception as e:
                self.logger.error(f"Failed to load tiktoken {tokenizer_name}: {e}")
                raise

        # For HuggingFace tokenizers, try TokenizerManager first
        try:
            from app.services.tokenizer_manager import TokenizerManager

            manager = TokenizerManager.get_instance()
            local_path = manager._get_local_path(tokenizer_name)

            if local_path.exists():
                # Load from local storage
                wrapper = manager._load_from_local(tokenizer_name)
                if wrapper:
                    self.logger.info(f"Loaded tokenizer from local cache: {tokenizer_name}")
                    return wrapper

            # Try to download and save
            wrapper = manager._download_and_save(tokenizer_name)
            self.logger.info(f"Downloaded and cached tokenizer: {tokenizer_name}")
            return wrapper

        except Exception as e:
            self.logger.warning(f"TokenizerManager failed for {tokenizer_name}: {e}, falling back to direct load")

            # Fallback to direct AutoTokenizer loading
            try:
                from transformers import AutoTokenizer
                tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
                self.logger.info(f"Loaded tokenizer directly: {tokenizer_name}")
                return tokenizer
            except Exception as e2:
                self.logger.error(f"Failed to load tokenizer {tokenizer_name}: {e2}")
                raise