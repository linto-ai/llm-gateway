import asyncio
import json
import time
from llm import LLM
from prompt import get_chat_prompt


def load_file(file_path: str) -> str:
    """
    Reads a file and returns its content.

    Args:
        file_path (str): The path to the file.

    Returns:
        str: The content of the file.
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()


def split_text(text: str, chunk_size: int, chunk_overlap: int) -> list:
    """
    Splits a given text into chunks of a specified size with a specified overlap.

    Args:
        text (str): The text to be split.
        chunk_size (int): The desired size of each chunk.
        chunk_overlap (int): The desired overlap between chunks.

    Returns:
        list: A list of text chunks.
    """
    chunks = []
    for i in range(0, len(text), chunk_size - chunk_overlap):
        chunks.append(text[i:i + chunk_size])
    return chunks


async def infer_llm_map(client: LLM, prompt_map: str, text: str, n, max_tokens_llm):
    """
    Creates a chat completion with the OpenAI API.

    Args:
        client (LLM): The LLM client.
        prompt_map (str): The prompt for mapping.
        text (str): The text to be summarized.
        n (int): The number of chunks.
        max_tokens_llm (int): Maximum tokens for LLM.

    Returns:
        dict: The response from the API.
    """
    message = get_chat_prompt(prompt_map, text)
    return await client.call_llm(message, max_tokens_llm // n)


async def infer_llm_reduce(client: LLM, prompt_reduce: str, text: str, max_tokens):
    """
    Creates a chat completion with the OpenAI API to reduce the summaries.

    Args:
        client (LLM): The LLM client.
        prompt_reduce (str): The prompt for reduction.
        text (str): The text to be summarized.
        max_tokens (int): Maximum tokens for reduction.

    Returns:
        dict: The response from the API.
    """
    message = get_chat_prompt(prompt_reduce, text)
    return await client.call_llm(message, max_tokens)


async def queue_api_calls_map_reduce(client: LLM, prompt_map: str, prompt_reduce: str, chunks: list[str],
                                     max_tokens_llm, max_tokens):
    """
    Asynchronously calls the API to summarize each chunk of the document and then to reduce the summaries.

    Args:
        client (LLM): The LLM client.
        prompt_map (str): The prompt for mapping.
        prompt_reduce (str): The prompt for reduction.
        chunks (list): The list of chunks to be summarized.
        max_tokens_llm (int): Maximum tokens for LLM.
        max_tokens (int): Maximum tokens for reduction.

    Returns:
        str: The final summarized text.
    """
    n = len(chunks)
    responses = await asyncio.gather(*[infer_llm_map(client, prompt_map, chunk, n, max_tokens_llm) for chunk in chunks])
    results = [response for response in responses]
    final_response = await infer_llm_reduce(client, prompt_reduce, '\n'.join(results), max_tokens)
    return final_response



def queue_api_calls_refined(client: LLM, prompt_refine: str, prompt_refined_bf_text : str, chunks: list[str],
                            max_tokens_llm):
    """
    Calls the API to refine each chunk of the document.

    Args:
        client (LLM): The LLM client.
        prompt_refine (str): The prompt for refining.
        prompt_refined_bf_text (str): The prompt before refining the text.
        chunks (list): The list of chunks to be refined.
        max_tokens_llm (int): Maximum tokens for LLM.
    Returns:
        str: The final refined text.
    """
    n = len(chunks)
    resume = ""
    for chunk in chunks:
        message = get_chat_prompt(prompt_refine + resume, prompt_refined_bf_text + chunk)
        response = asyncio.run(client.call_llm(message, max_tokens_llm // n))
        resume += response
    return resume


def summarized_text(api_key, base_url, prompts_file: str, input_file, output_file, chunk_size, chunk_overlap,
                    max_tokens_llm,
                    max_tokens):
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
        max_tokens_llm (int): The maximum number of tokens for LLM.
        max_tokens (int): The maximum number of tokens for reduction.

    Returns:
        str: The summarized text.
    """
    start = time.time()

    llm = LLM(api_key=api_key, base_url=base_url)
    f = open(prompts_file, "r")
    prompts = json.loads(f.read())

    input_text = load_file(input_file)
    chunks = split_text(input_text, chunk_size, chunk_overlap)

    #final_summary = asyncio.run(
    #    queue_api_calls_map_reduce(llm, prompt_map=prompts["prompt_map"], prompt_reduce=prompts["prompt_reduce"],
    #                               chunks=chunks, max_tokens_llm=max_tokens_llm, max_tokens=max_tokens))

    final_summary = queue_api_calls_refined(llm, prompt_refine=prompts["prompt_refine"],
                                prompt_refined_bf_text=prompts["prompt_refine_bf_text"],
                                chunks=chunks, max_tokens_llm=max_tokens_llm, max_tokens=max_tokens)

    with open(output_file, 'w', encoding='utf-8') as file:
        file.write(final_summary)

    end = time.time()
    print(f"Time taken: {end - start}")

    return final_summary
