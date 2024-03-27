import nltk
nltk.download('punkt')
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from vllm import LLM, SamplingParams
from openai import OpenAI
import os

openai_api_key = os.getenv("OPENAI_API_KEY")
openai_api_base = os.getenv("OPENAI_API_BASE")
model_name = os.getenv("MODEL_NAME")
temp = float(os.getenv("TEMPERATURE"))
top_p = float(os.getenv("TOP_P"))

sampling_params = SamplingParams(temperature=temp, top_p=top_p)

client = OpenAI(
    api_key=openai_api_key,
    base_url=openai_api_base,
)

tokenizer = AutoTokenizer.from_pretrained(model_name)
#llm = LLM(model=model_name, quantization="awq", dtype="auto")

#model = AutoModelForSeq2SeqLM.from_pretrained(checkpoint)
prompt_template=f'''<s>[INST] <<SYS>>
    Vous êtes Vigogne, un assistant IA créé par Zaion Lab. Vous suivez extrêmement bien les instructions. Aidez autant que vous le pouvez.
    <</SYS>>

    {{}} [/INST] 
'''


def get_chunks(content: str):
    sentences = nltk.tokenize.sent_tokenize(content)
    #print(max([len(tokenizer.tokenize(sentence)) for sentence in sentences]))

    # TODO: vigostral have wrong max_len params, so hardcoded value here 
    #tokenizer_context_len = tokenizer.max_len_single_sentence
    tokenizer_context_len = 4096

    # The prompt should be less lengthy then model's max context windows
    tokenizer_context_len //= 2
     
    length = 0
    chunk = ""
    chunks = []
    count = -1
    for sentence in sentences:
        count += 1
        combined_length = len(tokenizer.tokenize(sentence)) + length # add the no. of sentence tokens to the length counter

        if combined_length  <= tokenizer_context_len: # if it doesn't exceed
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
    return chunks


def get_inputs(chunks):
    prompts = [prompt_template.format(chunk) for chunk in chunks]
    return prompts
    

def get_results(prompts):
    chat_responses = [prompt_template]
    for prompt in prompts:
        chat_response = client.chat.completions.create(
            model=model_name,

            messages=[
                #{"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=sampling_params.temperature,
            top_p=sampling_params.top_p
        )
        chat_responses.append(chat_response)
    return str(chat_responses)