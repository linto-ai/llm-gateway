# LLM Gateway (better working one i guess)

Can be started locally using after installing requirements.

```
python3 -m app --api_base=http://localhost:9000/v1
```

- `--service_name`: Sets the service name. Defaults to "LLM_Gateway".
- `--api_base`: Sets the OpenAI API base URL. Defaults to "http://localhost:9000/v1".
- `--api_key`: Sets the OpenAI API token. Defaults to "EMPTY".
- `--service_port`: Sets the service port. Defaults to 8000.
- `--workers`: Sets the number of Gunicorn workers. Defaults to 2.
- `--timeout`: Sets the request timeout. Defaults to 60 seconds.
- `--swagger_url`: Sets the Swagger interface URL. Defaults to "/docs".
- `--swagger_prefix`: Sets the Swagger prefix. Defaults to an empty string.
- `--swagger_path`: Sets the Swagger file path. Defaults to "../document/swagger_llm_gateway.yml".
- `--debug`: Enables debug logs if provided.
- `--db_path`: Sets the path to the result database. Defaults to "./results.sqlite".


Tests would use 

```
python3 -m tests
```
but none yet. Chunker seems very fine at least.

next head to host:port/docs for swagger and profit

# Docker Compose & swarm env

docker compose up shall start vLLM with vigostral and llm-gateway in the same network

__note__: Always use a string val for OPENAI_API_TOKEN.

## Available Envs

- `PYTHONUNBUFFERED=1`: Ensures that Python output is sent straight to terminal (unbuffered), making Python output, including tracebacks, immediately visible.
- `SERVICE_NAME=LLM_Gateway`: Sets the service name.
- `OPENAI_API_BASE=http://vllm-backend:8000/v1`: Sets the OpenAI API base URL.
- `OPENAI_API_TOKEN=EMPTY`: Sets the OpenAI API token.
- `HTTP_PORT=8000`: Sets the service port.
- `CONCURRENCY=2`: Sets the number of Gunicorn workers.
- `TIMEOUT=60`: Sets the request timeout.
- `SWAGGER_PREFIX=`: Sets the Swagger prefix.
- `SWAGGER_PATH=../document/swagger_llm_gateway.yml`: Sets the Swagger file path.
- `RESULT_DB_PATH=./results.sqlite`: Sets the path to the result database.

## vLLM backend locally

```console
docker run --gpus=all -v ~/.cache/huggingface:/root/.cache/huggingface  -p 9000:8000     --ipc=host vllm/vllm-openai:latest --model TheBloke/Vigostral-7B-Chat-AWQ  --quantization awq
```

## vLLM backend on the server

```console
docker service create \
  --name vllm-service \
  --network net_llm_services \
  --mount type=bind,source=/home/linagora/shared_mount/models/,target=/root/.cache/huggingface \
  vllm/vllm-openai:latest \
  --model TheBloke/Instruct_Mixtral-8x7B-v0.1_Dolly15K-AWQ \
  --quantization awq \
  --gpu-memory-utilization 0.5
```

## Note on app/services

A new service is created using servicename.json, as a manifest of parameters. It's associated with servicename.txt that holds the prompt template

See notes below
```json
{
    "type": "summary",
    "fields": 2,
    "name": "cra", // name of the service (route)
    "description": {
        "fr": "Compte Rendu Analytique"
    },
    "backend": "vLLM", // only one supported, we can add more easily
    "flavor": [
        {
            "name":"mixtral", // the name of the flavor to use in request
            "modelName": "TheBloke/Instruct_Mixtral-8x7B-v0.1_Dolly15K-AWQ", // Ensure you have this running on vLLM server or it will crash
            "totalContextLength": 32768, // Max Context = Prompt + User Prompt + generated Tokens
            "maxGenerationLength": 2048, // Limits the output from the model. Keep this fairly high.
            "tokenizerClass": "LlamaTokenizer",
            "createNewTurnAfter": 178, // Forces the chunker to create a new "virtual turns" whenever a turn reaches this number of tokens.
            "summaryTurns": 2, // 2 previously summarized turns will get injected to the template
            "maxNewTurns": 6, // 6 turns at max will get processed. Shall failback to less if we reach high token count (close to maxContextSize)
            "temperature": 0.1, // 0-1 : creativity, shall be close to zero as we want accurate sumpmaries
            "top_p": 0.8 // 0-1 : i.e. 0.5: only considers words that together add up to at least 50% of the total probability, leaving out the less likely ones. i.e 0.9 0.9: This includes a lot more words in the choice, allowing for more variety and originality.
        }
    ]
}
```