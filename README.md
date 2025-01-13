# LLM Gateway

To test the app locally, use Docker Compose, which will also start the required services :  

* Celery for managing tasks that run LLM inference in the backend (run in the app docker entrypoint)  
* Redis as a task broker to queue and manage Celery tasks, and to keep track of the list of services configurations.


Follow these steps:

1. **Create a `.env` file** with the necessary environment variables. Below is a table listing configurable parameters that can be set in the `.env` file.

**Parameters:**

| Variable               | Description                                                                                   | Default                       | Example                          |
|------------------------|-----------------------------------------------------------------------------------------------|-------------------------------|----------------------------------|
| `PYTHONUNBUFFERED`     | Ensures Python output is immediately visible                                                 | `1`                           | `1`                              |
| `SERVICE_NAME`         | Sets the service name                                                                        | `LLM_Gateway`                 | `LLM_Gateway`                    |
| `OPENAI_API_BASE`      | Base URL for the OpenAI API                                                                  | `http://localhost:9000/v1`     | `http://vllm-backend:8000/v1`    |
| `OPENAI_API_TOKEN`     | Token for OpenAI API access                                                                  | `EMPTY`                       | `EMPTY`                          |
| `HTTP_PORT`            | Port for the service                                                                         | `8000`                        | `8000`                           |
| `CONCURRENCY`          | Number of Uvicorn workers                                                                   | `2`                           | `2`                              |
| `TIMEOUT`              | Request timeout in seconds                                                                   | `60`                          | `60`                             |
| `SWAGGER_URL`          | Route for the Swagger interface                                                              | `/docs`                       | `/docs`                          |
| `SERVICES_BROKER`      | URL for the Redis broker                                                                     | `redis://localhost:6379/0`     | `redis://task-broker-redis:6379/0` |
| `BROKER_PASS`          | Password for the Redis broker                                                                | `EMPTY`                       | `password`                       |
| `MAX_RETRIES`          | Max retries when calling OpenAI client                                                      | `6`                           | `6`                              |
| `MAX_RETRY_DELAY`      | Max delay between retries in seconds                                                         | `10`                          | `10`                             |
| `MAX_CONCURRENT_INFERENCES` | Max number of concurrent requests to the OpenAI client                                     | `3`                           | `3`                              |
| `WS_POLLING_INTERVAL`  | Polling interval for WebSocket updates in seconds                                            | `3`                           | `3`                              |


2. **Run Docker Compose**: After setting up your `.env` file, start the app using:

   ```bash
   docker compose up
   ```
The OpenAI API used in the application can be either vLLM or any inference endpoint, whether hosted locally or remotely.

note: mount your service prompts folder (./prompts here) as /usr/src/prompts  
note: mount your config folder (./.hydra-conf here) as /usr/src/.hydra-conf  
note : any modification to any service.yaml under .hydra-conf/services triggers a hot-reload of /services route. Prompt template (servicename.txt) is reloaded uppon any usage request

note: Always use a string val for OPENAI_API_TOKEN.

## Environment Variable Handling

Environment variables are preloaded by Hydra and are accessible in the code via a configuration object, making it easy to dynamically access settings in your application.

For example, in the Hydra YAML configuration:

```yaml
api_params:
  api_base: ${oc.env:OPENAI_API_BASE,http://localhost:9000/v1}  # Uses the OPENAI_API_BASE env variable or defaults to http://localhost:9000/v1
  api_key: ${oc.env:OPENAI_API_TOKEN,EMPTY}                      # Uses the OPENAI_API_TOKEN env variable or defaults to EMPTY
```


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

## Note on .hydra-conf/services

A new service is created using a yaml file under .hydra-conf/services, which acts as the manifest for the service parameters. It is associated with a corresponding `servicename.txt` under ./prompts, which contains the prompt template. The text file name must be the same as service.name (`summarize-en.txt` in the below example)

The configuration for each service is managed via Hydra and can be easily adjusted or extended by editing the YAML configuration. For example, a service configuration might look like this:

```yaml
summarize/en: # This is the service endpoint that will be generated
  type: summary
  fields: 2
  name: summarize-en
  description:
    fr: English summary
  backend: vLLM  # Deprecated, as the app is now backend-agnostic
  flavor:
    - name: llama
      modelName: meta-llama-31-8b-it  # Ensure the model is available on the inference server or it will cause errors
      totalContextLength: 128000  # Maximum context length, including prompt, user input, and generated tokens
      maxGenerationLength: 2048  # Maximum length for model output
      tokenizerClass: LlamaTokenizer
      createNewTurnAfter: 250  # New "virtual turns" created after this number of tokens
      summaryTurns: 3  # Number of turns to summarize
      maxNewTurns: 9  # Maximum number of turns processed; fewer may be used if the token count is too high
      temperature: 0.2  # Controls creativity, with a value close to zero for more accurate summaries
      top_p: 0.7  # Controls the variety of word choices in generation
      reduceSummary: false  # Option to reduce the summary (can be adjusted based on use case)
      consolidateSummary: false  # Option to consolidate the summary (can be adjusted based on use case)
      reduce_prompt: reduce-file # Specify a custom prompt to be used in the reduce step. Name of the txt file without the extension. File needs to be under the ${prompt_path} directory
      type: abstractive #  abstractive, extractive or markdown
```
This YAML configuration defines the parameters for the "summarize-en" service, specifying the model, tokenization settings, and output constraints. Each service is customized with its own settings under the `flavor` attribute, where you can configure the model name, context length, summary length, and other options.