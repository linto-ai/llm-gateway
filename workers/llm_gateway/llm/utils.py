import nltk
from transformers import AutoTokenizer
from vllm import SamplingParams
from openai import OpenAI
import os
import requests
import json
import asyncio


try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

openai_api_key = "EMPTY"
#openai_api_key = os.getenv("OPENAI_API_KEY")
openai_api_base = "http://188.165.70.251/v1"
#openai_api_base = os.getenv("OPENAI_API_BASE")
#model_name = "TheBloke/Instruct_Mixtral-8x7B-v0.1_Dolly15K-AWQ"
#model_name = os.getenv("MODEL_NAME")
temp = 0.8
#temp = float(os.getenv("TEMPERATURE"))
top_p = 0.95
#top_p = float(os.getenv("TOP_P"))
max_tokens = 2500
#max_tokens = int(os.getenv("MAX_TOKENS"))
frequency_penalty = 0
#frequency_penalty = int(os.getenv("FREQUENCY_PENALTY"))
presence_penalty = 0
#presence_penalty = int(os.getenv("PRESENCE_PENALTY"))
tokenizer_context_len = 1024
#tokenizer_context_len = int(os.getenv("TOKENIZER_CONTEXT_LEN"))


sampling_params = SamplingParams(temperature=temp, 
                                 top_p=top_p, 
                                 max_tokens=max_tokens, 
                                 frequency_penalty=frequency_penalty,
                                 presence_penalty=presence_penalty)

client = OpenAI(
    api_key=openai_api_key,
    base_url=openai_api_base,
)

tokenizer = AutoTokenizer.from_pretrained(model_name)
prompt_template=''

def get_models_dict():
    return {
        "mixtral" : "TheBloke/Instruct_Mixtral-8x7B-v0.1_Dolly15K-AWQ", 
        "vigostral" : "TheBloke/Vigostral-7B-Chat-AWQ",
    }

def get_template(type):
    if type == "cra":
        file_name = "summarization/prompt_templates/cra.txt"
    with open(file_name, 'r') as file:
        prompt_template = file.read()
    return prompt_template


def get_chunks(content: str):
    sentences = nltk.tokenize.sent_tokenize(content)
    #print(max([len(tokenizer.tokenize(sentence)) for sentence in sentences]))

    # TODO: vigostral have wrong max_len params, so hardcoded value here 
    #tokenizer_context_len = tokenizer.max_len_single_sentence
    chunker_context_len = tokenizer_context_len

    # The prompt should be less lengthy then model's max context windows
    chunker_context_len //= 2
     
    length = 0
    chunk = ""
    chunks = []
    count = -1
    for sentence in sentences:
        count += 1
        combined_length = len(tokenizer.tokenize(sentence)) + length # add the no. of sentence tokens to the length counter

        if combined_length  <= chunker_context_len: # if it doesn't exceed
            chunk += sentence + " " # add the sentence to the chunk
            length = combined_length # update the length counter

            # if it is the last sentence
            if count == len(sentences) - 1:
                chunks.append(chunk.strip()) # save the chunk
            
        else: 
            chunks.append(chunk.strip()) # save the chunk
            # reset 
            length = 0 
            chunk = ""

            # take care of the overflow sentence
            chunk += sentence + " "
            length = len(tokenizer.tokenize(sentence))
    #print(len(chunks), chunks)
    return chunks

    

async def get_result(prompt, model_name):
    chat_response = client.chat.completions.create(
        model=model_name,

        messages=[
            {"role": "user", "content": prompt},
        ],
        temperature=sampling_params.temperature,
        top_p=sampling_params.top_p, 
        max_tokens=sampling_params.max_tokens,
        frequency_penalty=sampling_params.frequency_penalty,
        presence_penalty=sampling_params.presence_penalty,
    )
    return chat_response



async def get_generation(documents, format, model_name):
    documents = str(documents)
    prompt_template = get_template(format)
    print(prompt_template)
    chunks = get_chunks(documents)
    summary = ""
    for chunk in chunks:
        # If the summary is bigger than 2000 words, use the biggest chunk at the end of the summary after the last new line
        if len(summary.split(' ')) > 2000:
            summary_lines = summary.split('\n')
            summary_chunk = ''
            for i in range(len(summary_lines) - 1, -1, -1):
                temp_chunk = summary_chunk + ' ' + summary_lines[i]
                if len(temp_chunk.split(' ')) > 2000:
                    break
                summary_chunk = temp_chunk
            summary = summary_chunk

        prompt = prompt_template.format(summary, chunk)
        #partial = await get_result(prompt, model_name)
        #summary += partial.choices[0].message.content + "\n"
    return summary


if __name__ == '__main__':
    with open('request.txt', 'r') as file:
        documents = file.read()
    print(asyncio.run(get_generation(documents, "cra", "mixtral")))
