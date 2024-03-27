#FROM python:3.11
FROM pytorch/pytorch:2.1.2-cuda11.8-cudnn8-runtime
LABEL maintainer="dgaynullin@linagora.com"
ENV PYTHONUNBUFFERED TRUE


# Common dependencies
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
    ca-certificates \
    g++ \
#     openjdk-11-jre-headless \
    curl \
    wget

WORKDIR /usr/src/app

# Python dependencies
COPY app/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app /usr/src/app/summarization
#COPY workers/language_modeling/RELEASE.md ./
#COPY workers/language_modeling/docker-entrypoint.sh ./

# Modules
#COPY celery_app /usr/src/app/celery_app
#COPY http_server /usr/src/app/http_server
#COPY document/swagger_llm.yml /usr/src/app/document/swagger.yml

#COPY scripts/wait-for-it.sh ./
#COPY scripts/healthcheck.sh ./

# Grep CURRENT VERSION
RUN export VERSION=$(awk -v RS='' '/#/ {print; exit}' RELEASE.md | head -1 | sed 's/#//' | sed 's/ //')

#HEALTHCHECK CMD ./healthcheck.sh

# Tag of the 
ENV SERVICE_TYPE rolling_prompt_summarization
ENV TEMP=/usr/src/app/tmp
ENV PYTHONPATH="${PYTHONPATH}:/usr/src/app/summarization"
#ENTRYPOINT ["./docker-entrypoint.sh"]
CMD "python proxy.py"