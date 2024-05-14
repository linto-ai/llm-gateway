import asyncio
import aiohttp
from openai import AsyncOpenAI

class LLM:
    """
    A class to represent a Language Model (LLM).
    It abstracts away the OpenAI client and provides a unified interface for the user.
    """

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1"):
        """
        Constructs all the necessary attributes for the LLM object.

        Parameters
        ----------
            api_key : str
                API key for OpenAI
            base_url : str
                Base URL for the OpenAI API
        """
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def call_llm(self, prompt: str, input_text: str, max_tokens: int = 1000, retries: int = 3) -> str:
        """
        Calls the LLM with the given prompt and input text.

        Parameters
        ----------
            prompt : str
                the prompt text
            input_text : str
                the input text
            max_tokens : int
                the maximum number of tokens to generate
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
                    model="meta-llama-3-8b-instruct",
                    messages=[
                        {"role": "system",
                         "content": "Vous êtes un assistant spécialisé dans le résumé de conversations en francais et vous parlez uniquement francais dans un langage soutenu."},
                        {"role": "user",
                         "content": prompt},
                        {"role": "user", "content": input_text},
                    ],
                    stream=False,
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content.strip()
            except (aiohttp.ClientError, aiohttp.ServerTimeoutError) as e:
                print(f"Request failed: {e}, retrying {attempt + 1}/{retries}...")
                await asyncio.sleep(2 ** attempt)
        raise Exception("Failed to get response from OpenAI API after multiple retries")
