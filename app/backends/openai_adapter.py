from openai import OpenAI, AsyncOpenAI
import logging
from typing import List
from tenacity import retry, stop_after_attempt, wait_random_exponential
from conf import cfg_instance

cfg = cfg_instance(cfg_name="config")

class OpenAIAdapter:
    def __init__(self, task_data: dict):
        # Set up OpenAI API client and logging
        self.api_key = cfg.api_params.api_key
        self.api_base = cfg.api_params.api_base
        self.modelName =  task_data["backendParams"]["modelName"]
        self.temperature = task_data["backendParams"]["temperature"]
        self.top_p = task_data["backendParams"]["top_p"]
        self.maxGenerationLength = task_data["backendParams"]["maxGenerationLength"]
        self.logger = logging.getLogger("OpenAIAdapter")
        self.client = OpenAI(api_key=self.api_key, base_url=self.api_base)
        self.async_client = AsyncOpenAI(api_key=self.api_key, base_url=self.api_base)

    
    @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(cfg.api_params.max_retries))
    def publish(self, content: str) -> str:
        """
        Sync publishes a message to the OpenAI chat model and returns the response.
        Args:
            content (str): The content to be sent to the chat model.
        Returns:
            str: The response content from the chat model if successful.
            None: If an error occurs during the publishing process.
        """
        chat_response = self.client.chat.completions.create(
            model=self.modelName,
            
            messages=[
                {"role": "user", "content": content}
            ],
            temperature=self.temperature,
            top_p=self.top_p,
            max_tokens=self.maxGenerationLength
        )
        return chat_response.choices[0].message.content


    @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(cfg.api_params.max_retries))
    async def async_publish(self, content: str) -> str:
        """
        Async publishes a message to the OpenAI chat model and returns the response.
        Args:
            content (str): The content to be sent to the chat model.
        Returns:
            str: The response content from the chat model if successful.
            None: If an error occurs during the publishing process.
        """
        chat_response = await self.async_client.chat.completions.create(
            model=self.modelName,
            messages=[{"role": "user", "content": content}],
            temperature=self.temperature,
            top_p=self.top_p,
            max_tokens=self.maxGenerationLength
        )
        return chat_response.choices[0].message.content