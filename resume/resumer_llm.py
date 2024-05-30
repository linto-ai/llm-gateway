import asyncio
import json
import time

from resume.transcriptions import Transcription

from resume.llm import LLM
from resume.utils import get_chat_prompt, RESUME_TYPE, load_file, split_text


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


async def infer_llm_on_chunck(client: LLM, prompt: str, chunk: dict, max_tokens: int) -> dict:
    message = get_chat_prompt(prompt, chunk['text'])
    chunk['text'] = await client.call_llm(message, max_tokens)
    return chunk

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
                    max_tokens, resume_type: str) -> str:
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
        resume_type (str): The type of resume to use.
    Returns:
        str: The summarized text.
    """

    start = time.time()

    # Initialize the LLM client
    llm = LLM(api_key=api_key, base_url=base_url)

    # Check if max_tokens is lower than llm.max_tokens
    if max_tokens > llm.max_tokens:
        raise ValueError("max_tokens cannot be greater than llm.max_tokens")

    # Load prompts from file depending on the resume type
    f = open(prompts_file, "r")
    prompts = json.loads(f.read())
    f.close()

    # Load input text
    input_text = load_file(input_file)
    chunks = split_text(input_text, chunk_size, chunk_overlap)

    # Call the API based on the resume type
    if resume_type == 'map_reduce':
        final_summary = asyncio.run(
            queue_api_calls_map_reduce(llm, prompt_map=prompts["prompt_map"], prompt_reduce=prompts["prompt_reduce"],
                                       chunks=chunks, max_tokens=max_tokens))
    elif resume_type == 'refine':
        final_summary = queue_api_calls_refined(llm, prompt_refine=prompts["prompt_refine"],
                                                prompt_refined_bf_text=prompts["prompt_refine_bf_text"],
                                                chunks=chunks, max_tokens=max_tokens)
    else:
        raise ValueError("Invalid resume type. Please choose from {}".format(RESUME_TYPE))

    with open(output_file, 'w', encoding='utf-8') as file:
        file.write(final_summary)

    end = time.time()
    print(f"Time taken: {end - start}")

    return final_summary


async def map_trancription(api_key, base_url, prompt, transcription: Transcription, max_call=5):
    """
    Asynchronously calls the LLM to process each chunk of the transcription.

    Args:
        api_key (str): The API key for OpenAI.
        base_url (str): The base URL for the OpenAI API.
        prompt (str): The prompt for the LLM.
        transcription (Transcription): The transcription to be processed.
        max_call (int, optional): The maximum number of API calls to make at once. Defaults to 5.

    Returns:
        list[dict]: A list of processed transcription chunks.

    Raises:
        Exception: If the API fails to respond after multiple retries.
    """
    start = time.time()

    # Initialize the LLM client
    llm = LLM(api_key=api_key, base_url=base_url)
    n = len(transcription)
    i = 0
    responses = []
    while(i < n):
        result = await asyncio.gather(
            *[infer_llm_on_chunck(llm, prompt, turn, 4000) for turn in transcription[i:min(i+max_call,n-1)]])
        for r in result:
            responses.append(r)
        i+= max_call
    end = time.time()
    print(f"Time taken: {end - start}")
    return responses




async def generate_cri(api_key, base_url, prompts_file: str, input_file):
    start = time.time()

    # Initialize the LLM client
    llm = LLM(api_key=api_key, base_url=base_url)

    # Load prompts from file depending on the resume type
    f = open(prompts_file, "r")
    prompts = json.loads(f.read())
    f.close()

    # Load input text
    with open(input_file, 'r') as file:
        dict_json = json.load(file)

    #chunks = split_json_text(dict_json)[:10]

    responses = await asyncio.gather(
        *[infer_llm_map(llm, prompts['prompt_CRI'], chunk, 3000) for chunk in chunks])
    results = [response for response in responses]

    # Call the API based on the resume type

    end = time.time()
    print(f"Time taken: {end - start}")

    for i in range(len(results)):
        dict_json[i]['CRI'] = results[i]
    return dict_json