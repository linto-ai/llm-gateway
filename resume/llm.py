import asyncio
import aiohttp
from openai import AsyncOpenAI


class LLM:
    """
    A class to represent a Language Model (LLM).
    It abstracts away the OpenAI client and provides a unified interface for the user.
    """

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1",
                 model: str = "meta-llama-3-8b-instruct", max_tokens: int = 8000):
        """
        Constructs all the necessary attributes for the LLM object.

        Parameters
        ----------
            api_key : str
                API key for OpenAI
            base_url : str
                Base URL for the OpenAI API
            model : str
                The model to use for the LLM
            max_tokens : int
                The maximum number of tokens for the LLM
        """
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.max_tokens = max_tokens

    async def call_llm(self, message: list[dict], max_tokens: int = 1000, retries: int = 3) -> str:
        """
        Calls the LLM with the given prompt and input text.

        Parameters
        ----------
            message : list[dict]
                the prompt and input text to send to the LLM
            max_tokens : int
                the maximum number of tokens to generate as an output
            retries : int
                the number of times to retry in case of failure

        Returns
        -------
            str
                the generated output from the LLM
        """
        for attempt in range(retries):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=message,
                    stream=False,
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content.strip()
            except (aiohttp.ClientError, aiohttp.ServerTimeoutError) as e:
                print(f"Request failed: {e}, retrying {attempt + 1}/{retries}...")
                await asyncio.sleep(2 ** attempt)
        raise Exception("Failed to get response from OpenAI API after multiple retries")
