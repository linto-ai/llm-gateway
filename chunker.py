import nltk
nltk.download('punkt')
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from vllm import LLM, SamplingParams


model_name = "TheBloke/Vigostral-7B-Chat-AWQ"
tokenizer = AutoTokenizer.from_pretrained(model_name)
llm = LLM(model=model_name, quantization="awq", dtype="auto")

#model = AutoModelForSeq2SeqLM.from_pretrained(checkpoint)



def get_chunks(content: str):
    sentences = nltk.tokenize.sent_tokenize(content)
    print(max([len(tokenizer.tokenize(sentence)) for sentence in sentences]))

    # TODO: vigostral have wrong max_len params, so hardcoded value here 
    #tokenizer_context_len = tokenizer.max_len_single_sentence
    tokenizer_context_len = 10

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



def get_prompts(chunks):
    prompts = [
        "Tell me about AI",
        "Write a story about llamas",
        "What is 291 - 150?",
        "How much wood would a woodchuck chuck if a woodchuck could chuck wood?",
    ]
    prompt_template=f'''<s>[INST] <<SYS>>
    Vous êtes Vigogne, un assistant IA créé par Zaion Lab. Vous suivez extrêmement bien les instructions. Aidez autant que vous le pouvez.
    <</SYS>>

    {prompt} [/INST] 
    '''

    prompts = [prompt_template.format(prompt=prompt) for prompt in prompts]

    sampling_params = SamplingParams(temperature=0.8, top_p=0.95)


    outputs = llm.generate(prompts, sampling_params)

    # Print the outputs.
    for output in outputs:
        prompt = output.prompt
        generated_text = output.outputs[0].text
        print(f"Prompt: {prompt!r}, Generated text: {generated_text!r}")
'''
def get_prompts(chunks):
    inputs = [tokenizer(chunk, return_tensors="pt") for chunk in chunks]
    prompts = []
    for input in inputs:
        output = model.generate(**input)
        prompt = tokenizer.decode(*output, skip_special_tokens=True)
        prompts += prompt
    return prompts
'''