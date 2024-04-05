import nltk
from transformers import AutoTokenizer
from openai import OpenAI
from typing import List, Tuple
import os
import requests
import json
import asyncio
import math
import re
from asyncio import Semaphore



#from __init__ import logger

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

semaphore = Semaphore(1)
OPENAI_API_KEY = "EMPTY"
#openai_api_key = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = "http://188.165.70.251:443/v1"
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

def get_template(type, template_has_two_fields):
    if type == "cra":
        file_name = "summarization/prompt_templates/cra.txt"
        
        #file_name = "prompt_templates/cra.txt" if template_has_two_fields else "prompt_templates/cra_reduced.txt"
    elif type == "cred":
        file_name = "summarization/prompt_templates/cra.txt"
        #file_name = "prompt_templates/cred.txt" if template_has_two_fields else "prompt_templates/cred_reduced.txt"
    with open(file_name, 'r') as file:
        prompt_template = file.read()
    return prompt_template


def get_splits(content: str, granularity: int = -1) -> List[Tuple[str, str]]:
    # If granularity is == -1, then 
    if granularity == -1:
        granularity = TOKENIZER_CONTEXT_LEN

    # Split the lines
    lines = content.splitlines()


    # Initialize variables
    current_speaker = None
    current_speech = ""
    speeches = []

    # Process each line
    for line in lines:
        # Check if the line starts with "Jon Doe : "
        pattern = r"\b[A-Za-z\-éèêëàâäôöùûüçïîÿæœñ]+\s[A-Za-z\-éèêëàâäôöùûüçïîÿæœñ]+\s:\s.*"
        match = re.match(pattern, line, re.I)
        if match:
            matched_string = match.group()
            # Split the matched string into two parts along ":"
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
            chunk = ""
            length = 0
            for i, sentence in enumerate(sentences):
                tokenized_sentence = tokenizer.tokenize(sentence)        
                current_token_count = len(tokenized_sentence) + length

                if current_token_count <= granularity:
                    chunk += sentence + " "
                    length = current_token_count
                else:
                    if chunk:
                        speeches.append((current_speaker, chunk.strip()))
                        chunk = sentence + "\n"
                        length = len(tokenized_sentence)
                        current_speech = current_speech[len(chunk)-1:] 
                
                # If it is the last sentence, save the chunk
                if i == len(sentences) - 1:
                    for line in chunk.split("\n"):
                        if line:
                            speeches.append((current_speaker, line.strip()))
                            current_speech = current_speech[len(chunk)-1:]
        else:
            # If the line doesn't start with "Jon Doe : ", add it to the current speech
            current_speech += " " + line

    # Save the last speech
    if current_speech:
        speeches.append((current_speaker, current_speech))

    return speeches


def get_dialogs(chunks: List[Tuple[str, str]], max_new_speeches: int = -1) -> List[str]:
    if max_new_speeches == -1:
        max_new_speeches = len(chunks)
    
    dialogs = [''.join(f'{speaker} : {speech}\n' for speaker, speech in chunks[i:i+max_new_speeches]) 
               for i in range(0, len(chunks), max_new_speeches)]
    
    return dialogs


def get_result(prompt, model_name, temperature=1, top_p=0.95, generation_max_tokens=1028):
    chat_response = client.chat.completions.create(
        model=model_name,

        messages=[
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        top_p=top_p, 
        max_tokens=generation_max_tokens
    )
    return chat_response


def get_generation(content, params, model_name):
    
    #logger.info(f'Template {format} has two fields') if template_has_two_fields else logger.info(f'Template {format} has one field')
    
    granularity = params["granularity_tokens"]
    max_new_speeches = params["max_new_speeches"]
    prev_new_summary_ratio = params["previous_new_summary_ratio"]
    resume_format = params["format"]
    template_has_two_fields = False if prev_new_summary_ratio == 0 else True

    prompt_template = get_template(resume_format, template_has_two_fields)
    tokenized_prompt_template = tokenizer.tokenize(prompt_template) 
    chunks = get_splits(content, granularity)
    dialogs = get_dialogs(chunks, max_new_speeches)
    intermediate_summary = ""
    summary = ""
    tokenized_summary = []
    for dialog in dialogs:
        tokenized_dialog = tokenizer.tokenize(dialog) 
        
        MAX_GENERATION_SIZE = TOKENIZER_CONTEXT_LEN - len(tokenized_dialog) - len(tokenized_prompt_template) - len(tokenized_summary)
        max_summary_len = math.floor(MAX_GENERATION_SIZE * prev_new_summary_ratio)
        max_prev_len = max_summary_len * PREVIOUS_NEW_SUMMARY_LEN_RATIO
        if len(tokenized_summary) >  max_summary_len:
            summary_lines = intermediate_summary.split('\n')
            intermediate_summary = " ".join(line for line in reversed(summary_lines) if len(line.split(' ')) <= max_prev_len)
        prompt = prompt_template.format(intermediate_summary, dialog) if template_has_two_fields else prompt_template.format(dialog)
        #print(f'Execuiting the prompt:\n{prompt}')
        #logger.info(f'Execuiting the prompt:\n{prompt}')
        #print(prompt)
        tokenized_summary = tokenizer.tokenize(intermediate_summary)        
        try:
                partial = get_result(prompt, model_name, params["temperature"], params["top_p"], params["maxGeneratedTokens"])
        except Exception as e:
            print(f"An error occurred: {e}")
            # Handle the error (e.g., by retrying the API call, logging the error, or stopping the application)
        else:
            intermediate_summary += partial.choices[0].message.content + "\n"
            summary += partial.choices[0].message.content + "\n"
        #generation_max_tokens = max(generation_max_tokens, 1)
    return summary



if __name__ == '__main__':
    with open('request.txt', 'r') as file:
        documents = file.read()
    MODELS = get_models_dict()
    params = {
        
    }
    print(asyncio.run(get_generation(documents, "cra", params, MODELS["mixtral"])))


