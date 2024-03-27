# LinTO-NLP-Superservice

## Description

This subfolder is for building a Docker image for LinTO's NLP superservice - API for requesting information extraction services


## Prerequisites
To use the service you must have at least:
* A REDIS broker running at `SERVICES_BROKER`.
* A mongo DB running at `MONGO_HOST:MONGO_PORT`.
* One or multiple instances of NLP microservices (e.g. keyphrase extraction).
# //


## Deploy
### Using docker run
1. First build the image:
```cd nlp_superservice &&
docker build . -t nlp-superservice
```

2. Configure running environment variables in [environment file](.env) with the value described below [Environement Variables](#environement-variables)

3. Launch a container:

```bash
docker run --rm -it -p $SERVING_PORT:80 \
    --env-file .env \
    --name my_nlp_api \
    nlp-superservice \
    /bin/bash
```

### Using docker compose
1. Configure running environment variables in [environment file](.env) with the value described bellow [Environement Variables](#environement-variables)

2. Compose
```bash
docker compose up nlp-superservice
```

### Environement Variables

| Env variable| Description | Example |
|:-|:-|:-|
|SERVICE_NAME| Service name, use to connect to the proper redis channel and mongo collection|my_nlp_service|
|LANGUAGE| Language code as a BCP-47 code | fr_FR |
|CONCURRENCY|Number of workers (default 10)|10|
|SERVICES_BROKER|Message broker address|redis://broker_address:6379|
|BROKER_PASS|Broker Password| Password|
|MONGO_HOST|MongoDB results url|my-mongo-service| 
|MONGO_PORT|MongoDB results port|27017|
|RESOLVE_POLICY| Subservice resolve policy (default ANY) * |ANY \| DEFAULT \| STRICT |
# |MONGO_USER|MongoDB user|user|
# |MONGO_PSWD|MongoDB pswd|pswd|
# my-mongo-service = mongo-service-ip ?


*: See [Subservice Resolution](#subservice-resolution)

## API
The service offers a API REST to submit requests.

The service revolves arround 2 concepts:
* Asynchronous jobs identified with job_id: A job_id represents an ongoing task.
* Results identified by result_id.

Typical process follows this steps:
1. Submit your request and the configuration on ```/nlp```. The route returns a 201 with the job_id
2. Use the ```/job/{job_id}``` route to follow the job's progress. When the job is finished, you'll be greated with a 201 alongside a result_id.
3. Fetch the result using the ```/results/{result_id}``` route specifying your desired format and options. 

### /list-services
The list-services GET route fetch available sub-services.

It returns a json object containing list of deployed services indexed by service type. Services listed are filtered using the set LANGUAGE parameters.

```json
{
  "service-type1": [ # Service type
    {
      "service_name": "myservicetype1", # Service name. Used as parameter in the subservice config to call this specific service.
      "service_type": "service-type1", # Service type
      "service_language": "*", # Supported language
      "queue_name": "aqueue", # Celery queue used by this service
      "info": "It does something", # Information about the service.
      "instances": [ # Instances of this specific service.
        {
          "host_name": "feb42aacd8ad", # Instance unique id
          "last_alive": 1665996709, # Last heartbeat
          "version": "1.2.0", # Service version
          "concurrency": 1 # Concurrency of the instance
        }
      ]
    }
  ],
  "service-type2": [
    {
      "service_name": "myservicetype2",
      "service_type": "service-type2",
      "service_language": "fr-FR",
      "queue_name": "anotherqueue",
      "info": "Does something else",
      "instances": [
        {
          "host_name": "b0e9e24349a9",
          "last_alive": 1665996709,
          "version": "1.2.0",
          "concurrency": 1
        }
      ]
    }
  ]
}

```
__Language compatibily__

A subservice is compatible if its language(s) is(are) compatible with the superservice language:

superservice language <-> subservice language.
* Same BCP-27 code: fr-Fr <-> fr-FR => OK
* Language contained: fr-FR <-> fr-FR|it-IT|en-US => OK
* Star token (all_language): fr-FR <-> * => OK


### /nlp

The /nlp route allows POST request containing a text.

The /route route allows POST request.

The route accepts multipart/form-data requests.

Response format can be application/json or text/plain as specified in the accept field of the header.

|Form Parameter| Description | Required |
|:-|:-|:-|
|input| Text to extract information from | |
|Config|(object optionnal) A MainConfig Object describing parameters | Json |

If the request is accepted, answer should be ```201``` with a json or text response containing the jobid.

With accept: application/json
```json
{"jobid" : "the-job-id"}
```
With accept: text/plain
```
the-job-id
```

#### Mainconfig
The MainConfig object describe the transcription parameters and flags of the request. It is structured as follows:
```s{
  "keywordExtractionConfig":
    {
      "enableKeywordExtraction": true, 
      "methodConfig": 
          {
            "method": "textrank", 
            "damping": 0.3
          }
    }
}
```
# TBR: Add final Keyphrase extraction format

ServiceNames can be filled to use a specific subservice version. Available services are available on /list-services.

#### Subservice resolution
Subservice resolution is the mecanism allowing the transcription service to use the proper optionnal subservice such as diarization or punctuation prediction. Resolution is applied when no serviceName is passed along subtask configs. 

There is 3 policies to resolve service names:
* ANY: Use any compatible subservice.
* DEFAULT: Use the service default subservice (must be declared)
* STRICT: If the service is not specified, raise an error.

Resolve policy is declared at launch using the RESOLVE_POLICY environement variable: ANY | DEFAULT | STRICT (default ANY).

Default service names must be declared at launch: <SERVICE_TYPE>_DEFAULT. E.g. A default subservice is "capitalize", `CAPITALIZE_DEFAULT=capitalize1`.

### /job/

The /job/{jobid} GET route allow you to get the state of the given job.

Response format is application/json.

* If the job state is **started**, it returns a code ```102``` with informations on the progress.
* If the job state is **done**, it returns a code ```201``` with the ```result_id```.
* If the job state is **pending** returns a code ```404```. Pending can mean 2 things: a worker is not yet available or the jobid does not exist. 
* If the job state is **failed** returns a code ```400```.

```json
{
  #Task pending or wrong jobid: 404
  {"state": "pending"}

  #Task started: 102
  {"state": "started", "progress": {"current": 1, "total": 3, "step": "preprocessing (75%)"}}

  #Task completed: 201
  {"state": "done", "result_id" : "result_id"}

  #Task failed: 400
  {"state": "failed", "reason": "Something went wrong"}
}
```

### /results/
The /results/{result_id} GET route allows you to fetch result associated to a result_id.

#### Results
The accept header specifies the format of the result:
* application/json returns the complete result as a json object; 
```json
TBR Describe the result return format
```
* text/plain returns the final result as text
```
TBR exemple result
```

### /job-log/
The /job-log/{jobid} GET route to is used retrieve job details for debugging. Returns logs as raw text.

### /docs
The /docs route offers access to a swagger-ui interface with the API specifications (OAS3).

It also allows to directly test requests using pre-filled modifiable parameters.

## Usage
Request exemple:

__Initial request__
```bash
TBR give an exemple of curl request and its result
```

__Request job status__
```bash
curl -X GET "http://MY_HOST:MY_PORT/job/6e3f8b5a-5b5a-4c3d-97b6-3c438d7ced25" -H  "accept: application/json"

> {"result_id": "769d9c20-ad8c-4957-9581-437172434ec0", "state": "done"}
```

__Fetch result__
```bash
curl -X GET "http://MY_HOST:MY_PORT/results/769d9c20-ad8c-4957-9581-437172434ec0" -H  "accept: application/json"
```
## License
This project is licensed under AGPLv3 license. Please refer to the LICENSE file for full description of the license.

## Acknowledgment
* [celery](https://docs.celeryproject.org/en/stable/index.html): Distributed Task Queue.
* [pymongo](https://pypi.org/project/pymongo/): A MongoDB python client.
* [text2num](https://pypi.org/project/text2num/): A text to number convertion library.
* [Supervisor](http://supervisord.org/): A Process Control System.
