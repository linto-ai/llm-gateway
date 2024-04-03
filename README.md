# Summarization
Summarization using rolling prompt and vLLM


## Start working with the module:
1. Choose the the model from:
* TheBloke/Instruct_Mixtral-8x7B-v0.1_Dolly15K-AWQ
* TheBloke/Vigostral-7B-Chat-AWQ
2. Start vLLM server:
```console
docker run --runtime nvidia  
-v ~/.cache/huggingface:/root/.cache/huggingface     
--env "HUGGING_FACE_HUB_TOKEN=<secret>"     
-p 80:8000     --ipc=host     vllm/vllm-openai:latest     
--model TheBloke/Instruct_Mixtral-8x7B-v0.1_Dolly15K-AWQ  
--quantization awq
```
3. Build image
```console
docker build --tag linto-nlp/rolling-summarization:latest .
```
4. If you run container with GPU support, make sure that NVIDIA Container Toolkit and GPU driver are installed.
```console
docker run --gpus all \
--rm -p 80:80  \
--env-file .env \
linto-nlp/rolling-summarization:latest
```
or 
```console
docker compose up
```

## Request examples:
## POST request:
```console
curl --request POST --url 'http://localhost/services/mixtral/generate' --header 'Accept: application/json' --form 'format={
        "maxGeneratedTokens": 1024,
        "temperature": 1,
        "top_p": 0.95,
        "granularity_tokens": 200,
        "max_new_speeches": 4,
        "previous_new_summary_ratio": 0.5,
        "format": "cra"
    }' --form file=@tests/request.txt
```
File tests/form.json contains example config file read by the server.

File requests.txt contains the example of actual transcript.

## GET request:
```console
curl --request GET --url 'http://localhost/services'
```