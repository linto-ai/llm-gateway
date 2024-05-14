import asyncio
import time
from llm import LLM

def load_file(file_path: str) -> str:
    """
    Load the content of a file.

    Args:
        file_path (str): The path to the file.

    Returns:
        str: The content of the file.
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def split_text(text: str, chunk_size: int, chunk_overlap: int) -> list:
    """
    Splits the text into chunks of a specified size with a specified overlap.

    Args:
        text (str): The text to be split.
        chunk_size (int): The size of each chunk.
        chunk_overlap (int): The overlap between chunks.

    Returns:
        list: The list of text chunks.
    """
    chunks = []
    for i in range(0, len(text), chunk_size - chunk_overlap):
        chunks.append(text[i:i + chunk_size])
    return chunks

async def infer_llm_map(client, prompt, text, n, max_tokens_llm):
    """
    This function creates a chat completion with the OpenAI API.

    Args:
        client (LLM): The LLM client.
        text (str): The text to be summarized.
        n (int): The number of chunks.
        max_tokens_llm (int): Maximum tokens for LLM.

    Returns:
        dict: The response from the API.
    """
    return await client.call_llm(prompt, text, max_tokens_llm // n)

async def infer_llm_reduce(client, prompt, text, max_tokens):
    """
    This function creates a chat completion with the OpenAI API to reduce the summaries.

    Args:
        client (LLM): The LLM client.
        text (str): The text to be summarized.
        max_tokens (int): Maximum tokens for reduction.

    Returns:
        dict: The response from the API.
    """
    return await client.call_llm(prompt, text, max_tokens)

async def queue_api_calls(client, prompt, chunks, max_tokens_llm, max_tokens):
    """
    This function asynchronously calls the API to summarize each chunk of the document and then to reduce the summaries.

    Args:
        client (LLM): The LLM client.
        chunks (list): The list of chunks to be summarized.
        max_tokens_llm (int): Maximum tokens for LLM.
        max_tokens (int): Maximum tokens for reduction.

    Returns:
        str: The final summarized text.
    """
    n = len(chunks)
    responses = await asyncio.gather(*[infer_llm_map(client, prompt, chunk, n, max_tokens_llm) for chunk in chunks])
    results = [response for response in responses]
    final_response = await infer_llm_reduce(client, prompt, '\n'.join(results), max_tokens)
    return final_response

def summarized_text(api_key, base_url, prompt_file, input_file, output_file, chunk_size, chunk_overlap, max_tokens_llm, max_tokens):
    """
    This function summarizes a text from a given file path.

    Args:
        api_key (str): The API key for OpenAI.
        base_url (str): The base URL for the OpenAI API.
        prompt_file (str): The path to the prompt file.
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
    prompt = load_file(prompt_file)
    input_text = load_file(input_file)
    chunks = split_text(input_text, chunk_size, chunk_overlap)
    final_summary = asyncio.run(queue_api_calls(llm, prompt, chunks, max_tokens_llm, max_tokens))

    with open(output_file, 'w', encoding='utf-8') as file:
        file.write(final_summary)

    end = time.time()
    print(f"Time taken: {end - start}")

    return final_summary
