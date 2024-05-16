import asyncio
import json
import time
from llm import LLM
from prompt import get_chat_prompt
from utils import load_file, split_text


async def infer_llm_map(client: LLM, prompt_map: str, text: str, max_tokens: int) -> str:
    """
    Creates a chat completion with the OpenAI API.

    Args:
        client (LLM): The LLM client.
        prompt_map (str): The prompt for mapping.
        text (str): The text to be summarized.
        max_tokens (int): Maximum tokens for the output.

    Returns:
        str: The response from the llm.
    """
    message = get_chat_prompt(prompt_map, text)
    return await client.call_llm(message, max_tokens)


async def infer_llm_reduce(client: LLM, prompt_reduce: str, text: str, max_tokens) -> str:
    """
    Creates a chat completion with the OpenAI API to reduce the summaries.

    Args:
        client (LLM): The LLM client.
        prompt_reduce (str): The prompt for reduction.
        text (str): The text to be summarized.
        max_tokens (int): Maximum tokens for reduction.

    Returns:
        str: The response from the llm.
    """
    message = get_chat_prompt(prompt_reduce, text)
    return await client.call_llm(message, max_tokens)


async def queue_api_calls_map_reduce(client: LLM, prompt_map: str, prompt_reduce: str, chunks: list[str],
                                     max_tokens) -> str:
    """
    Asynchronously calls the API to summarize each chunk of the document and then to reduce the summaries.

    Args:
        client (LLM): The LLM client.
        prompt_map (str): The prompt for mapping.
        prompt_reduce (str): The prompt for reduction.
        chunks (list): The list of chunks to be summarized.
        max_tokens (int): Maximum tokens for reduction output.

    Returns:
        str: The final summarized text.
    """
    responses = await asyncio.gather(
        *[infer_llm_map(client, prompt_map, chunk, client.max_tokens // len(chunks)) for chunk in chunks])
    results = [response for response in responses]
    final_response = await infer_llm_reduce(client, prompt_reduce, '\n'.join(results), max_tokens)
    return final_response


def queue_api_calls_refined(client: LLM, prompt_refine: str, prompt_refined_bf_text: str, chunks: list[str],
                            max_tokens: int) -> str:
    """
    Calls the API to refine each chunk of the document.

    Args:
        client (LLM): The LLM client.
        prompt_refine (str): The prompt for refining.
        prompt_refined_bf_text (str): The prompt before refining the text.
        chunks (list): The list of chunks to be refined.
        max_tokens (int): Maximum tokens for the output.
    Returns:
        str: The final refined text.
    """
    n = len(chunks)
    resume = ""
    for i, chunk in enumerate(chunks):
        message = get_chat_prompt(prompt_refine + resume, prompt_refined_bf_text + chunk)
        response = asyncio.run(client.call_llm(message, max_tokens * (i + 1) // n))
        resume += response
    return resume


def summarized_text(api_key, base_url, prompts_file: str, input_file, output_file, chunk_size, chunk_overlap,
                    max_tokens) -> str:
    """
    Summarizes a text from a given file path.

    Args:
        api_key (str): The API key for OpenAI.
        base_url (str): The base URL for the OpenAI API.
        prompts_file (str): The path to the json prompts file.
        input_file (str): The path to the input text file.
        output_file (str): The path to the output text file.
        chunk_size (int): The size of each chunk.
        chunk_overlap (int): The overlap between chunks.
        max_tokens (int): Maximum tokens for the output.
    Returns:
        str: The summarized text.
    """
    start = time.time()

    llm = LLM(api_key=api_key, base_url=base_url)
    f = open(prompts_file, "r")
    prompts = json.loads(f.read())

    input_text = load_file(input_file)
    chunks = split_text(input_text, chunk_size, chunk_overlap)

    # final_summary = asyncio.run(
    #    queue_api_calls_map_reduce(llm, prompt_map=prompts["prompt_map"], prompt_reduce=prompts["prompt_reduce"],
    #                               chunks=chunks,max_tokens = max_tokens))

    final_summary = queue_api_calls_refined(llm, prompt_refine=prompts["prompt_refine"],
                                            prompt_refined_bf_text=prompts["prompt_refine_bf_text"],
                                            chunks=chunks, max_tokens=max_tokens)

    with open(output_file, 'w', encoding='utf-8') as file:
        file.write(final_summary)

    end = time.time()
    print(f"Time taken: {end - start}")

    return final_summary
