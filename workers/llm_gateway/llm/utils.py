import nltk
from transformers import AutoTokenizer
from vllm import SamplingParams
from openai import OpenAI
import os
import requests
import json
import asyncio
import math
import re


from __init__ import logger

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

OPENAI_API_KEY = "EMPTY"
#openai_api_key = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = "http://188.165.70.251/v1"
#openai_api_base = os.getenv("OPENAI_API_BASE")
MODEL_NAME = "TheBloke/Instruct_Mixtral-8x7B-v0.1_Dolly15K-AWQ"
#model_name = os.getenv("MODEL_NAME")
TEMPERATURE = 0.8
#temp = float(os.getenv("TEMPERATURE"))
TOP_P = 0.95
#top_p = float(os.getenv("TOP_P"))
FREQUENCY_PENALTY = 0
#frequency_penalty = int(os.getenv("FREQUENCY_PENALTY"))
PRESENCE_PENALTY = 0
#presence_penalty = int(os.getenv("PRESENCE_PENALTY"))
TOKENIZER_CONTEXT_LEN = 4096
#tokenizer_context_len = int(os.getenv("TOKENIZER_CONTEXT_LEN"))
CHUNKER_GRANULARITY_RATIO = 1
PROMPT_GENERATION_RATIO = 0.5
PREVIOUS_NEW_SUMMARY_LEN_RATIO = 0.3


sampling_params = SamplingParams(temperature=TEMPERATURE, 
                                 top_p=TOP_P,  
                                 frequency_penalty=FREQUENCY_PENALTY,
                                 presence_penalty=PRESENCE_PENALTY)

client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_API_BASE,
)

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
prompt_template=''


def get_models_dict():
    return {
        "mixtral" : "TheBloke/Instruct_Mixtral-8x7B-v0.1_Dolly15K-AWQ", 
        "vigostral" : "TheBloke/Vigostral-7B-Chat-AWQ",
    }

def get_template(type):
    if type == "cra":
        #file_name = "summarization/prompt_templates/cra.txt"
        file_name = "prompt_templates/cra.txt"
    with open(file_name, 'r') as file:
        prompt_template = file.read()
    return prompt_template



def get_chunks(prompt_template: str, content: str):
    # Read the file
    lines = content.splitlines()

    # Initialize variables
    current_speaker = None
    current_speech = ""
    speeches = []

    # Process each line
    for line in lines:
        # Check if the line starts with "speaker X:"
        pattern = r"\b[A-Za-z\-éèêëàâäôöùûüçïîÿæœñ]+\s[A-Za-z\-éèêëàâäôöùûüçïîÿæœñ]+\s:\s.*"
        match = re.match(pattern, line, re.I)
        if match:
            matched_string = match.group()
            speaker, speech = matched_string.split(":", 1)
            # If this is a new speaker, save the current speech and start a new one
            if speaker != current_speaker:
                current_speaker = speaker
                current_speech = speech
            else:
                # Add to the current speech
                current_speech += " " + speech

            # If the current speech is too long, split it
            sentences = nltk.tokenize.sent_tokenize(current_speech)
            tokenized_prompt_template = tokenizer.tokenize(prompt_template)        
            summarization_context_len = (TOKENIZER_CONTEXT_LEN - len(tokenized_prompt_template)) * PROMPT_GENERATION_RATIO
            max_chunk_len = math.floor(summarization_context_len * CHUNKER_GRANULARITY_RATIO)  # The prompt should be less lengthy then model's max context windows
            chunk = ""
            length = 0

            for i, sentence in enumerate(sentences):
                tokenized_sentence = tokenizer.tokenize(sentence)        
                current_token_count = len(tokenized_sentence) + length

                
                if current_token_count <= max_chunk_len or i == len(sentences) - 1:
                    chunk += sentence + "\n"
                    length = current_token_count
                else:
                    speeches.append((current_speaker, chunk.strip()))
                    chunk = sentence + "\n"
                    length = len(tokenized_sentence)
                    current_speech = current_speech[len(chunk):] 
                
                # If it is the last sentence, save the chunk
                if i == len(sentences) - 1:
                    speeches.append((current_speaker, chunk.strip()))
                    current_speech = current_speech[len(chunk):]
        else:
            # If the line doesn't start with "speaker X:", add it to the current speech
            current_speech += " " + line

    return speeches


async def get_result(prompt, model_name, temperature=1, top_p=0.95, generation_max_tokens=1028):
    chat_response = client.chat.completions.create(
        model=model_name,

        messages=[
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        top_p=top_p, 
        max_tokens=generation_max_tokens,
        frequency_penalty=sampling_params.frequency_penalty,
        presence_penalty=sampling_params.presence_penalty,
    )
    return chat_response


async def get_generation(content, format, params, template_has_two_fields=True):
    prompt_template = get_template(format)
    tokenized_prompt_template = tokenizer.tokenize(prompt_template) 
    logger.info(f'Template {format} has two fields') if template_has_two_fields else logger.info(f'Template {format} has one field')
    chunks = get_chunks(prompt_template, content)
    summary = ""
    tokenized_summary = []
    for speaker, speech in chunks:
        chunk = speaker + ": " + speech
        tokenized_chunk = tokenizer.tokenize(chunk) 
        # Maximum summary len + Maximum generation len + chunk size + template = tokenizer context len
        MAX_GENERATION_SIZE = TOKENIZER_CONTEXT_LEN - len(tokenized_chunk) - len(tokenized_prompt_template)
        max_summary_len = math.floor(MAX_GENERATION_SIZE * PREVIOUS_NEW_SUMMARY_LEN_RATIO)
        if len(tokenized_summary) >  max_summary_len:
            summary_lines = summary.split('\n')
            summary = ' '.join(line for line in reversed(summary_lines) if len(line.split(' ')) <= max_summary_len)

        prompt = prompt_template.format(summary, chunk) if template_has_two_fields else prompt_template.format(chunk)
        
        logger.info(f'Execuiting the prompt:\n{prompt}')
        
        tokenized_summary = tokenizer.tokenize(summary)        
        
        # Tokenizer context len - (chunk size + template) * PREVIOUS_NEW_SUMMARY_LEN_RATIO = Maximum generation len
        generation_max_tokens = math.floor(MAX_GENERATION_SIZE * (1 - PREVIOUS_NEW_SUMMARY_LEN_RATIO))
    
        generation_max_tokens = max(generation_max_tokens, 1)
        partial = await get_result(prompt, MODEL_NAME, params["temperature"], params["top_p"], params["maxGeneratedTokens"])
        logger.info(f'{partial.choices[0].message.content}')
        summary += partial.choices[0].message.content + "\n"
    return summary



if __name__ == '__main__':
    with open('request.txt', 'r') as file:
        documents = file.read()
    MODELS = get_models_dict()
    temperature = 1
    top_p = 0.95 
    print(asyncio.run(get_generation(documents, "cra", temperature, top_p, MODELS["mixtral"])))


